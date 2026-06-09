from typing import List, Dict, Any, Optional

class VectorStore:
    """
    Abstract interface for Vector Database operations.
    Supports inserting, searching, updating, and deleting embeddings.
    """
    async def insert(
        self, 
        collection_name: str, 
        ids: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]], 
        documents: List[str]
    ) -> None:
        raise NotImplementedError()

    async def search(
        self, 
        collection_name: str, 
        query_embedding: List[float], 
        limit: int,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError()

    async def update(
        self, 
        collection_name: str, 
        ids: List[str], 
        embeddings: List[List[float]], 
        metadatas: List[Dict[str, Any]], 
        documents: List[str]
    ) -> None:
        raise NotImplementedError()

    async def delete(
        self, 
        collection_name: str, 
        ids: List[str]
    ) -> None:
        raise NotImplementedError()
