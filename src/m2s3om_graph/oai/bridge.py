from dataclasses import dataclass

from .parser import MetadataFormatInfo


@dataclass(frozen=True)
class ResolvedFormat:
    metadata_prefix: str
    internal_format: str
    source_profile: str
    note: str = ""


def _resolve_from_prefix(raw_prefix: str, prefix: str) -> ResolvedFormat | None:
    if prefix in {"oai_dc", "oai_bibl", "uketd_dc", "qdc"}:
        return ResolvedFormat(
            metadata_prefix=raw_prefix,
            internal_format="oai_dc_xml",
            source_profile=prefix,
        )

    if prefix in {"datacite", "oai_datacite"}:
        return ResolvedFormat(
            metadata_prefix=raw_prefix,
            internal_format="datacite_xml",
            source_profile=prefix,
        )

    if prefix == "oai_openaire":
        return ResolvedFormat(
            metadata_prefix=raw_prefix,
            internal_format="datacite_xml",
            source_profile="oai_openaire",
            note="OpenAIRE is treated as DataCite-compatible in the demo app.",
        )

    if prefix == "marcxml":
        return ResolvedFormat(
            metadata_prefix=raw_prefix,
            internal_format="marcxml",
            source_profile="marcxml",
        )

    if prefix == "mods":
        return ResolvedFormat(
            metadata_prefix=raw_prefix,
            internal_format="mods_xml",
            source_profile="mods",
        )

    return None


def _contains_in_schema_or_namespace(
    schema: str,
    namespace: str,
    needle: str,
) -> bool:
    return needle in schema or needle in namespace


def bridge_metadata_format(
    metadata_format: MetadataFormatInfo,
) -> ResolvedFormat | None:
    prefix = metadata_format.metadata_prefix.strip().lower()
    schema = metadata_format.schema.strip().lower()
    namespace = metadata_format.metadata_namespace.strip().lower()

    if _contains_in_schema_or_namespace(schema, namespace, "marc21/slim"):
        return ResolvedFormat(
            metadata_prefix=metadata_format.metadata_prefix,
            internal_format="marcxml",
            source_profile="marcxml",
        )

    if _contains_in_schema_or_namespace(schema, namespace, "loc.gov/mods"):
        return ResolvedFormat(
            metadata_prefix=metadata_format.metadata_prefix,
            internal_format="mods_xml",
            source_profile="mods",
        )

    resolved = _resolve_from_prefix(metadata_format.metadata_prefix, prefix)
    if resolved is not None:
        return resolved

    if "openaire" in namespace:
        return ResolvedFormat(
            metadata_prefix=metadata_format.metadata_prefix,
            internal_format="datacite_xml",
            source_profile="oai_openaire",
            note="OpenAIRE is treated as DataCite-compatible in the demo app.",
        )

    if _contains_in_schema_or_namespace(schema, namespace, "datacite"):
        return ResolvedFormat(
            metadata_prefix=metadata_format.metadata_prefix,
            internal_format="datacite_xml",
            source_profile=prefix or "datacite",
        )

    if "oai_dc" in schema or namespace.endswith("/oai_dc/"):
        return ResolvedFormat(
            metadata_prefix=metadata_format.metadata_prefix,
            internal_format="oai_dc_xml",
            source_profile=prefix or "oai_dc",
        )

    return None
