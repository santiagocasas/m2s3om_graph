from dataclasses import dataclass
from pathlib import Path

import yaml

_RESOURCE_DIR = Path(__file__).resolve().parents[3] / "resources"
_INSTITUTION_CONFIG = _RESOURCE_DIR / "OAIHarvester.config.yaml"
_SAMPLE_CONFIG = _RESOURCE_DIR / "OAIHarvester.samples.yaml"


@dataclass(frozen=True)
class InstitutionEndpoint:
    name: str
    oai_endpoint: str


def _load_yaml(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return loaded
    return {}


def load_institution_endpoints() -> list[InstitutionEndpoint]:
    loaded = _load_yaml(_INSTITUTION_CONFIG)
    institutions: list[InstitutionEndpoint] = []
    for name, payload in loaded.items():
        if not isinstance(name, str) or not isinstance(payload, dict):
            continue
        endpoint = payload.get("oai_endpoint")
        if isinstance(endpoint, str) and endpoint.strip():
            institutions.append(
                InstitutionEndpoint(name=name.strip(), oai_endpoint=endpoint.strip())
            )
    return sorted(institutions, key=lambda item: item.name)


def load_demo_identifiers() -> dict[str, dict[str, list[str]]]:
    loaded = _load_yaml(_SAMPLE_CONFIG)
    out: dict[str, dict[str, list[str]]] = {}
    for institution, payload in loaded.items():
        if not isinstance(institution, str) or not isinstance(payload, dict):
            continue
        prefix_map: dict[str, list[str]] = {}
        for metadata_prefix, identifiers in payload.items():
            if not isinstance(metadata_prefix, str) or not isinstance(
                identifiers, list
            ):
                continue
            clean_ids = [
                item.strip()
                for item in identifiers
                if isinstance(item, str) and item.strip()
            ]
            if clean_ids:
                prefix_map[metadata_prefix.strip()] = clean_ids
        if prefix_map:
            out[institution.strip()] = prefix_map
    return out
