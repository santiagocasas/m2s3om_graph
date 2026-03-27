from kaigraph.transform.xml_namespaces import DATACITE_NS as _DATACITE_NS

DATACITE_NS = _DATACITE_NS

OAIRE_NS = "http://namespace.openaire.eu/schema/oaire/"

ELIB_BASE_SCHEME = "https"
ELIB_BASE_HOST = "elib.dlr.de"
ELIB_BASE_URL = f"{ELIB_BASE_SCHEME}://{ELIB_BASE_HOST}"

ELIB_OPENAIRE_EXPORT_TEMPLATE = (
    f"{ELIB_BASE_URL}/cgi/export/eprint/{{record_id}}/OPENAIRE/"
    "dlr-eprint-{record_id}.xml"
)
ELIB_DC_EXPORT_TEMPLATE = (
    f"{ELIB_BASE_URL}/cgi/export/eprint/{{record_id}}/DC/dlr-eprint-{{record_id}}.txt"
)
