import pytest

from kaigraph.rdamsc.api import RDAMSCClient, RDAMSCClientError


class _FakeResponse:
    def __init__(self, payload: object):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


def test_list_mappings_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_get(*args: object, **kwargs: object) -> _FakeResponse:
        return _FakeResponse(
            {"data": {"items": [{"uri": "https://example.org/mapping"}]}}
        )

    monkeypatch.setattr("kaigraph.rdamsc.api.requests.get", _fake_get)

    client = RDAMSCClient()
    items = client.list_mappings()
    assert len(items) == 1
    assert items[0]["uri"] == "https://example.org/mapping"


def test_list_mappings_raises_on_malformed_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_get(*args: object, **kwargs: object) -> _FakeResponse:
        return _FakeResponse({"data": []})

    monkeypatch.setattr("kaigraph.rdamsc.api.requests.get", _fake_get)

    client = RDAMSCClient()
    with pytest.raises(RDAMSCClientError) as exc_info:
        _ = client.list_mappings()

    assert exc_info.value.diagnostics["operation"] == "list_mappings.parse_data"


def test_get_mapping_detail_raises_on_malformed_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_get(*args: object, **kwargs: object) -> _FakeResponse:
        return _FakeResponse({"data": []})

    monkeypatch.setattr("kaigraph.rdamsc.api.requests.get", _fake_get)

    client = RDAMSCClient()
    with pytest.raises(RDAMSCClientError) as exc_info:
        _ = client.get_mapping_detail("msc:c123")

    assert exc_info.value.diagnostics["operation"] == "get_mapping_detail.parse_data"
