#!/usr/bin/env python3
"""Build snapshot-specific publication figures and an audit report from exports."""

from __future__ import annotations

import argparse
import csv
import io
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "figures"
PAPER_VALUES = {
    "Crosswalk catalog size": "37",
    "Outcomes (processed/unreachable/no rules)": "19/11/7",
    "Artifact URLs checked": "45",
    "Artifacts fetched": "32",
    "SSSOM rows": "993",
    "Predicates exact/related/broad/narrow": "800/152/28/13",
    "LLM runs with/without rules": "13/7",
    "Deterministic runs": "2",
    "Graph nodes/edges": "20/23",
    "Benchmark field coverage/value overlap": "30.9% / 16.7%",
}
COLORS = {
    "processed": "#009E73", "unreachable": "#D55E00", "no_rules": "#E69F00",
    "fetched": "#009E73", "failed": "#D55E00", "noaa": "#CC79A7",
    "nasa": "#0072B2", "datacite": "#E69F00", "other": "#999999",
    "exact": "#0072B2", "related": "#E69F00", "broad": "#009E73",
    "narrow": "#CC79A7", "llm_rules": "#0072B2", "llm_zero": "#D55E00",
    "deterministic": "#009E73", "coverage": "#0072B2", "overlap": "#E69F00",
}
plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 8, "axes.titlesize": 9,
    "axes.labelsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300,
})


class Snapshot:
    def __init__(self, commit: str):
        self.commit = subprocess.check_output(
            ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"], cwd=ROOT, text=True
        ).strip()
        self.short = self.commit[:8]
        date = subprocess.check_output(
            ["git", "show", "-s", "--format=%cI", self.commit], cwd=ROOT, text=True
        ).strip()
        self.date = datetime.fromisoformat(date.replace("Z", "+00:00")).date().isoformat()
        self.is_head = commit.upper() == "HEAD"

    def read(self, rel: str) -> str | None:
        proc = subprocess.run(
            ["git", "show", f"{self.commit}:{rel}"], cwd=ROOT, text=True,
            capture_output=True,
        )
        return proc.stdout if proc.returncode == 0 else None

    def paths(self, pattern: str) -> list[str]:
        proc = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", self.commit],
            cwd=ROOT, text=True, capture_output=True,
        )
        # git ls-tree pathspecs treat '*.tsv' literally; filter a full tree listing instead.
        if proc.returncode:
            return []
        paths = proc.stdout.splitlines()
        if pattern == "exports/sssom/*.sssom.tsv":
            return sorted(p for p in paths if p.startswith("exports/sssom/") and p.endswith(".sssom.tsv"))
        if pattern == "exports/benchmark/*.json":
            return sorted(p for p in paths if p.startswith("exports/benchmark/") and p.endswith(".json"))
        return paths


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse_csv(text: str | None, source: str) -> list[dict[str, str]]:
    require(text is not None, f"Missing required snapshot input: {source}")
    return list(csv.DictReader(io.StringIO(text)))


def num(row: dict[str, str], *keys: str) -> int:
    for key in keys:
        value = row.get(key, "")
        if value:
            try:
                return int(float(value))
            except ValueError:
                pass
    return 0


