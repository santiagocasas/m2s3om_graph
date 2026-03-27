from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urljoin

import requests

from kaigraph.errors import ErrorPayload, make_error_payload
from kaigraph.rdamsc.constants import RDAMSC_BASE_URL


class RDAMSCClientError(RuntimeError):
    def __init__(self, diagnostics: ErrorPayload):
        self.diagnostics = diagnostics
        operation = diagnostics.get("operation", "rdamsc_client")
        message = diagnostics.get("message", "request failed")
        super().__init__(f"{operation}: {message}")


@dataclass
class RDAMSCClient:
    base_url: str = RDAMSC_BASE_URL
    timeout: int = 30

    def _url(self, path: str) -> str:
        return urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def _get_json(
        self,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> dict[str, object]:
        operation = f"GET {path}"
        try:
            response = requests.get(
                self._url(path),
                params=cast(Any, params),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            status_code = (
                exc.response.status_code if getattr(exc, "response", None) else None
            )
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation=operation,
                    error=exc,
                    status_code=status_code,
                )
            ) from exc
        try:
            payload = cast(Any, response.json())
        except ValueError as exc:
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation=f"{operation}.decode_json",
                    error=exc,
                )
            ) from exc
        if not isinstance(payload, dict):
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation=f"{operation}.validate_payload",
                    error="Unexpected RDAMSC response payload",
                )
            )
        return cast(dict[str, object], payload)

    def get_json_by_url(self, url: str) -> dict[str, object]:
        operation = f"GET {url}"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            status_code = (
                exc.response.status_code if getattr(exc, "response", None) else None
            )
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation=operation,
                    error=exc,
                    status_code=status_code,
                )
            ) from exc
        try:
            payload = cast(Any, response.json())
        except ValueError as exc:
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation=f"{operation}.decode_json",
                    error=exc,
                )
            ) from exc
        if not isinstance(payload, dict):
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation=f"{operation}.validate_payload",
                    error="Unexpected RDAMSC response payload",
                )
            )
        return cast(dict[str, object], payload)

    def list_mappings(self, page_size: int = 200) -> list[dict[str, object]]:
        payload = self._get_json("/api2/c", params={"pageSize": page_size})
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation="list_mappings.parse_data",
                    error="Unexpected RDAMSC response: 'data' must be an object",
                )
            )
        items = data.get("items", [])
        if not isinstance(items, list):
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation="list_mappings.parse_items",
                    error="Unexpected RDAMSC response: 'data.items' must be a list",
                )
            )
        return [cast(dict[str, object], x) for x in items if isinstance(x, dict)]

    def get_mapping_detail(self, mscid: str) -> dict[str, object]:
        suffix = mscid.replace("msc:", "")
        payload = self._get_json(f"/api2/{suffix}")
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise RDAMSCClientError(
                make_error_payload(
                    source="rdamsc_client",
                    operation="get_mapping_detail.parse_data",
                    error="Unexpected RDAMSC response: 'data' must be an object",
                )
            )
        return cast(dict[str, object], data)
