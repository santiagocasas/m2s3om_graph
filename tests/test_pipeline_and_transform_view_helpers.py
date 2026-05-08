from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from views import pipeline as pipeline_view
from views import transform as transform_view
from m2s3om_graph.crosswalk.route import ConversionStep
from m2s3om_graph.db import CrosswalkRecord, InMemoryCrosswalkStore
from m2s3om_graph.oai.bridge import ResolvedFormat
from m2s3om_graph.oai.parser import IdentifierList, MetadataFormatInfo
from m2s3om_graph.transform.apply import TransformationReport


def test_pipeline_status_rows_extracts_reason_and_sorts(
    monkeypatch, tmp_path: Path
) -> None:
    store = InMemoryCrosswalkStore()
    first = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_c2",
            name="Second",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:c2",
        )
    )
    second = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_c1",
            name="First",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:c1",
        )
    )

    monkeypatch.setattr(pipeline_view, "ensure_store", lambda: store)
    monkeypatch.setattr(pipeline_view, "sssom_dir", lambda: tmp_path)
    monkeypatch.setattr(
        pipeline_view,
        "load_pipeline_status",
        lambda: {
            first.id: {
                "updated_at": "2026-01-01T00:00:00+00:00",
                "result": {"ok": False, "reason": "artifacts_unreachable"},
            },
            second.id: {
                "updated_at": "2026-01-02T00:00:00+00:00",
                "result": {"ok": True},
            },
        },
    )
    monkeypatch.setattr(
        pipeline_view,
        "resolve_crosswalk_status",
        lambda _store, crosswalk, _out_dir, _status_map: (
            "failed_unreachable" if crosswalk.id == first.id else "ready"
        ),
    )

    rows = pipeline_view._status_rows()
    assert [row["msc_id"] for row in rows] == ["msc:c1", "msc:c2"]
    by_id = {row["msc_id"]: row for row in rows}
    assert by_id["msc:c2"]["reason"] == "artifacts_unreachable"
    assert by_id["msc:c1"]["status"] == "SSSOM ready"


def test_transform_route_caption_and_apply_steps(monkeypatch) -> None:
    step_one = ConversionStep(
        crosswalk_id="cw1",
        crosswalk_name="CW One",
        source_standard_id="s1",
        target_standard_id="s2",
        direction="forward",
        rules=[],
    )
    step_two = ConversionStep(
        crosswalk_id="cw2",
        crosswalk_name="CW Two",
        source_standard_id="s2",
        target_standard_id="s3",
        direction="reverse",
        rules=[],
    )
    caption = transform_view._route_caption(
        [step_one, step_two], "marcxml", "oai_dc_xml"
    )
    assert caption == "CW One (forward) -> CW Two (reverse)"

    calls: list[str] = []

    def _fake_apply(source_ir, _rules):
        calls.append("apply")
        report = TransformationReport(
            applied_rule_ids=["rule-a"],
            unmapped_fields=["missing:title"],
            semantic_loss_rules=[],
            ambiguous_rules=["ambig-1"],
        )
        out = dict(source_ir)
        out[f"step_{len(calls)}"] = []
        return out, report

    monkeypatch.setattr(transform_view, "apply_mapping_rules", _fake_apply)
    converted, report = transform_view._apply_conversion_steps({}, [step_one, step_two])
    assert list(converted.keys()) == ["step_1", "step_2"]
    assert report.applied_rule_ids == ["rule-a"]
    assert report.unmapped_fields == ["missing:title"]
    assert report.ambiguous_rules == ["ambig-1"]


def test_transform_parse_payload_dispatch(monkeypatch) -> None:
    monkeypatch.setattr(
        transform_view,
        "parse_oai_dc_xml_to_ir",
        lambda _payload: {"format": "oai_dc_xml"},
    )
    monkeypatch.setattr(
        transform_view,
        "parse_marcxml_to_ir",
        lambda _payload: {"format": "marcxml"},
    )
    monkeypatch.setattr(
        transform_view,
        "parse_openaire_xml_to_ir",
        lambda _payload: {"format": "oai_openaire"},
    )
    monkeypatch.setattr(
        transform_view,
        "parse_datacite_xml_to_ir",
        lambda _payload: {"format": "datacite_xml"},
    )

    assert transform_view._parse_payload("<xml />", "oai_dc_xml") == {
        "format": "oai_dc_xml"
    }
    assert transform_view._parse_payload("<xml />", "marcxml") == {"format": "marcxml"}
    assert transform_view._parse_payload("<xml />", "datacite_xml", "oai_openaire") == {
        "format": "oai_openaire"
    }
    assert transform_view._parse_payload("<xml />", "datacite_xml") == {
        "format": "datacite_xml"
    }

    with pytest.raises(ValueError, match="Unsupported format"):
        transform_view._parse_payload("<xml />", "mods_xml")