def load_data(snap: Snapshot) -> dict:
    cwpath = "exports/pipeline/latest/rdamsc_crosswalks.csv"
    apath = "exports/pipeline/latest/rdamsc_artifacts.csv"
    crosswalks = parse_csv(snap.read(cwpath), cwpath)
    artifacts = parse_csv(snap.read(apath), apath)
    statuses = Counter(r["status"] for r in crosswalks)
    outcomes = {
        "processed": statuses.get("ready", 0),
        "unreachable": statuses.get("failed_unreachable", 0),
        "no_rules": statuses.get("failed_parse", 0),
    }
    fetched = [r for r in artifacts if (r.get("check_status") or r.get("status")) in {"fetched", "ready"}]
    failed = [r for r in artifacts if r not in fetched]
    host_counts = Counter((r.get("host") or urlparse(r.get("url", "")).netloc).lower() for r in failed)
    host_groups = {
        "noaa": sum(v for h, v in host_counts.items() if "ncddc.noaa.gov" in h),
        "nasa": sum(v for h, v in host_counts.items() if "gcmd.nasa.gov" in h),
        "datacite": sum(v for h, v in host_counts.items() if h == "schema.datacite.org"),
    }
    host_groups["other"] = len(failed) - sum(host_groups.values())

    sssom_paths = snap.paths("exports/sssom/*.sssom.tsv")
    predicates: Counter[str] = Counter()
    file_ids: set[str] = set()
    total_rows = 0
    for path in sssom_paths:
        text = snap.read(path)
        if text is None:
            continue
        body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
        rows = list(csv.DictReader(io.StringIO(body), delimiter="\t"))
        total_rows += len(rows)
        predicates.update(r.get("predicate_id", "") for r in rows)
        if path.rsplit("/", 1)[-1].startswith("rdamsc_"):
            file_ids.add(path.rsplit("/", 1)[-1].removeprefix("rdamsc_").removesuffix(".sssom.tsv"))
    pred = {
        "exact": predicates.get("skos:exactMatch", 0) + predicates.get("http://www.w3.org/2004/02/skos/core#exactMatch", 0),
        "related": predicates.get("skos:relatedMatch", 0) + predicates.get("http://www.w3.org/2004/02/skos/core#relatedMatch", 0),
        "broad": predicates.get("skos:broadMatch", 0) + predicates.get("http://www.w3.org/2004/02/skos/core#broadMatch", 0),
        "narrow": predicates.get("skos:narrowMatch", 0) + predicates.get("http://www.w3.org/2004/02/skos/core#narrowMatch", 0),
    }
    strategies = Counter(r.get("strategy", "") for r in crosswalks)
    llm_rows = [r for r in crosswalks if r.get("strategy", "").lower() == "llm"]
    llm_with = sum(1 for r in llm_rows if num(r, "inserted_rules", "total_rules", "backfilled_rules") > 0)
    llm_without = len(llm_rows) - llm_with
    det = sum(v for k, v in strategies.items() if "deterministic" in k.lower())

    gpath = "exports/graph/crosswalk_graph.json"
    graph_text = snap.read(gpath)
    graph = json.loads(graph_text) if graph_text else None

    bench_files = snap.paths("exports/benchmark/*.json")
    benchmark = None
    benchmark_source = None
    for path in bench_files:
        if "awi" not in path.lower() or path.endswith(".failures.json"):
            continue
        payload = json.loads(snap.read(path) or "{}")
        aggregate = payload.get("aggregate", payload)
        benchmark = {
            "coverage": aggregate.get("avg_field_coverage"),
            "overlap": aggregate.get("avg_value_overlap"),
            "cases": aggregate.get("cases", payload.get("cases_count")),
            "failures": payload.get("failures") if isinstance(payload.get("failures"), int) else None,
        }
        if isinstance(payload.get("failures"), list):
            benchmark["failures"] = len(payload["failures"])
        failures_text = snap.read(path.removesuffix(".json") + ".failures.json")
        if failures_text:
            try:
                benchmark["failures"] = len(json.loads(failures_text))
            except (ValueError, TypeError):
                benchmark["failures"] = None
        benchmark_source = path
        break

    ready_no_file = sorted(r["crosswalk_id"] for r in crosswalks if r["status"] == "ready" and r["crosswalk_id"].removeprefix("rdamsc_") not in file_ids)
    file_not_ready = sorted(r["crosswalk_id"] for r in crosswalks if r["status"] != "ready" and r["crosswalk_id"].removeprefix("rdamsc_") in file_ids)
    return locals()


def save(fig, stem: str, snap: Snapshot) -> list[str]:
    stamp = "" if snap.is_head else f"_{snap.short}"
    base = OUT / f"{stem}{stamp}"
    fig.subplots_adjust(top=min(fig.subplotpars.top, 0.88))
    fig.text(0.99, 0.99, f"Source: {snap.commit} · {snap.date}", ha="right", va="top", fontsize=5, color="#555555")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    return [str(base.with_suffix(".pdf").relative_to(ROOT)), str(base.with_suffix(".png").relative_to(ROOT))]


