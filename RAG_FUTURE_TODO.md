# Future Work: RAG-Based Mapping Inference

This note captures future work items for opening a GitHub issue about Retrieval-Augmented Generation (RAG) for mapping inference from artifact documents.

## Goal

Improve mapping extraction quality by retrieving relevant artifact chunks for each candidate mapping question instead of sending one large merged context to the LLM.

## Why This Matters

- Better precision/recall on long and heterogeneous docs.
- Lower hallucination risk through evidence-grounded extraction.
- Stronger provenance: each mapping can point to specific chunk IDs and URLs.

## Proposed Phased Plan

### Phase 1: Retrieval-First Pipeline (No Vector DB Yet)

1. Build a retrieval service over stored artifact chunks (lexical/hybrid ranking).
2. For each source term/candidate, retrieve top-k chunks and pass only those to LLM.
3. Add a two-pass extraction:
   - pass A: propose candidate mappings,
   - pass B: verify evidence and filter weak candidates.
4. Persist retrieval metadata with each mapping rule:
   - chunk IDs,
   - snippet text,
   - source URL,
   - retrieval score.

### Phase 2: Confidence + Verification Layer

1. Add rule-level confidence calibration and thresholding.
2. Add conflict handling (multiple targets for same source term).
3. Add semantic-loss and ambiguity tagging based on retrieved evidence.

### Phase 3: UI + Explainability

1. In Crosswalk Browser, show "retrieved chunks used" per rule.
2. Add a reviewer workflow to accept/reject AI-assisted rules.
3. Keep authoritative SSSOM generation limited to verified/approved rules.

### Phase 4: Optional Embedding Upgrade

1. Add embedding-based retrieval (hybrid lexical + vector).
2. Compare quality/latency against lexical-only baseline.
3. Keep lexical retrieval as fallback when embeddings are unavailable.

## Deliverables

- New retrieval component integrated into mapping ingestion.
- Provenance-rich rule records in KG.
- SSSOM output backed by verified evidence.
- Pipeline metrics: extraction yield, precision proxy, unresolved mappings.

## Acceptance Criteria (Issue Checklist)

- [ ] Retrieval is used for LLM extraction contexts (not only full-document stuffing).
- [ ] Each generated rule stores evidence chunk IDs and source URLs.
- [ ] Failed/ambiguous mappings are explicitly classified.
- [ ] UI exposes evidence used per rule.
- [ ] Exported SSSOM is generated from validated rules only.
- [ ] Tests cover retrieval ranking + evidence persistence + end-to-end extraction.

## Nice-to-Have

- Add a benchmarking dataset to compare non-RAG vs RAG extraction quality.
- Add a quick "re-run single mapping with debug retrieval traces" mode.
