import tempfile
import os
from unittest.mock import AsyncMock

from app.services.chunk import DocumentChunkService
from app.models.document import Document, DocumentChunk


async def run_integration_like_test():
    # Create temporary text file simulating upload
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as temp_file:
        temp_file.write("Section 1: Intro\nThis is an intro.\n\nSection 2: Details\nSome details here.")
        temp_path = temp_file.name

    try:
        db_mock = AsyncMock()
        doc_repo_mock = AsyncMock()
        chunk_repo_mock = AsyncMock()

        mock_doc = Document(
            id=2,
            filename=os.path.basename(temp_path),
            original_filename="policy.txt",
            file_type="text/plain",
            file_path=temp_path,
            file_size=os.path.getsize(temp_path),
            user_id=99
        )

        doc_repo_mock.get_by_id_and_owner.return_value = mock_doc
        chunk_repo_mock.delete_by_document.return_value = None
        chunk_repo_mock.create.side_effect = lambda data: DocumentChunk(id=200 + data.get("chunk_index"), **data)

        service = DocumentChunkService(db_mock)
        service.doc_repo = doc_repo_mock
        service.chunk_repo = chunk_repo_mock

        created_chunks = await service.chunk_document(document_id=2, user_id=99)

        # Ensure chunks created and metadata fields present
        assert len(created_chunks) >= 2
        for c in created_chunks:
            assert hasattr(c, "chunk_type")
            assert c.chunking_strategy_used == "adaptive"
            # page_number may be None for txt files
        # Verify repository create calls
        assert chunk_repo_mock.create.call_count == len(created_chunks)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_run():
    import asyncio
    asyncio.run(run_integration_like_test())


if __name__ == "__main__":
    test_run()
