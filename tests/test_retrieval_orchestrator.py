import asyncio

from app.services.retrieval.retrieval_orchestrator import RetrievalOrchestrator


class SimpleDoc:
    def __init__(self, id, user_id=1):
        self.id = id
        self.user_id = user_id


class SimpleChunk:
    def __init__(self, id, content, doc_id=1, user_id=1):
        self.id = id
        self.content = content
        self.document_id = doc_id
        self.document = SimpleDoc(doc_id, user_id=user_id)


class FakeRepo:
    def __init__(self, chunks):
        self._chunks = {c.id: c for c in chunks}

    async def get_multi(self, skip=0, limit=100):
        return list(self._chunks.values())

    async def get(self, cid):
        return self._chunks.get(cid)


class FakeVectorStore:
    def __init__(self, hits):
        # hits: list of dicts with 'id' and 'score'
        self.hits = hits

    async def search(self, collection_name, query_embedding, limit=10):
        return self.hits[:limit]


class FakeProvider:
    async def embed_text(self, text):
        return [0.0, 0.1]


class FakeReranker:
    def rerank(self, query, chunks):
        # assign similarity proportional to content length
        results = []
        for c in chunks:
            results.append((c, float(len(c.content))))
        results.sort(key=lambda x: x[1], reverse=True)
        return results


async def run_test():
    # Prepare fake chunks
    chunks = [SimpleChunk(1, "this is a test chunk about python"), SimpleChunk(2, "another chunk about fastapi"), SimpleChunk(3, "short")] 

    orch = RetrievalOrchestrator(db=None)
    orch.chunk_repo = FakeRepo(chunks)
    orch.vector_store = FakeVectorStore([{"id": 2, "score": 0.9}, {"id":1, "score":0.8}])
    orch.provider = FakeProvider()
    orch.reranker = FakeReranker()

    res = await orch.retrieve("test query about python", top_k=2, user_id=None)
    assert isinstance(res, dict)
    assert "chunks" in res and "retrieval_scores" in res and "source_type" in res
    assert len(res["chunks"]) == 2


def test_run():
    asyncio.run(run_test())


if __name__ == "__main__":
    test_run()
