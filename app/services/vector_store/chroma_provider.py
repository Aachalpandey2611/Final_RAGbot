import logging
from typing import List, Dict, Any, Optional
from app.services.vector_store.base import VectorStore

logger = logging.getLogger("vector_store")

class ChromaVectorStore(VectorStore):
    """
    Adapter for ChromaDB local persistent server/SQLite.
    """
    def __init__(self, persist_directory: str):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_directory)

    def _get_collection(self, collection_name: str):
        # Create a valid collection name (alphanumeric, chars/numbers/underscores/dashes only)
        clean_name = collection_name.replace("-", "_").replace(".", "_")
        # Chroma collection names must start with a letter or number
        if not clean_name[0].isalnum():
            clean_name = "col_" + clean_name
        # Length check
        if len(clean_name) < 3:
            clean_name = clean_name + "_coll"
        clean_name = clean_name[:63]
        return self.client.get_or_create_collection(clean_name)

    async def insert(
        self, 
        collection_name: str, 
        ids: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]], 
        documents: List[str]
    ) -> None:
        if not documents:
            return
        collection = self._get_collection(collection_name)
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    async def search(
        self, 
        collection_name: str, 
        query_embedding: List[float], 
        limit: int,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        collection = self._get_collection(collection_name)
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where
            )
            # Reformat to common dictionary structure
            output = []
            if results and results["documents"]:
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                ids = results["ids"][0]
                distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)
                
                for d, m, i, dist in zip(docs, metas, ids, distances):
                    output.append({
                        "id": i,
                        "text": d,
                        "metadata": m,
                        "score": 1.0 / (1.0 + dist)  # Normalize L2 distance to [0, 1] similarity
                    })
            return output
        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            return []

    async def update(
        self, 
        collection_name: str, 
        ids: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]], 
        documents: List[str]
    ) -> None:
        if not ids:
            return
        collection = self._get_collection(collection_name)
        collection.update(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

    async def delete(
        self, 
        collection_name: str, 
        ids: List[str]
    ) -> None:
        if not ids:
            return
        collection = self._get_collection(collection_name)
        collection.delete(ids=ids)