def test_transform_serialize_target_dispatch() -> None:
    source = {"title": []}
    assert transform_view._serialize_target(source, "oai_dc_xml").startswith("<")
    assert transform_view._serialize_target(source, "datacite_xml").startswith("<")
    with pytest.raises(ValueError, match="Unsupported target format"):
        transform_view._serialize_target(source, "marcxml")


def test_transform_merge_reports_deduplicates_and_sorts() -> None:
    merged = transform_view._merge_reports(
        [
            TransformationReport(
                applied_rule_ids=["b", "a"],
                unmapped_fields=["z"],
                semantic_loss_rules=["loss-2"],
                ambiguous_rules=["amb-2", "amb-1"],
            ),
            TransformationReport(
                applied_rule_ids=["a", "c"],
                unmapped_fields=["z", "y"],
                semantic_loss_rules=["loss-2", "loss-1"],
                ambiguous_rules=["amb-1"],
            ),
        ]
    )
    assert merged.applied_rule_ids == ["a", "b", "c"]
    assert merged.unmapped_fields == ["y", "z"]
    assert merged.semantic_loss_rules == ["loss-1", "loss-2"]
    assert merged.ambiguous_rules == ["amb-1", "amb-2"]


def test_transform_resolved_choices_filters_unsupported(monkeypatch) -> None:
    formats = [
        MetadataFormatInfo(
            metadata_prefix="oai_dc",
            schema="",
            metadata_namespace="",
        ),
        MetadataFormatInfo(
            metadata_prefix="custom",
            schema="",
            metadata_namespace="",
        ),
    ]

    def _bridge(item: MetadataFormatInfo) -> ResolvedFormat | None:
        if item.metadata_prefix == "oai_dc":
            return ResolvedFormat(
                metadata_prefix="oai_dc",
                internal_format="oai_dc_xml",
                source_profile="oai_dc",
            )
        return None

    monkeypatch.setattr(transform_view, "bridge_metadata_format", _bridge)

    choices = transform_view._resolved_choices(formats)
    assert list(choices.keys()) == ["oai_dc"]
    assert choices["oai_dc"].internal_format == "oai_dc_xml"


def test_transform_load_sample_identifiers_live_and_fallback(monkeypatch) -> None:
    class _LiveClient:
        def __init__(self, _endpoint: str) -> None:
            pass

        def list_identifiers(self, _metadata_prefix: str) -> str:
            return "<ListIdentifiers />"

    monkeypatch.setattr(transform_view, "OAIClient", _LiveClient)
    monkeypatch.setattr(
        transform_view,
        "parse_identifiers",
        lambda _xml, limit=8: IdentifierList(identifiers=["id:one", "id:two"]),
    )
    identifiers, warning = transform_view._load_sample_identifiers(
        "DLR", "https://example.org/oai", "oai_dc"
    )
    assert identifiers == ["id:one", "id:two"]
    assert warning is None

    class _FailingClient:
        def __init__(self, _endpoint: str) -> None:
            pass

        def list_identifiers(self, _metadata_prefix: str) -> str:
            raise RuntimeError("service unavailable")

    monkeypatch.setattr(transform_view, "OAIClient", _FailingClient)
    monkeypatch.setattr(
        transform_view,
        "load_demo_identifiers",
        lambda: {"DLR": {"oai_dc": ["demo:123"]}},
    )
    identifiers, warning = transform_view._load_sample_identifiers(
        "DLR", "https://example.org/oai", "oai_dc"
    )
    assert identifiers == ["demo:123"]
    assert warning is not None
    assert "Live identifier lookup failed" in warning


def test_transform_load_sample_identifiers_returns_error_without_fallback(
    monkeypatch,
) -> None:
    class _FailingClient:
        def __init__(self, _endpoint: str) -> None:
            pass

        def list_identifiers(self, _metadata_prefix: str) -> str:
            raise RuntimeError("service unavailable")

    monkeypatch.setattr(transform_view, "OAIClient", _FailingClient)
    monkeypatch.setattr(transform_view, "load_demo_identifiers", lambda: {})

    identifiers, warning = transform_view._load_sample_identifiers(
        "DLR", "https://example.org/oai", "oai_dc"
    )
    assert identifiers == []
    assert warning == "service unavailable"
