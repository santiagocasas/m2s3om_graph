HTTPS_SCHEME = "https"

RDAMSC_HOST = "rdamsc.bath.ac.uk"
BLABLADOR_HOST = "api.helmholtz-blablador.fz-juelich.de"

RDAMSC_BASE_URL = f"{HTTPS_SCHEME}://{RDAMSC_HOST}"
BLABLADOR_DEFAULT_BASE_URL = f"{HTTPS_SCHEME}://{BLABLADOR_HOST}/v1"
GITHUB_WEB_HOST = "github.com"
GITHUB_RAW_HOST = "raw.githubusercontent.com"
GITHUB_RAW_CONTENT_URL_TEMPLATE = (
    f"{HTTPS_SCHEME}://{GITHUB_RAW_HOST}/{{owner}}/{{repo}}/{{branch}}/{{tail}}"
)
