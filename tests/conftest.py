from pathlib import Path

import pytest


@pytest.fixture
def datacite_mapping_pdf_path() -> Path:
    path = Path("/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf")
    if not path.exists():
        pytest.skip("requires local DataCite_DublinCore_Mapping.pdf fixture")
    return path
