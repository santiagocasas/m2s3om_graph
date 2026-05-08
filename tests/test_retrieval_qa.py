from m2s3om_graph.db.repository import InMemoryCrosswalkRepository
from m2s3om_graph.models.standards import Chunk, Element, Standard
from m2s3om_graph.qa.service import answer_question
from m2s3om_graph.retrieval.hybrid import confidence_from_similarity, retrieve_for_element


def _seed_repo_for_retrieval() -> tuple[InMemoryCrosswalkRepository, Element]:
    repo = InMemoryCrosswalkRepository()
    repo.upsert_standard(Standard(id="src", name="Source"))
    repo.upsert_standard(Standard(id="dc", name="Dublin Core"))
    repo.upsert_elements(
        [
            Element(id="dc:title", standard_id="dc", path="dc:title", label="Title"),
            Element(
                id="dc:creator",
                standard_id="dc",
                path="dc:creator",
                label="Creator",
            ),
        ]
    )
    repo.upsert_chunks(
        [
            Chunk(
                id="chunk_title",
                standard_id="dc",
                element_id="dc:title",
                content="Title of resource text with publication metadata",
            ),
            Chunk(
                id="chunk_creator",
                standard_id="dc",
                element_id="dc:creator",
                content="Creator names and contributor guidance",
            ),
            Chunk(
                id="chunk_misc",
                standard_id="dc",
                element_id=None,
                content="Completely unrelated wording",
            ),
        ]
    )
    query = Element(
        id="src:title",
        standard_id="src",
        path="title",
        label="Title",
        scope_note="Resource title metadata",
    )
    return repo, query


def test_retrieve_for_element_prefers_target_element_overlap() -> None:
    repo, query = _seed_repo_for_retrieval()
    results = retrieve_for_element(repo, query, "dc", top_k=3)
    assert [x.chunk.id for x in results] == ["chunk_title", "chunk_creator"]
    assert "chunk_misc" not in [x.chunk.id for x in results]
    assert results[0].score >= results[1].score


def test_confidence_from_similarity_clamps_bounds() -> None:
    assert confidence_from_similarity(0.95, penalties=0) == 0.95
    assert confidence_from_similarity(0.95, penalties=2) == 0.75
    assert confidence_from_similarity(0.2, penalties=5) == 0.0
    assert confidence_from_similarity(1.2, penalties=0) == 1.0


def test_answer_question_uses_grounded_chunks_and_no_evidence_fallback() -> None:
    repo, _ = _seed_repo_for_retrieval()
    answered = answer_question(repo, "title creator metadata")
    assert answered.startswith("Grounded answer candidate based on standards corpus:")
    assert "Title of resource text" in answered
    assert "Creator names" in answered

    no_match = answer_question(repo, "quantum foobar baz")
    assert no_match == "No grounded evidence found in standards corpus."
