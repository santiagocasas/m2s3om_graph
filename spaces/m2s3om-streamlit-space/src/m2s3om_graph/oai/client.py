from dataclasses import dataclass

import requests


@dataclass
class OAIClient:
    base_url: str
    timeout_s: int = 20

    def _request(self, params: dict[str, str]) -> str:
        response = requests.get(self.base_url, params=params, timeout=self.timeout_s)
        response.raise_for_status()
        return response.text

    def identify(self) -> str:
        return self._request({"verb": "Identify"})

    def list_metadata_formats(self, identifier: str | None = None) -> str:
        params = {"verb": "ListMetadataFormats"}
        if identifier is not None:
            params["identifier"] = identifier
        return self._request(params)

    def list_identifiers(self, metadata_prefix: str = "oai_dc") -> str:
        return self._request(
            {
                "verb": "ListIdentifiers",
                "metadataPrefix": metadata_prefix,
            }
        )

    def list_identifiers_resumption(self, resumption_token: str) -> str:
        return self._request(
            {
                "verb": "ListIdentifiers",
                "resumptionToken": resumption_token,
            }
        )

    def get_record(self, identifier: str, metadata_prefix: str = "oai_dc") -> str:
        return self._request(
            {
                "verb": "GetRecord",
                "identifier": identifier,
                "metadataPrefix": metadata_prefix,
            }
        )
