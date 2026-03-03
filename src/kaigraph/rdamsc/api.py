from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urljoin

import requests


@dataclass
class RDAMSCClient:
    base_url: str = "https://rdamsc.bath.ac.uk"
    timeout: int = 30

    def _url(self, path: str) -> str:
        return urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def _get_json(
        self,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, object]:
        response = requests.get(
            self._url(path),
            params=cast(Any, params),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = cast(Any, response.json())
        if not isinstance(payload, dict):
            raise ValueError("Unexpected RDAMSC response payload")
        return cast(dict[str, object], payload)

    def get_json_by_url(self, url: str) -> dict[str, object]:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        payload = cast(Any, response.json())
        if not isinstance(payload, dict):
            raise ValueError("Unexpected RDAMSC response payload")
        return cast(dict[str, object], payload)

    def list_mappings(self, page_size: int = 200) -> list[dict[str, object]]:
        payload = self._get_json("/api2/c", params={"pageSize": page_size})
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return []
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        return [cast(dict[str, object], x) for x in items if isinstance(x, dict)]

    def get_mapping_detail(self, mscid: str) -> dict[str, object]:
        suffix = mscid.replace("msc:", "")
        payload = self._get_json(f"/api2/{suffix}")
        data = payload.get("data", {})
        if not isinstance(data, dict):
            return {}
        return cast(dict[str, object], data)
