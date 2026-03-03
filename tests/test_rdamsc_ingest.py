from pathlib import Path
from typing import cast

from kaigraph.db import InMemoryCrosswalkStore
from kaigraph.rdamsc.artifacts import ArtifactFetchError
from kaigraph.rdamsc.api import RDAMSCClient
from kaigraph.rdamsc.artifacts import ArtifactText
from kaigraph.rdamsc.ingest import ingest_rdamsc_crosswalk_docs, sync_rdamsc_catalog


class _FakeClient:
    def list_mappings(self, page_size: int = 200) -> list[dict]:
        return [{"uri": "https://example.org/api2/c5"}]

    def get_json_by_url(self, url: str) -> dict:
        return {
            "data": {
                "mscid": "msc:c5",
                "name": "DataCite to Dublin Core",
                "slug": "datacite_TO_dc",
                "locations": [
                    {"url": "https://example.org/mapping.txt", "type": "document"}
                ],
                "relatedEntities": [
                    {
                        "role": "input scheme",
                        "data": {
                            "mscid": "msc:m11",
                            "title": "DataCite",
                            "uri": "https://example.org/api2/m11",
                        },
                    },
                    {
                        "role": "output scheme",
                        "data": {
                            "mscid": "msc:m15",
                            "title": "Dublin Core",
                            "uri": "https://example.org/api2/m15",
                        },
                    },
                ],
            }
        }

    def get_mapping_detail(self, mscid: str) -> dict:
        assert mscid == "msc:c5"
        return {
            "mscid": "msc:c5",
            "locations": [
                {"url": "https://example.org/mapping.txt", "type": "document"}
            ],
        }


def test_sync_rdamsc_catalog_creates_crosswalks() -> None:
    store = InMemoryCrosswalkStore()
    count = sync_rdamsc_catalog(store, client=cast(RDAMSCClient, _FakeClient()))
    assert count == 1
    crosswalks = store.list_crosswalks()
    assert len(crosswalks) == 1
    assert crosswalks[0].msc_id == "msc:c5"


