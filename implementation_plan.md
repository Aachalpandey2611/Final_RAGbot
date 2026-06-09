# Improve RAG Retrieval Accuracy for Architecture Documentation

The retrieval report shows that BM25 and Vector search retrieve independent chunks that break decision logic across multiple fragments, leading to poor context selection and poor reranking. We will systematically address the 9 required improvements to ensure routing rules and logic chains remain fully intact and accurately retrieved.

## Proposed Changes

### Configuration
#### [MODIFY] `app/core/config.py`
- Increase `DEFAULT_CHUNK_SIZE` to `1200`.
- Increase `DEFAULT_CHUNK_OVERLAP` to `300`.
- Increase `HYBRID_SEARCH_TOP_N` to `20`.

---

### Chunking Strategy
#### [MODIFY] `app/services/chunking.py`
- Refactor the `AdaptiveChunkingEngine` to use improved semantic overlapping to prevent splitting `->`, `=>`, and conditional blocks.
- Update `_preserve_logic_chains` to be highly sensitive to specific business flow keywords (`accountType`, `Route to`, `Collection Agency`, `Otherwise`) to forcefully concatenate fragments containing business rules.

---

### Retrieval Orchestration
#### [MODIFY] `app/services/retrieval/retrieval_orchestrator.py`
- **Hybrid Retrieval (RRF):** Update `merge_results` to use **Reciprocal Rank Fusion (RRF)** instead of `max(score)`. This properly scales and merges dense vector scores (often 0-1) and BM25 scores (often 10+).
- **Increase Candidate Depth:** Ensure `retrieve()` requests at least 20 chunks from each sub-retriever.
- **Neighbor Expansion:** Update `fetch_neighbor_chunks` so that instead of treating neighbor chunks as independent candidate results, it **concatenates the text** of `chunk_index - 1` and `chunk_index + 1` directly into the matching candidate chunk's content. This ensures rerankers and the LLM see the full contiguous business rule.

---

### Query Logic & Flow
#### [MODIFY] `app/services/rag/rag_service.py`
- **Query Expansion:** Introduce an LLM call at the very beginning of the retrieval flow to extract exact business entities and operation names (e.g., `Z00095`, `POST_PAYMENT`, `getBillingCreditDetails`). Append these exact keywords to the query sent to the Orchestrator.
- **Multi-Hop Retrieval:** Improve the existing multi-hop check. Scan the retrieved context for missing routing conditions (e.g. if the context says "if accountType=2" but doesn't mention the outcome). If a routing flow is partially retrieved, fire a secondary BM25/Vector retrieval specifically searching for the missing terms.
- **Context Validation Before Generation:** Before invoking the `PromptBuilder`, do a string presence check for decision keywords (`if`, `route`, `->`, `determine`, `flow`) when the query explicitly asks for a flow or routing logic. If the context fails validation, return a fallback message or attempt a fallback retrieval.

---

### Reranking
#### [MODIFY] `app/services/rag/reranker.py`
- Ensure the `CrossEncoder` model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) is appropriately scoring the expanded multi-chunk context. 
- *Note: the model is currently implemented correctly, but because the neighbor chunks were separated, it couldn't score the logic chains high enough. The neighbor concatenation fix in the orchestrator will dramatically improve the reranker's accuracy.*

---

## User Review Required

> [!IMPORTANT]  
> The `sentence-transformers` cross-encoder model might take a minute to download on the first run after restarting the backend if it isn't cached locally. I will monitor the startup to ensure it completes successfully.

> [!WARNING]  
> Re-chunking strategy changes will only apply to **newly uploaded** documents. If you have already uploaded the architecture documents into the database, we will need to re-upload them or trigger a database re-index script to apply the new semantic chunking sizes (1200 / 300) to your existing files. Let me know if you'd like me to write a quick database re-index script.

## Verification Plan

### Automated Tests
1. Generate the same Retrieval Debug Report using `generate_report.py` after implementing the fixes.
2. Verify that **Rank 1** for "How does Bill Inquiry determine whether to route..." contains the full `Z00095 -> JPL-RR` rule.
3. Verify that the primary source for "Bill Plan Change through MyJio" correctly points to `Plan Subscription Management`.

### Manual Verification
1. I will ask the chat the 3 reference questions to verify the generated UI responses are fully correct.
