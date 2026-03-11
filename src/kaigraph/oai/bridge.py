from dataclasses import dataclass

from .parser import MetadataFormatInfo


@dataclass(frozen=True)
class ResolvedFormat:
    metadata_prefix: str
    internal_format: str
    source_profile: str
    note: str = ""


def bridge_metadata_format(
    metadata_format: MetadataFormatInfo,
) -> ResolvedFormat | None:
    prefix = metadata_format.metadata_prefix.strip().lower()
    schema = metadata_format.schema.strip().lower()
    namespace = metadata_format.metadata_namespace.strip().lower()

    if prefix in {"oai_dc", "oai_bibl", "uketd_dc", "qdc"}:
        return ResolvedFormat(
            metadata_prefix=metadata_format.metadata_prefix,
            internal_format="oai_dc_xml",
            source_profile=prefix,
        )

    if prefix in {"datacite", "oai_datacite"}:
        return ResolvedFormat(
            metadata_prefix=metadata_format.metadata_prefix,
            internal_format="datacite_xml",
            source_profile=prefix,
        )

    if prefix == "oai_openaire" or "openaire" in namespace:
        return ResolvedFormat(
            metadata_prefix=metadata_format.metadata_prefix,
            internal_format="datacite_xml",
            source_profile="oai_openaire",
            note="OpenAIRE is treated as DataCite-compatible in the demo app.",
        )

    if "datacite" in schema or "datacite" in namespace:
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
