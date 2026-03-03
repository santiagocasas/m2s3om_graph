import json
import re
from pathlib import Path
from typing import Callable, cast

from kaigraph.db import (
    ArtifactChunkRecord,
    ArtifactDocumentRecord,
    CrosswalkBundle,
    CrosswalkRecord,
    CrosswalkStore,
    ElementRecord,
    EvidenceRecord,
    MappingRuleRecord,
    MappingType,
    StandardRecord,
    stable_id,
)
from kaigraph.ingest.pdf_crosswalk_parser import parse_mapping_page_texts
from kaigraph.sssom import write_bundle_sssom

from .api import RDAMSCClient
from .artifacts import (
    ArtifactFetchError,
    ArtifactText,
    artifact_extension,
    fetch_artifact_text,
)
from .llm_extract import extract_mapping_candidates
from .llm_extract import blablador_enabled, configured_llm_model

_DC_HEADING_RE = re.compile(r"^\s*([A-Za-z][A-Za-z\s]+?)\s+--\s+")
_MARC_FIELD_RE = re.compile(r"\b(\d{3})\s*([0-9#])([0-9#])?\$([0-9a-z])")


def _slug_term(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return cleaned or "term"


def _local_id_from_msc(mscid: str) -> str:
    return "rdamsc_" + mscid.replace("msc:", "")


def _first_doi(payload: dict[str, object]) -> str | None:
    identifiers = payload.get("identifiers")
    if not isinstance(identifiers, list):
        return None
    for item in identifiers:
        if not isinstance(item, dict):
            continue
        if str(item.get("scheme", "")).upper() == "DOI":
            value = str(item.get("id", "")).strip()
            if value:
                return value
    return None


def _latest_version(payload: dict[str, object]) -> str | None:
    versions = payload.get("versions")
    if not isinstance(versions, list) or not versions:
        return None
    last = versions[-1]
    if not isinstance(last, dict):
        return None
    value = str(last.get("number", "")).strip()
    return value or None


def _primary_doc_uri(mapping_payload: dict[str, object]) -> str | None:
    locations = mapping_payload.get("locations")
    if not isinstance(locations, list):
        return None
    urls: list[str] = []
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        url = str(loc.get("url", "")).strip()
        if url:
            urls.append(url)
    if not urls:
        return None

    def score(url: str) -> tuple[int, str]:
        lower = url.lower()
        if lower.endswith(".pdf"):
            return (0, lower)
        if lower.endswith((".html", ".htm")):
            return (1, lower)
        if lower.endswith((".txt", ".xml", ".xsl", ".xslt")):
            return (2, lower)
        return (5, lower)

    return sorted(urls, key=score)[0]


def _standard_from_entity(entity: dict[str, object]) -> StandardRecord | None:
    mscid = str(entity.get("mscid", "")).strip()
    if not mscid.startswith("msc:"):
        return None
    name = str(entity.get("title") or entity.get("name") or entity.get("slug") or mscid)
    uri = str(entity.get("uri", "")).strip()
    urls: dict[str, str] = {}
    if uri:
        urls["api"] = uri
    locations = entity.get("locations")
    if isinstance(locations, list):
        for index, loc in enumerate(locations, start=1):
            if not isinstance(loc, dict):
                continue
            url = str(loc.get("url", "")).strip()
            if not url:
                continue
            key = (
                str(loc.get("type", f"location_{index}"))
                .strip()
                .lower()
                .replace(" ", "_")
            )
            urls[key] = url

    return StandardRecord(
        id=_local_id_from_msc(mscid),
        name=name,
        namespace="rdamsc",
        version=_latest_version(entity),
        urls=urls,
        external_ids={"msc_id": mscid},
    )


def _source_target_entities(
    mapping_payload: dict[str, object],
) -> tuple[dict[str, object] | None, dict[str, object] | None]:
    related = mapping_payload.get("relatedEntities")
    if not isinstance(related, list):
        return (None, None)
    source_entity: dict[str, object] | None = None
    target_entity: dict[str, object] | None = None
    for item in related:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        entity = item.get("data")
        if not isinstance(entity, dict):
            continue
        if role == "input scheme" and source_entity is None:
            source_entity = entity
        if role == "output scheme" and target_entity is None:
            target_entity = entity
    return (source_entity, target_entity)


def sync_rdamsc_catalog(
    store: CrosswalkStore, client: RDAMSCClient | None = None
) -> int:
    client = client or RDAMSCClient()
    store.apply_schema()

    count = 0
    for item in client.list_mappings(page_size=200):
        uri = str(item.get("uri", "")).strip()
        if not uri:
            continue
        detail_response = client.get_json_by_url(uri)
        detail_payload = detail_response.get("data")
        if not isinstance(detail_payload, dict):
            continue
        detail_payload = cast(dict[str, object], detail_payload)

        mscid = str(detail_payload.get("mscid", "")).strip()
        if not mscid.startswith("msc:"):
            continue
        source_entity, target_entity = _source_target_entities(detail_payload)
        if source_entity is None or target_entity is None:
            continue

        source_standard = _standard_from_entity(source_entity)
        target_standard = _standard_from_entity(target_entity)
        if source_standard is None or target_standard is None:
            continue
        _ = store.upsert_standard(source_standard)
        _ = store.upsert_standard(target_standard)

        crosswalk = CrosswalkRecord(
            id=_local_id_from_msc(mscid),
            name=str(detail_payload.get("name") or detail_payload.get("slug") or mscid),
            source_standard_id=source_standard.id,
            target_standard_id=target_standard.id,
            version=_latest_version(detail_payload),
            doi=_first_doi(detail_payload),
            msc_id=mscid,
            doc_uri=_primary_doc_uri(detail_payload),
        )
        _ = store.upsert_crosswalk(crosswalk)
        count += 1

    return count


def _mapping_type_from_text(value: str) -> MappingType:
    try:
        return MappingType(value)
    except ValueError:
        return MappingType.DIRECT


def _merge_texts(artifacts: list[ArtifactText], max_chars: int = 140_000) -> str:
    parts: list[str] = []
    used = 0
    for artifact in artifacts:
        if not artifact.text:
            continue
        header = f"\n\n## Source: {artifact.url}\n"
        chunk = header + artifact.text
        remaining = max_chars - used
        if remaining <= 0:
            break
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
        parts.append(chunk)
        used += len(chunk)
    return "".join(parts).strip()


def _chunk_markdown(
    markdown: str,
    *,
    chunk_chars: int = 3200,
    overlap_chars: int = 320,
) -> list[str]:
    if not markdown.strip():
        return []
    if chunk_chars <= 0:
        return [markdown]
    if overlap_chars < 0:
        overlap_chars = 0
    step = max(1, chunk_chars - overlap_chars)
    out: list[str] = []
    cursor = 0
    while cursor < len(markdown):
        part = markdown[cursor : cursor + chunk_chars].strip()
        if part:
            out.append(part)
        cursor += step
    return out


def _persist_artifacts_in_kg(
    store: CrosswalkStore,
    crosswalk: CrosswalkRecord,
    artifacts: list[ArtifactText],
) -> tuple[int, int]:
    docs = 0
    chunks = 0
    for artifact in artifacts:
        extension = artifact_extension(artifact.url)
        document_id = stable_id("artifact_document", crosswalk.id, artifact.url)
        _ = store.upsert_artifact_document(
            ArtifactDocumentRecord(
                id=document_id,
                crosswalk_id=crosswalk.id,
                source_url=artifact.url,
                resolved_url=artifact.url,
                content_type=artifact.content_type,
                extension=extension,
                markdown=artifact.text,
            )
        )
        docs += 1
        for ordinal, chunk in enumerate(_chunk_markdown(artifact.text), start=1):
            _ = store.upsert_artifact_chunk(
                ArtifactChunkRecord(
                    id=stable_id("artifact_chunk", document_id, str(ordinal)),
                    document_id=document_id,
                    crosswalk_id=crosswalk.id,
                    ordinal=ordinal,
                    text=chunk,
                )
            )
            chunks += 1
    return docs, chunks


def _merged_markdown_from_kg(
    store: CrosswalkStore,
    crosswalk_id: str,
    *,
    max_chars: int = 140_000,
) -> str:
    docs = {x.id: x for x in store.list_artifact_documents(crosswalk_id)}
    chunks = store.list_artifact_chunks(crosswalk_id)
    if not chunks:
        return ""
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        doc = docs.get(chunk.document_id)
        header = f"\n\n## Source: {doc.resolved_url if doc else chunk.document_id}\n"
        block = header + chunk.text
        remaining = max_chars - used
        if remaining <= 0:
            break
        if len(block) > remaining:
            block = block[:remaining]
        parts.append(block)
        used += len(block)
    return "".join(parts).strip()


def _ingest_datacite_like_pdf(
    store: CrosswalkStore,
    crosswalk: CrosswalkRecord,
    source_standard: StandardRecord,
    artifact: ArtifactText,
) -> int:
    rows = parse_mapping_page_texts([artifact.text], doc_uri=artifact.url)
    count = 0
    source_element_by_path: dict[str, str] = {}
    for row in rows:
        source_path = row.datacite_property.strip()
        source_element_id = source_element_by_path.get(source_path)
        if source_element_id is None:
            source_element_id = stable_id("element", source_standard.id, source_path)
            source_element_by_path[source_path] = source_element_id
            _ = store.upsert_element(
                ElementRecord(
                    id=source_element_id,
                    standard_id=source_standard.id,
                    path=source_path,
                    label=source_path,
                    notes=row.notes,
                )
            )

        target_paths: list[str] = []
        if row.dublin_core.startswith("dcterms:"):
            target_paths.append(row.dublin_core)
        for case in row.cases:
            target_paths.append(case.value)

        mapping_type = row.mapping_type
        if row.dublin_core == "Not present in Dublin Core":
            mapping_type = MappingType.MISSING
        confidence = (
            0.95 if mapping_type in {MappingType.DIRECT, MappingType.MISSING} else 0.8
        )

        rule = MappingRuleRecord(
            id=stable_id(
                "mapping_rule", crosswalk.id, row.row_id, row.datacite_property
            ),
            crosswalk_id=crosswalk.id,
            source_element_id=source_element_id,
            source_paths=[source_path],
            target_paths=sorted(set(target_paths)),
            mapping_type=mapping_type,
            confidence=confidence,
            semantic_loss=mapping_type == MappingType.MISSING,
            ambiguity=mapping_type
            in {MappingType.CONDITIONAL, MappingType.AGGREGATION},
            transform={"op": "copy" if mapping_type != MappingType.MISSING else "drop"},
            notes=row.notes,
        )
        _ = store.upsert_mapping_rule(rule)
        _ = store.upsert_evidence(
            EvidenceRecord(
                id=stable_id("evidence", rule.id, str(row.page_number), row.row_id),
                mapping_rule_id=rule.id,
                source="PDF",
                doc_uri=artifact.url,
                page_number=row.page_number,
                row_id=row.row_id,
                snippet=row.snippet,
            )
        )
        count += 1
    return count


def _ingest_with_llm(
    store: CrosswalkStore,
    crosswalk: CrosswalkRecord,
    source_standard: StandardRecord,
    target_standard: StandardRecord,
    merged_markdown: str,
    evidence_doc_uri: str,
) -> int:
    if not merged_markdown:
        return 0

    extracted = extract_mapping_candidates(
        merged_markdown,
        source_standard.name,
        target_standard.name,
    )
    count = 0
    for index, item in enumerate(extracted, start=1):
        source_path = str(item.get("source_path", "")).strip()
        target_path = str(item.get("target_path", "")).strip()
        if not source_path:
            continue

        source_element_id = stable_id("element", source_standard.id, source_path)
        _ = store.upsert_element(
            ElementRecord(
                id=source_element_id,
                standard_id=source_standard.id,
                path=source_path,
                label=source_path,
            )
        )

        mapping_type = _mapping_type_from_text(str(item.get("mapping_type", "direct")))
        raw_confidence = item.get("confidence", 0.7)
        try:
            confidence = float(str(raw_confidence))
        except (TypeError, ValueError):
            confidence = 0.7
        confidence = max(0.0, min(1.0, confidence))
        notes = item.get("notes")
        if notes is not None:
            notes = str(notes)
        evidence_snippet = item.get("evidence")
        if evidence_snippet is None:
            evidence_snippet = "AI-assisted extraction from mapping documentation"

        transform: dict[str, object]
        if mapping_type == MappingType.MISSING:
            transform = {"op": "drop"}
        else:
            transform = {"op": "copy"}

        rule = MappingRuleRecord(
            id=stable_id(
                "mapping_rule",
                crosswalk.id,
                source_path,
                target_path,
                str(index),
            ),
            crosswalk_id=crosswalk.id,
            source_element_id=source_element_id,
            source_paths=[source_path],
            target_paths=[target_path] if target_path else [],
            mapping_type=mapping_type,
            confidence=confidence,
            semantic_loss=mapping_type == MappingType.MISSING,
            ambiguity=mapping_type
            in {MappingType.CONDITIONAL, MappingType.AGGREGATION},
            transform=transform,
            notes=notes,
        )
        _ = store.upsert_mapping_rule(rule)
        _ = store.upsert_evidence(
            EvidenceRecord(
                id=stable_id("evidence", rule.id, "1", str(index)),
                mapping_rule_id=rule.id,
                source="LLM",
                doc_uri=evidence_doc_uri,
                page_number=1,
                row_id=str(index),
                snippet=str(evidence_snippet),
            )
        )
        count += 1

    return count


def _ingest_loc_dccross_html(
    store: CrosswalkStore,
    crosswalk: CrosswalkRecord,
    source_standard: StandardRecord,
    artifacts: list[ArtifactText],
) -> int:
    seen: set[tuple[str, str]] = set()
    source_ids: dict[str, str] = {}
    count = 0

    for artifact in artifacts:
        current_source: str | None = None
        for line_number, line in enumerate(artifact.text.splitlines(), start=1):
            heading = _DC_HEADING_RE.search(line)
            if heading:
                current_source = f"dc:{_slug_term(heading.group(1))}"
                if current_source not in source_ids:
                    source_element_id = stable_id(
                        "element", source_standard.id, current_source
                    )
                    source_ids[current_source] = source_element_id
                    _ = store.upsert_element(
                        ElementRecord(
                            id=source_element_id,
                            standard_id=source_standard.id,
                            path=current_source,
                            label=current_source,
                        )
                    )

            if current_source is None:
                continue

            for match in _MARC_FIELD_RE.finditer(line):
                tag = match.group(1)
                subfield = match.group(4)
                target_path = f"marc:{tag}${subfield}"
                key = (current_source, target_path)
                if key in seen:
                    continue
                seen.add(key)

                source_element_id = source_ids[current_source]
                rule = MappingRuleRecord(
                    id=stable_id(
                        "mapping_rule",
                        crosswalk.id,
                        current_source,
                        target_path,
                        str(line_number),
                    ),
                    crosswalk_id=crosswalk.id,
                    source_element_id=source_element_id,
                    source_paths=[current_source],
                    target_paths=[target_path],
                    mapping_type=MappingType.DIRECT,
                    confidence=0.75,
                    semantic_loss=False,
                    ambiguity=False,
                    transform={"op": "copy"},
                    notes="Deterministic extraction from LOC Dublin Core to MARC crosswalk.",
                )
                _ = store.upsert_mapping_rule(rule)
                _ = store.upsert_evidence(
                    EvidenceRecord(
                        id=stable_id(
                            "evidence", rule.id, str(line_number), target_path
                        ),
                        mapping_rule_id=rule.id,
                        source="HTML",
                        doc_uri=artifact.url,
                        page_number=1,
                        row_id=str(line_number),
                        snippet=line.strip()[:400],
                    )
                )
                count += 1

    return count


def sssom_output_path(base_dir: Path, crosswalk_id: str) -> Path:
    return base_dir / f"{crosswalk_id}.sssom.tsv"


def ingest_rdamsc_crosswalk_docs(
    store: CrosswalkStore,
    crosswalk_id: str,
    output_dir: Path,
    client: RDAMSCClient | None = None,
    logger: Callable[[str], None] | None = None,
) -> dict[str, object]:
    def emit(message: str) -> None:
        if logger is not None:
            logger(message)

    client = client or RDAMSCClient()
    crosswalks = {x.id: x for x in store.list_crosswalks()}
    crosswalk = crosswalks.get(crosswalk_id)
    if crosswalk is None:
        return {"ok": False, "reason": "crosswalk_not_found"}
    if not crosswalk.msc_id:
        return {"ok": False, "reason": "missing_msc_id"}

    emit(f"[{crosswalk.msc_id}] Inspecting mapping metadata")
    detail = client.get_mapping_detail(crosswalk.msc_id)
    locations = detail.get("locations")
    if not isinstance(locations, list):
        return {"ok": False, "reason": "no_locations"}

    artifacts: list[ArtifactText] = []
    artifact_checks: list[dict[str, object]] = []
    skipped: list[str] = []
    for loc in locations:
        if not isinstance(loc, dict):
            continue
        url = str(loc.get("url", "")).strip()
        if not url:
            continue
        check: dict[str, object] = {
            "url": url,
            "extension": artifact_extension(url),
            "location_type": str(loc.get("type", "")),
        }
        emit(
            f"[{crosswalk.msc_id}] Fetching artifact: {url} (ext={check['extension']})"
        )
        try:
            artifact = fetch_artifact_text(url)
            artifacts.append(artifact)
            check["status"] = "fetched"
            check["resolved_url"] = artifact.url
            check["content_type"] = artifact.content_type
            check["text_chars"] = len(artifact.text)
            emit(
                f"[{crosswalk.msc_id}] Fetched OK: {artifact.url} ({len(artifact.text)} chars)"
            )
        except ArtifactFetchError as exc:
            check["status"] = exc.reason
            check["error"] = str(exc)
            check["http_status"] = exc.status_code
            emit(f"[{crosswalk.msc_id}] Fetch failed: {url} ({exc})")
            skipped.append(url)
        except Exception as exc:
            check["status"] = "fetch_error"
            check["error"] = str(exc)
            emit(f"[{crosswalk.msc_id}] Fetch failed: {url} ({exc})")
            skipped.append(url)
        artifact_checks.append(check)

    if not artifacts:
        had_fetch_errors = any(
            x.get("status") == "fetch_error" for x in artifact_checks
        )
        had_conversion_errors = any(
            x.get("status") == "conversion_error" for x in artifact_checks
        )
        reason = "artifacts_unsupported"
        if had_fetch_errors and not had_conversion_errors:
            reason = "artifacts_unreachable"
        elif had_fetch_errors and had_conversion_errors:
            reason = "artifacts_unreachable"
        return {
            "ok": False,
            "reason": reason,
            "crosswalk_id": crosswalk.id,
            "skipped": skipped,
            "artifact_checks": artifact_checks,
        }

    standards = {x.id: x for x in store.list_standards()}
    source_standard = standards.get(crosswalk.source_standard_id)
    target_standard = standards.get(crosswalk.target_standard_id)
    if source_standard is None or target_standard is None:
        return {"ok": False, "reason": "missing_standards"}

    docs_count, chunks_count = _persist_artifacts_in_kg(store, crosswalk, artifacts)
    emit(
        f"[{crosswalk.msc_id}] Ingested artifacts into KG as markdown "
        f"(documents={docs_count}, chunks={chunks_count})"
    )
    merged_markdown = _merged_markdown_from_kg(store, crosswalk.id)
    if not merged_markdown:
        merged_markdown = _merge_texts(artifacts)
    evidence_doc_uri = artifacts[0].url if artifacts else (crosswalk.doc_uri or "")

    inserted_rules = 0
    artifact_urls = [x.url.lower() for x in artifacts]
    first_url = artifact_urls[0]
    strategy = "llm"
    if "datacite_dublincore_mapping" in first_url and first_url.endswith(".pdf"):
        strategy = "deterministic_pdf"
        emit(f"[{crosswalk.msc_id}] Parsing deterministic PDF mapping")
        inserted_rules = _ingest_datacite_like_pdf(
            store,
            crosswalk,
            source_standard,
            artifacts[0],
        )
    elif any("loc.gov/marc/dccross" in url for url in artifact_urls):
        strategy = "deterministic_html_loc"
        emit(f"[{crosswalk.msc_id}] Parsing deterministic LOC HTML crosswalk")
        inserted_rules = _ingest_loc_dccross_html(
            store,
            crosswalk,
            source_standard,
            artifacts,
        )
        if inserted_rules == 0:
            strategy = "llm"
            backend = (
                f"Blablador model={configured_llm_model()}"
                if blablador_enabled()
                else "heuristic fallback (BLABLADOR_API_KEY not set)"
            )
            emit(
                f"[{crosswalk.msc_id}] Deterministic parser found 0 rules; "
                f"falling back to LLM extraction ({backend})"
            )
            inserted_rules = _ingest_with_llm(
                store,
                crosswalk,
                source_standard,
                target_standard,
                merged_markdown,
                evidence_doc_uri,
            )
    else:
        backend = (
            f"Blablador model={configured_llm_model()}"
            if blablador_enabled()
            else "heuristic fallback (BLABLADOR_API_KEY not set)"
        )
        emit(
            f"[{crosswalk.msc_id}] Running LLM extraction on merged artifact text ({backend})"
        )
        inserted_rules = _ingest_with_llm(
            store,
            crosswalk,
            source_standard,
            target_standard,
            merged_markdown,
            evidence_doc_uri,
        )

    bundle = store.get_crosswalk_bundle(crosswalk.id)
    if bundle is None:
        return {"ok": False, "reason": "bundle_missing_after_ingest"}

    out_path = sssom_output_path(output_dir, crosswalk.id)
    if not bundle.rules:
        if out_path.exists():
            out_path.unlink()
        emit(
            f"[{crosswalk.msc_id}] No rules extracted; no authoritative SSSOM file created"
        )
        return {
            "ok": False,
            "reason": "no_rules_extracted",
            "crosswalk_id": crosswalk.id,
            "inserted_rules": inserted_rules,
            "artifact_documents": docs_count,
            "artifact_chunks": chunks_count,
            "artifacts": [x.url for x in artifacts],
            "skipped": skipped,
            "artifact_checks": artifact_checks,
            "strategy": strategy,
        }

    emit(
        f"[{crosswalk.msc_id}] Loading {len(bundle.rules)} rules into KG/DB and writing SSSOM"
    )
    _ = write_bundle_sssom(bundle, out_path)
    emit(f"[{crosswalk.msc_id}] Wrote SSSOM: {out_path}")

    return {
        "ok": True,
        "crosswalk_id": crosswalk.id,
        "inserted_rules": inserted_rules,
        "total_rules": len(bundle.rules),
        "artifact_documents": docs_count,
        "artifact_chunks": chunks_count,
        "artifacts": [x.url for x in artifacts],
        "skipped": skipped,
        "artifact_checks": artifact_checks,
        "strategy": strategy,
        "sssom_path": str(out_path),
    }


def ensure_sssom_for_bundle(bundle: CrosswalkBundle, output_dir: Path) -> Path:
    path = sssom_output_path(output_dir, bundle.crosswalk.id)
    _ = write_bundle_sssom(bundle, path)
    return path


def dump_result_json(result: dict[str, object]) -> str:
    return json.dumps(result, indent=2, ensure_ascii=True)