def make_figures(d: dict, snap: Snapshot) -> tuple[list[str], list[str]]:
    files: list[str] = []
    failures: list[str] = []
    require(sum(d["outcomes"].values()) > 0, "No crosswalk outcomes to plot")

    # Donut: retain the legacy basename because it is the same outcome plot.
    fig, ax = plt.subplots(figsize=(3.35, 2.35))
    vals = [d["outcomes"][k] for k in ("processed", "unreachable", "no_rules")]
    labels = [f"{name}\n{v} ({v / sum(vals):.1%})" for name, v in zip(("processed", "artifact unreachable", "no rules extractable"), vals)]
    wedges, _ = ax.pie(vals, startangle=90, counterclock=False, colors=[COLORS["processed"], COLORS["unreachable"], COLORS["no_rules"]], wedgeprops={"width": .38, "edgecolor": "white"})
    for wedge, label in zip(wedges, labels):
        angle = (wedge.theta1 + wedge.theta2) / 2
        import math
        ax.text(.79 * math.cos(math.radians(angle)), .79 * math.sin(math.radians(angle)), label, ha="center", va="center", fontsize=6.5)
    ax.text(0, 0, f"{sum(vals)}", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.set(aspect="equal")
    files += save(fig, "fig_pipeline_status", snap)

    fig, ax = plt.subplots(figsize=(3.35, 1.7))
    stacks = [("fetched", len(d["fetched"]), COLORS["fetched"]), ("NOAA NCDDC", d["host_groups"]["noaa"], COLORS["noaa"]), ("NASA GCMD", d["host_groups"]["nasa"], COLORS["nasa"]), ("schema.datacite.org", d["host_groups"]["datacite"], COLORS["datacite"]), ("other failed", d["host_groups"]["other"], COLORS["other"])]
    left = 0
    for label, value, color in stacks:
        ax.barh([0], [value], left=left, color=color, edgecolor="white", height=.46)
        if value:
            ax.text(left + value / 2, 0, str(value), ha="center", va="center", fontsize=7, color="white" if color != COLORS["datacite"] else "black")
        left += value
    ax.set_xlim(0, max(left, 1)); ax.set_yticks([]); ax.set_xlabel(f"Artifact URLs (n={len(d['artifacts'])})")
    ax.spines[["top", "right", "left"]].set_visible(False)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=color, label=f"{label} ({value})") for label, value, color in stacks], loc="lower center", bbox_to_anchor=(.5, .02), ncol=3, frameon=False, fontsize=6.2, columnspacing=.8, handlelength=1)
    fig.subplots_adjust(bottom=.42)
    files += save(fig, "fig_artifact_fetch", snap)

    fig, ax = plt.subplots(figsize=(3.35, 1.85))
    predkeys = [("exact", "exactMatch"), ("related", "relatedMatch / missing"), ("broad", "broadMatch"), ("narrow", "narrowMatch")]
    total = sum(d["pred"].values()); left = 0
    for key, label in predkeys:
        value = d["pred"][key]
        ax.barh([0], [value], left=left, color=COLORS[key], edgecolor="white", height=.48)
        if value >= total * .07:
            ax.text(left + value/2, 0, str(value), ha="center", va="center", fontsize=7, color="white" if key == "exact" else "black")
        left += value
    ax.set_xlim(0, max(total, 1)); ax.set_yticks([]); ax.set_xlabel(f"SSSOM mapping rows (n={total})")
    ax.spines[["top", "right", "left"]].set_visible(False)
    from matplotlib.patches import Patch
    pred_handles = [Patch(color=COLORS[key], label=f"{label}: {d['pred'][key]} ({d['pred'][key]/total:.1%})") for key, label in predkeys]
    fig.legend(handles=pred_handles, loc="lower center", bbox_to_anchor=(.5, .015), ncol=2, frameon=False, fontsize=6.3, columnspacing=.8, handlelength=1)
    fig.subplots_adjust(bottom=.42)
    files += save(fig, "fig_predicates", snap)

    fig, ax = plt.subplots(figsize=(3.35, 1.65))
    names = ["LLM with rules", "LLM without rules", "Deterministic"]
    values = [d["llm_with"], d["llm_without"], d["det"]]
    colors = [COLORS["llm_rules"], COLORS["llm_zero"], COLORS["deterministic"]]
    ys = list(range(3)); ax.barh(ys, values, color=colors, height=.55)
    ax.set_yticks(ys, names); ax.invert_yaxis(); ax.set_xlabel("Crosswalk runs")
    for y, value in zip(ys, values): ax.text(value + .15, y, str(value), va="center", fontsize=8)
    ax.set_xlim(0, max(values, default=0) * 1.22 + 1); ax.spines[["top", "right", "left"]].set_visible(False)
    files += save(fig, "fig_strategy", snap)

    if d["benchmark"] is None or d["benchmark"]["coverage"] is None:
        failures.append("fig_benchmark: no AWI benchmark JSON exists in this snapshot")
    else:
        fig, ax = plt.subplots(figsize=(3.35, 1.7))
        bvals = [d["benchmark"]["coverage"] * 100, d["benchmark"]["overlap"] * 100]
        ax.barh([0, 1], bvals, color=[COLORS["coverage"], COLORS["overlap"]], height=.55)
        ax.set_yticks([0, 1], ["Field coverage", "Value overlap"]); ax.invert_yaxis(); ax.set_xlim(0, 105); ax.set_xlabel("Percent")
        for y, value in enumerate(bvals): ax.text(value + 1, y, f"{value:.1f}%", va="center", fontsize=8)
        failtext = str(d["benchmark"]["failures"]) if d["benchmark"]["failures"] is not None else "not recorded"
        fig.suptitle(f"AWI benchmark · n={d['benchmark']['cases']} · failures={failtext}", fontsize=8, y=.94)
        ax.spines[["top", "right", "left"]].set_visible(False)
        files += save(fig, "fig_benchmark", snap)

    # Optional wide overview combines the five panels without obscuring tiny segments.
    fig, axs = plt.subplots(2, 3, figsize=(6.7, 4.4))
    for axis in axs.flat: axis.axis("off")
    axs[0, 0].axis("on"); axs[0, 0].pie(vals if False else [d["outcomes"][k] for k in ("processed", "unreachable", "no_rules")], colors=[COLORS["processed"], COLORS["unreachable"], COLORS["no_rules"]], wedgeprops={"width": .4})
    axs[0, 0].text(0, 0, str(sum(d["outcomes"].values())), ha="center", va="center")
    axs[0, 1].axis("on"); axs[0, 1].barh([0], [len(d["fetched"])], color=COLORS["fetched"]); axs[0, 1].set_title("Fetched URLs")
    axs[0, 2].axis("on"); axs[0, 2].barh([0], list(d["pred"].values()), color=[COLORS[k] for k in ("exact", "related", "broad", "narrow")], left=[0, d["pred"]["exact"], d["pred"]["exact"]+d["pred"]["related"], d["pred"]["exact"]+d["pred"]["related"]+d["pred"]["broad"]]); axs[0, 2].set_title("SSSOM predicates")
    axs[1, 0].axis("on"); axs[1, 0].barh([0,1,2], values if False else [d["llm_with"], d["llm_without"], d["det"]], color=colors); axs[1,0].set_title("Extraction strategy")
    if d["benchmark"]:
        axs[1, 1].axis("on"); axs[1, 1].barh([0,1], [d["benchmark"]["coverage"], d["benchmark"]["overlap"]], color=[COLORS["coverage"], COLORS["overlap"]]); axs[1,1].set_title("Benchmark")
    else:
        axs[1, 1].text(.5, .5, "Benchmark unavailable", ha="center", va="center")
    fig.text(.5, .51, f"{snap.short} · {snap.date}", ha="center", fontsize=7)
    files += save(fig, "fig_overview", snap)
    return files, failures


