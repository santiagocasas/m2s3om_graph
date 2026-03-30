from kaigraph.oai.client import OAIClient


class _Response:
    def __init__(self, text: str = "<ok/>") -> None:
        self.text = text
        self.raise_called = False

    def raise_for_status(self) -> None:
        self.raise_called = True


def test_oai_client_identify_uses_base_url_and_timeout(monkeypatch) -> None:
    calls: dict[str, object] = {}
    response = _Response("<identify/>")

    def _fake_get(url: str, params: dict[str, str], timeout: int) -> _Response:
        calls["url"] = url
        calls["params"] = params
        calls["timeout"] = timeout
        return response

    monkeypatch.setattr("kaigraph.oai.client.requests.get", _fake_get)

    client = OAIClient(base_url="https://repo.example/oai", timeout_s=11)
    text = client.identify()
    assert text == "<identify/>"
    assert response.raise_called is True
    assert calls == {
        "url": "https://repo.example/oai",
        "params": {"verb": "Identify"},
        "timeout": 11,
    }


def test_oai_client_verbs_build_expected_params(monkeypatch) -> None:
    captured: list[dict[str, str]] = []

    def _fake_get(url: str, params: dict[str, str], timeout: int) -> _Response:
        _ = url, timeout
        captured.append(params)
        return _Response()

    monkeypatch.setattr("kaigraph.oai.client.requests.get", _fake_get)

    client = OAIClient(base_url="https://repo.example/oai")
    _ = client.list_metadata_formats()
    _ = client.list_metadata_formats(identifier="oai:repo:1")
    _ = client.list_identifiers(metadata_prefix="marcxml")
    _ = client.get_record(identifier="oai:repo:2", metadata_prefix="mods")

    assert captured == [
        {"verb": "ListMetadataFormats"},
        {"verb": "ListMetadataFormats", "identifier": "oai:repo:1"},
        {"verb": "ListIdentifiers", "metadataPrefix": "marcxml"},
        {
            "verb": "GetRecord",
            "identifier": "oai:repo:2",
            "metadataPrefix": "mods",
        },
    ]
