from kaigraph.db import InMemoryCrosswalkRepository
from kaigraph.ingestion import StandardSource, ingest_standard_source
from kaigraph.mapping import MappingAgent
from kaigraph.models import Standard


def test_generate_crosswalk_creates_mappings() -> None:
    repo = InMemoryCrosswalkRepository()
    ingest_standard_source(
        repo,
        StandardSource(
            standard=Standard(id="a", name="A"),
            text="title - title of resource. cardinality 1..1 type string",
        ),
    )
    ingest_standard_source(
        repo,
        StandardSource(
            standard=Standard(id="b", name="B"),
            text="name - name of resource. cardinality 1..1 type string",
        ),
    )
    agent = MappingAgent(repo)
    crosswalk, mappings = agent.generate_crosswalk("a", "b")
    assert crosswalk.id == "crosswalk:a:b"
    assert len(mappings) == 1
    assert mappings[0].source_element_id.startswith("a:")
    assert mappings[0].target_element_id.startswith("b:")
