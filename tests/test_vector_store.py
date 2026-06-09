import pytest
import tempfile
import shutil
import os
from app.services.vector_store.chroma_provider import ChromaVectorStore

@pytest.mark.asyncio
async def test_chroma_vector_store():
    """
    Validates basic CRUD operations on ChromaVectorStore using a temporary persist directory.
    """
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Instantiate store
        store = ChromaVectorStore(persist_directory=temp_dir)
        
        collection_name = "test_collection"
        ids = ["chunk_1", "chunk_2"]
        embeddings = [
            [0.1, 0.2, 0.3, 0.4],
            [0.9, 0.8, 0.7, 0.6]
        ]
        metadatas = [
            {"document_id": 1, "chunk_index": 0},
            {"document_id": 1, "chunk_index": 1}
        ]
        documents = [
            "This is the first test chunk of text.",
            "This is the second test chunk containing other information."
        ]
        
        # Test insert
        await store.insert(
            collection_name=collection_name,
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        # Test search (query close to first vector)
        query_embedding = [0.12, 0.22, 0.32, 0.42]
        results = await store.search(
            collection_name=collection_name,
            query_embedding=query_embedding,
            limit=1
        )
        
        assert len(results) == 1
        assert results[0]["id"] == "chunk_1"
        assert results[0]["text"] == "This is the first test chunk of text."
        assert results[0]["metadata"]["document_id"] == 1
        assert "score" in results[0]
        
        # Test update
        updated_embeddings = [
            [0.11, 0.21, 0.31, 0.41],
            [0.91, 0.81, 0.71, 0.61]
        ]
        updated_documents = [
            "This is the first test chunk of text - UPDATED.",
            "This is the second test chunk - UPDATED."
        ]
        await store.update(
            collection_name=collection_name,
            ids=ids,
            embeddings=updated_embeddings,
            metadatas=metadatas,
            documents=updated_documents
        )
        
        # Search again to verify update
        results_after_update = await store.search(
            collection_name=collection_name,
            query_embedding=query_embedding,
            limit=1
        )
        assert len(results_after_update) == 1
        assert results_after_update[0]["text"] == "This is the first test chunk of text - UPDATED."
        
        # Test delete
        await store.delete(collection_name=collection_name, ids=["chunk_1"])
        
        # Search again and ensure only chunk_2 remains
        results_after_delete = await store.search(
            collection_name=collection_name,
            query_embedding=query_embedding,
            limit=2
        )
        assert len(results_after_delete) == 1
        assert results_after_delete[0]["id"] == "chunk_2"
        assert results_after_delete[0]["text"] == "This is the second test chunk - UPDATED."
        
    finally:
        # Cleanup temp directory (handle Windows permission lock gracefully)
        try:
            shutil.rmtree(temp_dir)
        except PermissionError:
            pass