def report(d: dict, snap: Snapshot, files: list[str]) -> str:
    outcomes = d["outcomes"]
    benchmark = d["benchmark"] or {}
    graph = d["graph"] or {"nodes": [], "edges": []}
    values = [
        ("Crosswalk catalog size", len(d["crosswalks"]), "exports/pipeline/latest/rdamsc_crosswalks.csv"),
        ("Outcomes (processed / unreachable / no rules)", f"{outcomes['processed']}/{outcomes['unreachable']}/{outcomes['no_rules']}", "exports/pipeline/latest/rdamsc_crosswalks.csv"),
        ("Artifact URLs / fetched", f"{len(d['artifacts'])} / {len(d['fetched'])}", "exports/pipeline/latest/rdamsc_artifacts.csv"),
        ("SSSOM files / rows", f"{len(d['sssom_paths'])} / {d['total_rows']}", "exports/sssom/*.sssom.tsv"),
        ("Predicates exact / related / broad / narrow", "/".join(str(d["pred"][k]) for k in ("exact", "related", "broad", "narrow")), "exports/sssom/*.sssom.tsv"),
        ("LLM with rules / without rules", f"{d['llm_with']}/{d['llm_without']}", "exports/pipeline/latest/rdamsc_crosswalks.csv"),
        ("Deterministic runs", d["det"], "exports/pipeline/latest/rdamsc_crosswalks.csv"),
        ("Graph nodes / edges", f"{len(graph['nodes'])}/{len(graph['edges'])}" if d["graph"] else "unavailable", "exports/graph/crosswalk_graph.json"),
        ("Benchmark field coverage / value overlap (cases / failures)", f"{benchmark.get('coverage', 'unavailable')} / {benchmark.get('overlap', 'unavailable')} (n={benchmark.get('cases', 'unavailable')}, failures={benchmark.get('failures') if benchmark.get('failures') is not None else 'not recorded'})", d.get("benchmark_source", "unavailable in this snapshot")),
    ]
    lines = [f"# Table 2 figure data — {snap.short} ({snap.date})", "", f"Commit: `{snap.commit}`  ", f"Commit date: `{snap.date}`  ", f"Regeneration: `uv run python scripts/make_paper_figures.py --commit {snap.commit}`", "", "## Computed values", "", "| Table 2 item | Computed value | Source file | Command |", "|---|---:|---|---|"]
    for label, value, source in values:
        source = source or "unavailable in this snapshot"
        if source.startswith("unavailable"):
            cmd = "not present in this snapshot"
        elif "*" in source:
            cmd = f"uv run python scripts/make_paper_figures.py --commit {snap.commit}"
        else:
            cmd = f"git show {snap.commit}:{source}"
        lines.append(f"| {label} | {value} | `{source}` | `{cmd}` |")
    lines += ["", "Artifact fetch detail: " + ", ".join(f"{k}={v}" for k, v in d["host_groups"].items()) + f"; failed={len(d['failed'])}.", "", "## Differences to paper values", "", "| Item | Paper value | Computed | Result |", "|---|---:|---:|---|"]
    computed = {
        "Crosswalk catalog size": str(len(d["crosswalks"])),
        "Outcomes (processed/unreachable/no rules)": f"{outcomes['processed']}/{outcomes['unreachable']}/{outcomes['no_rules']}",
        "Artifact URLs checked": str(len(d["artifacts"])), "Artifacts fetched": str(len(d["fetched"])),
        "SSSOM rows": str(d["total_rows"]), "Predicates exact/related/broad/narrow": "/".join(str(d["pred"][k]) for k in ("exact","related","broad","narrow")),
        "LLM runs with/without rules": f"{d['llm_with']}/{d['llm_without']}", "Deterministic runs": str(d["det"]),
        "Graph nodes/edges": f"{len(graph['nodes'])}/{len(graph['edges'])}" if d["graph"] else "unavailable",
        "Benchmark field coverage/value overlap": f"{benchmark.get('coverage', 0)*100:.1f}% / {benchmark.get('overlap', 0)*100:.1f}%" if benchmark else "unavailable",
    }
    for label, paper in PAPER_VALUES.items():
        got = computed[label]
        lines.append(f"| {label} | {paper} | {got} | {'MATCH' if got == paper else 'MISMATCH'} |")
    lines += ["", "## Status/file inconsistencies (reported without correction)", "", f"Ready status but no `rdamsc_*.sssom.tsv`: {', '.join(d['ready_no_file']) or 'none'}.", "", f"SSSOM file present but status is non-ready: {', '.join(d['file_not_ready']) or 'none'}.", "", "## Figures", ""]
    lines += [f"- `{f}`" for f in files]
    lines += ["", "Source note: all inputs are read-only and read from the selected Git commit using `git show <commit>:<path>` (including `--commit HEAD`). Benchmark failures are shown as 'not recorded' where no matching failures field or `.failures.json` exists.", ""]
    return "\n".join(lines)


def main() -> int:
    global OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD", help="Git commit/ref to read (default: HEAD)")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        snap = Snapshot(args.commit)
        data = load_data(snap)
        files, build_failures = make_figures(data, snap)
        text = report(data, snap, files)
        report_path = OUT / ("FIGURES_REPORT.md" if snap.is_head else f"FIGURES_REPORT_{snap.short}.md")
        if build_failures:
            text += "\n\n## Figure build failures\n\n" + "\n".join(f"- {e}" for e in build_failures) + "\n"
        report_path.write_text(text, encoding="utf-8")
        print(f"Snapshot: {snap.commit} ({snap.date})")
        print(text)
        return 1 if build_failures else 0
    except Exception as exc:  # report actionable build failures to CLI and nonzero status
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
