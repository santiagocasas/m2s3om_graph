#!/usr/bin/env python3
"""Fresh, read-only artifact-URL reachability check for all 37 RDAMSC crosswalks.

Design notes (documented per the 2026-09-29 freeze audit request):

- There is no persisted RDAMSC catalog JSON anywhere in this repository. The
  "synced RDAMSC data" is obtained live via ``RDAMSCClient.get_mapping_detail``
  for each of the 37 known ``msc_id`` values (read from
  ``.local/rdamsc_pipeline_status.json``), exactly mirroring what
  ``m2s3om_graph.rdamsc.ingest.sync_rdamsc_catalog`` does internally. This is a
  live network call to https://rdamsc.bath.ac.uk on every run.
- The artifact URL list per crosswalk is ``detail_payload["locations"][].url``
  - the same raw list that ``m2s3om_graph.rdamsc.ingest._fetch_artifacts``
  consumes (NOT the single collapsed ``doc_uri`` that ``CrosswalkRecord``
  stores).
- URL candidate expansion (http->https fallback, GitHub web->raw fallback) and
  the request headers are imported directly from
  ``m2s3om_graph.rdamsc.artifacts`` (``_candidate_urls``, ``DEFAULT_HEADERS``)
  so the fallback behaviour is byte-identical to the pipeline's own fetch
  function. The raw HTTP request is performed here (not via
  ``fetch_artifact_text``) because that function only returns converted
  Markdown text - it does not expose the response's raw size, content-type or
  a hash of the body, all of which this script must record.
- This script performs NO writes anywhere except the two output files named
  on the command line / via --output. It never touches exports/sssom.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import socket
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from m2s3om_graph.rdamsc.api import RDAMSCClient  # noqa: E402
from m2s3om_graph.rdamsc.artifacts import DEFAULT_HEADERS, _candidate_urls  # noqa: E402

STATUS_FILE = ROOT / ".local" / "rdamsc_pipeline_status.json"
DEFAULT_OUT_CSV = ROOT / "exports" / "pipeline" / "latest" / "rdamsc_artifacts_full.csv"
DEFAULT_OUT_SUMMARY = ROOT / "exports" / "pipeline" / "latest" / "rdamsc_artifacts_full_summary.json"

RETRIES = 3  # 1 initial attempt + 2 retries
RETRY_DELAY_S = 10
TIMEOUT_S = 30


def load_crosswalk_msc_ids() -> dict[str, str]:
    """crosswalk_id -> msc_id (e.g. 'rdamsc_c1' -> 'c1'), from the live status file."""
    data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for crosswalk_id, entry in data.items():
        msc_id = entry.get("msc_id", "")
        if msc_id.startswith("msc:"):
            msc_id = msc_id[len("msc:") :]
        out[crosswalk_id] = msc_id
    return out


def fetch_locations(client: RDAMSCClient, msc_id: str) -> list[dict]:
    detail = client.get_mapping_detail(msc_id)
    return detail.get("locations", []) or []


def classify_exception(exc: Exception) -> tuple[str, str]:
    """Return (reason_code, detail_string)."""
    if isinstance(exc, requests.exceptions.Timeout):
        return "timeout", str(exc)
    if isinstance(exc, requests.exceptions.ConnectionError):
        msg = str(exc)
        low = msg.lower()
        if isinstance(exc.args[0] if exc.args else None, Exception):
            inner = exc.args[0]
            if isinstance(getattr(inner, "reason", None), Exception):
                inner = inner.reason
            if isinstance(inner, socket.gaierror) or "name or service not known" in low or "nodename nor servname" in low or "getaddrinfo failed" in low:
                return "dns_failure", msg
            if "connection reset by peer" in low or isinstance(inner, ConnectionResetError):
                return "connection_reset", msg
        if "connection reset by peer" in low:
            return "connection_reset", msg
        if "name or service not known" in low or "getaddrinfo failed" in low:
            return "dns_failure", msg
        return "connection_error", msg
    if isinstance(exc, requests.exceptions.HTTPError):
        resp = exc.response
        code = resp.status_code if resp is not None else None
        if code == 403:
            return "http_403", str(exc)
        if code == 404:
            return "http_404", str(exc)
        return "other_http_error", str(exc)
    return exc.__class__.__name__, str(exc)


def attempt_candidate(url: str) -> dict:
    """One attempt at one already-expanded candidate URL. Returns a result dict."""
    started = dt.datetime.now(dt.timezone.utc)
    try:
        resp = requests.get(url, timeout=TIMEOUT_S, headers=DEFAULT_HEADERS)
        resp.raise_for_status()
        body = resp.content
        return {
            "ok": True,
            "resolved_url": resp.url,
            "http_status": resp.status_code,
            "content_type": resp.headers.get("Content-Type", ""),
            "size_bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "reason": "",
            "error_detail": "",
            "checked_at": started.isoformat(),
        }
    except requests.exceptions.HTTPError as exc:
        reason, detail = classify_exception(exc)
        code = exc.response.status_code if exc.response is not None else None
        return {
            "ok": False,
            "resolved_url": url,
            "http_status": code,
            "content_type": "",
            "size_bytes": None,
            "sha256": "",
            "reason": reason,
            "error_detail": detail,
            "checked_at": started.isoformat(),
        }
    except Exception as exc:  # noqa: BLE001 - must classify every failure mode
        reason, detail = classify_exception(exc)
        return {
            "ok": False,
            "resolved_url": url,
            "http_status": None,
            "content_type": "",
            "size_bytes": None,
            "sha256": "",
            "reason": reason,
            "error_detail": detail,
            "checked_at": started.isoformat(),
        }


def check_url_with_retries(url: str) -> dict:
    """Check one raw URL using the pipeline's own candidate-chain expansion,
    retrying the whole chain up to RETRIES times, RETRY_DELAY_S apart, on
    overall failure. Returns the result of the final attempt plus a list of
    per-attempt outcomes for transparency.
    """
    candidates = _candidate_urls(url)
    attempts_log: list[dict] = []
    last_result: dict | None = None

    for attempt_no in range(1, RETRIES + 1):
        chain_result = None
        for cand in candidates:
            res = attempt_candidate(cand)
            attempts_log.append({"attempt": attempt_no, "candidate": cand, **res})
            if res["ok"]:
                chain_result = res
                break
            chain_result = res  # keep the last failure if all candidates fail
        last_result = chain_result
        if chain_result and chain_result["ok"]:
            break
        if attempt_no < RETRIES:
            time.sleep(RETRY_DELAY_S)

    assert last_result is not None
    last_result["attempts_log"] = attempts_log
    last_result["num_attempts"] = len(attempts_log)
    last_result["candidates_tried"] = candidates
    return last_result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--output-summary", type=Path, default=DEFAULT_OUT_SUMMARY)
    parser.add_argument("--limit-crosswalks", type=int, default=None, help="debug: only check the first N crosswalks")
    args = parser.parse_args()

    crosswalk_msc_ids = load_crosswalk_msc_ids()
    if args.limit_crosswalks:
        crosswalk_msc_ids = dict(list(crosswalk_msc_ids.items())[: args.limit_crosswalks])

    client = RDAMSCClient()

    rows: list[dict] = []
    per_crosswalk_outcomes: dict[str, list[bool]] = defaultdict(list)

    for crosswalk_id, msc_id in sorted(crosswalk_msc_ids.items()):
        try:
            locations = fetch_locations(client, msc_id)
        except Exception as exc:  # noqa: BLE001
            print(f"[{crosswalk_id}] FAILED to fetch RDAMSC detail record: {exc}", file=sys.stderr)
            rows.append(
                {
                    "crosswalk_id": crosswalk_id,
                    "msc_id": msc_id,
                    "url": "",
                    "host": "",
                    "http_status": "",
                    "reason": "rdamsc_detail_fetch_error",
                    "exception_class": exc.__class__.__name__,
                    "error_detail": str(exc),
                    "content_type": "",
                    "size_bytes": "",
                    "sha256": "",
                    "resolved_url": "",
                    "num_attempts": 0,
                    "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
            )
            continue

        urls = [loc.get("url", "") for loc in locations if loc.get("url")]
        if not urls:
            print(f"[{crosswalk_id}] no locations/urls in RDAMSC record")
            continue

        for url in urls:
            print(f"[{crosswalk_id}] checking {url} ...", flush=True)
            result = check_url_with_retries(url)
            host = urlparse(url).netloc
            ok = bool(result["ok"])
            per_crosswalk_outcomes[crosswalk_id].append(ok)
            rows.append(
                {
                    "crosswalk_id": crosswalk_id,
                    "msc_id": msc_id,
                    "url": url,
                    "host": host,
                    "http_status": result.get("http_status") or "",
                    "reason": "ok" if ok else result.get("reason", ""),
                    "exception_class": "" if ok else result.get("reason", ""),
                    "error_detail": result.get("error_detail", ""),
                    "content_type": result.get("content_type", ""),
                    "size_bytes": result.get("size_bytes") if result.get("size_bytes") is not None else "",
                    "sha256": result.get("sha256", ""),
                    "resolved_url": result.get("resolved_url", ""),
                    "num_attempts": result.get("num_attempts", 0),
                    "checked_at": result.get("checked_at", ""),
                }
            )
            print(f"    -> {'OK' if ok else result.get('reason')} ({result.get('num_attempts')} attempts)", flush=True)

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "crosswalk_id",
        "msc_id",
        "url",
        "host",
        "http_status",
        "reason",
        "exception_class",
        "error_detail",
        "content_type",
        "size_bytes",
        "sha256",
        "resolved_url",
        "num_attempts",
        "checked_at",
    ]
    with args.output_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    fetched = sum(1 for r in rows if r["reason"] == "ok")
    failed = total - fetched
    by_host_failed = Counter(r["host"] for r in rows if r["reason"] != "ok")
    by_reason_failed = Counter(r["reason"] for r in rows if r["reason"] != "ok")

    all_fetched, some_fetched, none_fetched = [], [], []
    for cid, outcomes in sorted(per_crosswalk_outcomes.items()):
        if all(outcomes):
            all_fetched.append(cid)
        elif any(outcomes):
            some_fetched.append(cid)
        else:
            none_fetched.append(cid)

    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_urls": total,
        "fetched": fetched,
        "failed": failed,
        "failed_by_host": dict(by_host_failed.most_common()),
        "failed_by_reason": dict(by_reason_failed.most_common()),
        "crosswalks_all_fetched": all_fetched,
        "crosswalks_some_fetched": some_fetched,
        "crosswalks_none_fetched": none_fetched,
        "crosswalks_checked": len(per_crosswalk_outcomes),
    }
    args.output_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