def test_ingest_docs_generates_rules_and_sssom(monkeypatch, tmp_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    _ = sync_rdamsc_catalog(store, client=cast(RDAMSCClient, _FakeClient()))

    def _fake_fetch(
        url: str, timeout: int = 30, max_chars: int = 200_000
    ) -> ArtifactText:
        return ArtifactText(
            url=url,
            content_type="text/plain",
            text="title -> dcterms:title\ncreator -> dcterms:creator",
        )

    def _fake_extract(
        text: str,
        source_standard: str,
        target_standard: str,
        *,
        max_rules: int = 160,
    ) -> list[dict[str, object]]:
        return [
            {
                "source_path": "title",
                "target_path": "dcterms:title",
                "mapping_type": "direct",
                "confidence": 0.88,
                "notes": "auto",
                "evidence": "title -> dcterms:title",
            }
        ]

    monkeypatch.setattr("kaigraph.rdamsc.ingest.fetch_artifact_text", _fake_fetch)
    monkeypatch.setattr(
        "kaigraph.rdamsc.ingest.extract_mapping_candidates", _fake_extract
    )

    result = ingest_rdamsc_crosswalk_docs(
        store,
        "rdamsc_c5",
        tmp_path,
        client=cast(RDAMSCClient, _FakeClient()),
    )
    assert result["ok"] is True
    assert cast(int, result["artifact_documents"]) == 1
    assert cast(int, result["artifact_chunks"]) >= 1
    bundle = store.get_crosswalk_bundle("rdamsc_c5")
    assert bundle is not None
    assert len(bundle.rules) == 1
    assert bundle.rules[0].target_paths == ["dcterms:title"]
    assert len(store.list_artifact_documents("rdamsc_c5")) == 1
    assert len(store.list_artifact_chunks("rdamsc_c5")) >= 1
    assert (tmp_path / "rdamsc_c5.sssom.tsv").exists()


def test_ingest_docs_no_rules_does_not_write_sssom(monkeypatch, tmp_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    _ = sync_rdamsc_catalog(store, client=cast(RDAMSCClient, _FakeClient()))

    def _fake_fetch(
        url: str, timeout: int = 30, max_chars: int = 200_000
    ) -> ArtifactText:
        return ArtifactText(
            url=url,
            content_type="text/plain",
            text="This document has no explicit mapping arrow patterns.",
        )

    def _fake_extract(
        text: str,
        source_standard: str,
        target_standard: str,
        *,
        max_rules: int = 160,
    ) -> list[dict[str, object]]:
        return []

    monkeypatch.setattr("kaigraph.rdamsc.ingest.fetch_artifact_text", _fake_fetch)
    monkeypatch.setattr(
        "kaigraph.rdamsc.ingest.extract_mapping_candidates", _fake_extract
    )

    result = ingest_rdamsc_crosswalk_docs(
        store,
        "rdamsc_c5",
        tmp_path,
        client=cast(RDAMSCClient, _FakeClient()),
    )
    assert result["ok"] is False
    assert result["reason"] == "no_rules_extracted"
    assert not (tmp_path / "rdamsc_c5.sssom.tsv").exists()


def test_ingest_docs_unreachable_is_classified(monkeypatch, tmp_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    _ = sync_rdamsc_catalog(store, client=cast(RDAMSCClient, _FakeClient()))

    def _raise_fetch(
        url: str, timeout: int = 30, max_chars: int = 200_000
    ) -> ArtifactText:
        raise ArtifactFetchError("upstream unavailable", status_code=503)

    monkeypatch.setattr("kaigraph.rdamsc.ingest.fetch_artifact_text", _raise_fetch)

    result = ingest_rdamsc_crosswalk_docs(
        store,
        "rdamsc_c5",
        tmp_path,
        client=cast(RDAMSCClient, _FakeClient()),
    )
    assert result["ok"] is False
    assert result["reason"] == "artifacts_unreachable"


def test_ingest_docs_conversion_error_is_classified_unsupported(
    monkeypatch, tmp_path: Path
) -> None:
    class _DocClient(_FakeClient):
        def get_mapping_detail(self, mscid: str) -> dict:
            assert mscid == "msc:c5"
            return {
                "mscid": "msc:c5",
                "locations": [
                    {
                        "url": "https://example.org/mapping.doc",
                        "type": "document",
                    },
                    {
                        "url": "https://example.org/mapping.rtf",
                        "type": "document",
                    },
                ],
            }

    store = InMemoryCrosswalkStore()
    _ = sync_rdamsc_catalog(store, client=cast(RDAMSCClient, _DocClient()))

    def _raise_conversion(
        url: str, timeout: int = 30, max_chars: int = 200_000
    ) -> ArtifactText:
        raise ArtifactFetchError("conversion failed", reason="conversion_error")

    monkeypatch.setattr("kaigraph.rdamsc.ingest.fetch_artifact_text", _raise_conversion)

    result = ingest_rdamsc_crosswalk_docs(
        store,
        "rdamsc_c5",
        tmp_path,
        client=cast(RDAMSCClient, _DocClient()),
    )
    assert result["ok"] is False
    assert result["reason"] == "artifacts_unsupported"
    checks = cast(list[dict[str, object]], result["artifact_checks"])
    assert len(checks) == 2
    assert all(x.get("status") == "conversion_error" for x in checks)


def test_ingest_docs_attempts_non_easy_extensions(monkeypatch, tmp_path: Path) -> None:
    class _DocClient(_FakeClient):
        def get_mapping_detail(self, mscid: str) -> dict:
            assert mscid == "msc:c5"
            return {
                "mscid": "msc:c5",
                "locations": [
                    {
                        "url": "https://example.org/mapping.doc",
                        "type": "document",
                    },
                    {
                        "url": "https://example.org/mapping.rtf",
                        "type": "document",
                    },
                ],
            }

    store = InMemoryCrosswalkStore()
    _ = sync_rdamsc_catalog(store, client=cast(RDAMSCClient, _DocClient()))
    seen: list[str] = []

    def _fake_fetch(
        url: str, timeout: int = 30, max_chars: int = 200_000
    ) -> ArtifactText:
        seen.append(url)
        return ArtifactText(
            url=url,
            content_type="text/markdown",
            text="fieldA -> fieldB",
        )

    def _fake_extract(
        text: str,
        source_standard: str,
        target_standard: str,
        *,
        max_rules: int = 160,
    ) -> list[dict[str, object]]:
        return [
            {
                "source_path": "fieldA",
                "target_path": "fieldB",
                "mapping_type": "direct",
                "confidence": 0.7,
                "notes": "test",
                "evidence": "fieldA -> fieldB",
            }
        ]

    monkeypatch.setattr("kaigraph.rdamsc.ingest.fetch_artifact_text", _fake_fetch)
    monkeypatch.setattr(
        "kaigraph.rdamsc.ingest.extract_mapping_candidates", _fake_extract
    )

    result = ingest_rdamsc_crosswalk_docs(
        store,
        "rdamsc_c5",
        tmp_path,
        client=cast(RDAMSCClient, _DocClient()),
    )
    assert result["ok"] is True
    assert seen == [
        "https://example.org/mapping.doc",
        "https://example.org/mapping.rtf",
    ]


def test_datacite_like_ingest_reuses_element_for_same_source_path(
    monkeypatch, tmp_path: Path
) -> None:
    class _DataCitePdfClient(_FakeClient):
        def get_mapping_detail(self, mscid: str) -> dict:
            assert mscid == "msc:c5"
            return {
                "mscid": "msc:c5",
                "locations": [
                    {
                        "url": "https://schema.datacite.org/meta/kernel-4.4/doc/DataCite_DublinCore_Mapping.pdf",
                        "type": "document",
                    }
                ],
            }

    store = InMemoryCrosswalkStore()
    _ = sync_rdamsc_catalog(store, client=cast(RDAMSCClient, _DataCitePdfClient()))

    def _fake_fetch(
        url: str, timeout: int = 30, max_chars: int = 200_000
    ) -> ArtifactText:
        return ArtifactText(url=url, content_type="application/pdf", text="dummy pdf")

    class _Row:
        def __init__(self, row_id: str, path: str) -> None:
            self.row_id = row_id
            self.datacite_property = path
            self.dublin_core = "dcterms:title"
            self.cases = []
            self.mapping_type = "direct"
            self.notes = None
            self.page_number = 1
            self.snippet = f"{row_id} snippet"

    def _fake_parse(*_args, **_kwargs):
        from kaigraph.db import MappingType

        row1 = _Row("2.1", "schemeURI")
        row1.mapping_type = MappingType.DIRECT
        row2 = _Row("4.2", "schemeURI")
        row2.mapping_type = MappingType.DIRECT
        return [row1, row2]

    monkeypatch.setattr("kaigraph.rdamsc.ingest.fetch_artifact_text", _fake_fetch)
    monkeypatch.setattr("kaigraph.rdamsc.ingest.parse_mapping_page_texts", _fake_parse)

    result = ingest_rdamsc_crosswalk_docs(
        store,
        "rdamsc_c5",
        tmp_path,
        client=cast(RDAMSCClient, _DataCitePdfClient()),
    )
    assert result["ok"] is True
    bundle = store.get_crosswalk_bundle("rdamsc_c5")
    assert bundle is not None
    source_paths = [rule.source_paths[0] for rule in bundle.rules]
    assert source_paths.count("schemeURI") == 2
    element_paths = [x.path for x in store.list_elements(bundle.source_standard.id)]
    assert element_paths.count("schemeURI") == 1
