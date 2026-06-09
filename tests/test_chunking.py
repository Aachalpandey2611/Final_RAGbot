import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock
from app.services.ingestion.chunkers import RecursiveCharacterChunker
from app.services.ingestion.loaders import TextLoader
from app.services.chunk import DocumentChunkService
from app.models.document import Document, DocumentChunk

def test_recursive_character_chunker():
    """Validates that the recursive character chunker divides text within sizes and maintains order."""
    chunker = RecursiveCharacterChunker()
    text = "This is paragraph one.\n\nThis is paragraph two. It has more text."
    
    # Chunk with large size (should return paragraphs split by double newline)
    chunks = chunker.chunk(text, chunk_size=50, chunk_overlap=10)
    assert len(chunks) == 2
    assert "paragraph one" in chunks[0]
    assert "paragraph two" in chunks[1]

def test_recursive_character_chunker_overlap():
    """Validates that overlap is correctly preserved between chunks."""
    chunker = RecursiveCharacterChunker(separators=[" "])
    text = "one two three four five six"
    
    # Split by spaces with chunk size 9 characters and 4 characters overlap
    # "one two" is 7 chars. "two three" is 9 chars.
    chunks = chunker.chunk(text, chunk_size=10, chunk_overlap=4)
    assert len(chunks) > 1
    # Check that overlapping words are preserved
    assert chunks[0] == "one two"
    assert chunks[1] == "two three"

@pytest.mark.asyncio
async def test_text_loader():
    """Validates that TextLoader extracts text and records base metadata."""
    loader = TextLoader()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as temp_file:
        temp_file.write("Hello, standard plain text document loader test!")
        temp_path = temp_file.name

    try:
        loaded = await loader.load(temp_path)
        assert len(loaded) == 1
        assert loaded[0]["text"] == "Hello, standard plain text document loader test!"
        assert loaded[0]["metadata"]["source"] == os.path.basename(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@pytest.mark.asyncio
async def test_document_chunk_service():
    """Validates that the DocumentChunkService coordinates parsing and chunk storage correctly."""
    # Mock database session
    db_mock = AsyncMock()

    # Mock repositories
    doc_repo_mock = AsyncMock()
    chunk_repo_mock = AsyncMock()

    # Mock document record
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as temp_file:
        temp_file.write("Paragraph one content.\n\nParagraph two content.")
        temp_path = temp_file.name

    mock_doc = Document(
        id=1,
        filename="secure-uuid.txt",
        original_filename="sample.txt",
        file_type="text/plain",
        file_path=temp_path,
        file_size=len("Paragraph one content.\n\nParagraph two content."),
        user_id=42
    )

    doc_repo_mock.get_by_id_and_owner.return_value = mock_doc
    chunk_repo_mock.delete_by_document.return_value = None
    chunk_repo_mock.create.side_effect = lambda data: DocumentChunk(id=100 + data.get("chunk_index"), **data)

    try:
        service = DocumentChunkService(db_mock)
        service.doc_repo = doc_repo_mock
        service.chunk_repo = chunk_repo_mock

        # Run chunking (size=25, overlap=0)
        chunks = await service.chunk_document(document_id=1, user_id=42, chunk_size=25, chunk_overlap=0)

        # We expect 2 chunks: "Paragraph one content." and "Paragraph two content."
        assert len(chunks) == 2
        assert chunks[0].chunk_index == 0
        assert chunks[0].content == "Paragraph one content."
        assert chunks[1].chunk_index == 1
        assert chunks[1].content == "Paragraph two content."
        
        # Verify repo calls
        doc_repo_mock.get_by_id_and_owner.assert_called_once_with(1, 42)
        chunk_repo_mock.delete_by_document.assert_called_once_with(1)
        assert chunk_repo_mock.create.call_count == 2
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
