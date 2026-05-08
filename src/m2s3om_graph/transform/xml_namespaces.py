HTTP_SCHEME = "http"

OPENARCHIVES_HOST = "www.openarchives.org"
PURL_HOST = "purl.org"
W3C_HOST = "www.w3.org"
DATACITE_HOST = "datacite.org"
DATACITE_SCHEMA_HOST = "schema.datacite.org"


def _http_url(host: str, path: str) -> str:
    return f"{HTTP_SCHEME}://{host}/{path.lstrip('/')}"


OAI_DC_NS = _http_url(OPENARCHIVES_HOST, "OAI/2.0/oai_dc/")
OAI_PMH_NS = _http_url(OPENARCHIVES_HOST, "OAI/2.0/")
DC_ELEMENTS_NS = _http_url(PURL_HOST, "dc/elements/1.1/")
DCTERMS_NS = _http_url(PURL_HOST, "dc/terms/")
XSI_NS = _http_url(W3C_HOST, "2001/XMLSchema-instance")

OAI_DC_SCHEMA_LOCATION = (
    f"{OAI_DC_NS} {_http_url(OPENARCHIVES_HOST, 'OAI/2.0/oai_dc.xsd')}"
)

DATACITE_NS = _http_url(DATACITE_HOST, "schema/kernel-4")
DATACITE_SCHEMA_LOCATION = (
    f"{DATACITE_NS} {_http_url(DATACITE_SCHEMA_HOST, 'meta/kernel-4.4/metadata.xsd')}"
)
