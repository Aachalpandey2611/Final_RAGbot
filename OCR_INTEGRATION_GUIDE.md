"""
OCR Service Integration Guide

This guide shows how to integrate the OCR service with existing components
in your application (RAG, Document Management, etc.)
"""

# ============================================================================

# 1. INTEGRATION WITH DOCUMENT MANAGEMENT

# ============================================================================

"""
Link OCR results to Document model for comprehensive document processing.
"""

# In app/services/document.py

from app.services.ocr_service import OCRService
from app.models.document import Document
from app.models.ocr import OCRJob
from app.repositories.ocr import OCRJobRepository

class DocumentService:
def **init**(self):
self.ocr_service = OCRService()

    async def process_document_with_ocr(
        self,
        document_id: str,
        file_path: str,
        user_id: str,
        db: Session,
    ) -> Document:
        """Process document and extract text via OCR"""

        # Get document
        doc_repo = DocumentRepository(db)
        document = doc_repo.get(document_id)

        # Extract text with OCR
        ocr_result = await self.ocr_service.extract_text_from_file(
            file_path,
            provider="paddle",
            languages=["en"],
        )

        # Store OCR job
        ocr_repo = OCRJobRepository(db)
        ocr_job = ocr_repo.create(
            user_id=user_id,
            file_name=document.name,
            file_path=file_path,
            provider="paddle",
            extracted_text=ocr_result.text,
            text_regions=[r.to_dict() for r in ocr_result.regions],
            tables=[t.to_dict() for t in ocr_result.tables],
            overall_confidence=ocr_result.overall_confidence,
            status="completed",
        )

        # Link OCR job to document
        document.ocr_job_id = ocr_job.id
        document.extracted_text = ocr_result.text
        db.commit()

        return document

# ============================================================================

# 2. INTEGRATION WITH RAG PIPELINE

# ============================================================================

"""
Use OCR extracted text as input to RAG chunking and embedding.
"""

# In app/services/rag_service.py

from app.services.ocr_service import OCRService
from app.services.chunk import ChunkService
from app.services.embedding import EmbeddingService

class RAGWithOCR:
def **init**(self):
self.ocr_service = OCRService()
self.chunk_service = ChunkService()
self.embedding_service = EmbeddingService()

    async def process_document_for_rag(
        self,
        file_path: str,
        user_id: str,
        document_id: str,
        db: Session,
    ):
        """Extract OCR text, chunk it, and embed it"""

        # 1. Extract text with OCR
        ocr_result = await self.ocr_service.extract_text_from_file(
            file_path,
            provider="paddle",
            languages=["en"],
            preprocess=True,
        )

        # 2. Filter by confidence
        high_confidence_text = " ".join([
            r.text for r in ocr_result.regions
            if r.confidence > 0.7
        ])

        # 3. Chunk the text
        chunks = self.chunk_service.chunk_text(
            text=high_confidence_text,
            chunk_size=512,
            overlap=50,
        )

        # 4. Embed chunks
        for chunk in chunks:
            embedding = await self.embedding_service.embed_text(chunk)
            # Store in vector database
            await vector_store.add_document(
                document_id=document_id,
                text=chunk,
                embedding=embedding,
            )

        return {
            "ocr_confidence": ocr_result.overall_confidence,
            "chunks": len(chunks),
            "tables_extracted": len(ocr_result.tables),
        }

# ============================================================================

# 3. INTEGRATION WITH CONVERSATION/CHAT

# ============================================================================

"""
Use OCR for document-based conversation and Q&A.
"""

# In app/services/conversation.py

async def chat_about_document(
conversation_id: str,
document_id: str,
user_message: str,
db: Session,
):
"""Enable chat about OCR-extracted document"""

    # Get document and OCR results
    doc_repo = DocumentRepository(db)
    document = doc_repo.get(document_id)

    ocr_repo = OCRJobRepository(db)
    ocr_job = ocr_repo.get(document.ocr_job_id)

    # Get relevant context using RAG
    context = await rag_service.retrieve(
        query=user_message,
        document_ids=[document_id],
        top_k=3,
    )

    # Generate response using LLM
    response = await llm_service.generate(
        prompt=f"""
        Document: {ocr_job.extracted_text[:2000]}

        Context: {context}

        User: {user_message}
        """,
        conversation_history=conversation.messages,
    )

    # Store conversation
    message = Message(
        conversation_id=conversation_id,
        user_id=document.user_id,
        content=user_message,
        response=response,
    )
    db.add(message)
    db.commit()

    return response

# ============================================================================

# 4. INTEGRATION WITH BACKGROUND TASKS

# ============================================================================

"""
Process documents asynchronously in background.
"""

# In app/tasks.py

from app.tasks_ocr import process_ocr_file

@celery_app.task
def process_document_pipeline(document_id: str, file_path: str, user_id: str):
"""Complete document processing pipeline"""

    db = SessionLocal()
    try:
        # 1. Extract OCR
        ocr_task = process_ocr_file.delay(
            job_id=f"doc-{document_id}",
            file_path=file_path,
            provider="paddle",
            languages=["en"],
        )

        # 2. Wait for OCR completion
        ocr_result = ocr_task.get(timeout=300)

        # 3. Chunk and embed
        chunk_task = chunk_and_embed_document.delay(
            document_id=document_id,
            user_id=user_id,
            text=ocr_result["text"],
        )

        # 4. Update document status
        doc = DocumentRepository(db).get(document_id)
        doc.status = "processed"
        db.commit()

    finally:
        db.close()

# ============================================================================

# 5. INTEGRATION WITH SEARCH/INDEXING

# ============================================================================

"""
Index OCR results for full-text search and retrieval.
"""

# In app/services/search.py

from elasticsearch import Elasticsearch

class SearchService:
def **init**(self):
self.es = Elasticsearch(["localhost:9200"])

    async def index_ocr_result(self, ocr_job_id: str, ocr_result: dict):
        """Index OCR results in Elasticsearch"""

        self.es.index(
            index="ocr_documents",
            id=ocr_job_id,
            body={
                "text": ocr_result["text"],
                "confidence": ocr_result["overall_confidence"],
                "regions": ocr_result["regions"],
                "tables": ocr_result["tables"],
                "languages": ocr_result["languages_detected"],
                "timestamp": datetime.utcnow(),
            }
        )

    async def search_ocr_documents(self, query: str, user_id: str):
        """Search OCR-extracted documents"""

        results = self.es.search(
            index="ocr_documents",
            query={
                "bool": {
                    "must": [
                        {"match": {"text": query}},
                        {"term": {"user_id": user_id}},
                    ]
                }
            },
            size=20,
        )

        return results["hits"]["hits"]

# ============================================================================

# 6. INTEGRATION WITH DATA EXPORT

# ============================================================================

"""
Export OCR results in various formats.
"""

# In app/services/export.py

class OCRExportService:
async def export_ocr_as_json(self, ocr_job_id: str, db: Session):
"""Export OCR results as JSON"""
ocr_repo = OCRJobRepository(db)
job = ocr_repo.get(ocr_job_id)

        return {
            "job_id": job.id,
            "file_name": job.file_name,
            "text": job.extracted_text,
            "regions": job.text_regions,
            "tables": job.tables,
            "metadata": {
                "confidence": job.overall_confidence,
                "processing_time_ms": job.processing_time_ms,
                "provider": job.provider,
                "languages": job.languages,
            },
        }

    async def export_ocr_as_pdf(self, ocr_job_id: str, db: Session):
        """Export OCR results as PDF with highlights"""
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        ocr_repo = OCRJobRepository(db)
        job = ocr_repo.get(ocr_job_id)

        c = canvas.Canvas("ocr_result.pdf", pagesize=letter)
        c.setFont("Helvetica", 12)

        # Write extracted text
        text_object = c.beginText(40, 750)
        text_object.setFont("Helvetica", 10)
        text_object.textLines(job.extracted_text)
        c.drawText(text_object)

        # Draw bounding boxes
        for region in job.text_regions:
            bbox = region["bbox"]
            c.rect(bbox[0], bbox[1], bbox[2]-bbox[0], bbox[3]-bbox[1])

        c.save()
        return "ocr_result.pdf"

    async def export_ocr_as_csv(self, ocr_job_id: str, db: Session):
        """Export OCR regions as CSV"""
        import csv
        import io

        ocr_repo = OCRJobRepository(db)
        job = ocr_repo.get(ocr_job_id)

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["Text", "Confidence", "X1", "Y1", "X2", "Y2", "Language"])

        for region in job.text_regions:
            writer.writerow([
                region["text"],
                region["confidence"],
                region["bbox"][0],
                region["bbox"][1],
                region["bbox"][2],
                region["bbox"][3],
                region.get("language", ""),
            ])

        return output.getvalue()

# ============================================================================

# 7. API ENDPOINT INTEGRATION

# ============================================================================

"""
Create endpoints that combine OCR with other services.
"""

# In app/controllers/ocr_integration.py

from fastapi import APIRouter, File, UploadFile, Depends

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])

@router.post("/upload-and-process")
async def upload_and_process_document(
file: UploadFile = File(...),
db: Session = Depends(get_db),
current_user: dict = Depends(get_current_user),
):
"""Upload document and process with OCR + RAG"""

    # 1. Save file
    import tempfile
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # 2. Create document record
    doc = DocumentRepository(db).create(
        user_id=current_user["id"],
        name=file.filename,
        file_path=tmp_path,
        status="processing",
    )

    # 3. Queue processing pipeline
    from app.tasks import process_document_pipeline
    process_document_pipeline.delay(
        document_id=doc.id,
        file_path=tmp_path,
        user_id=current_user["id"],
    )

    return {
        "document_id": doc.id,
        "status": "processing",
        "message": "Document uploaded and queued for processing",
    }

@router.get("/extract/{document_id}")
async def get_extracted_text(
document_id: str,
db: Session = Depends(get_db),
current_user: dict = Depends(get_current_user),
):
"""Get OCR extracted text for document"""

    doc = DocumentRepository(db).get(document_id)
    if not doc or doc.user_id != current_user["id"]:
        raise HTTPException(status_code=404)

    ocr_job = OCRJobRepository(db).get(doc.ocr_job_id)
    if not ocr_job:
        raise HTTPException(status_code=404)

    return {
        "document_id": document_id,
        "text": ocr_job.extracted_text,
        "confidence": ocr_job.overall_confidence,
        "regions": ocr_job.text_regions,
        "tables": ocr_job.tables,
        "processing_time_ms": ocr_job.processing_time_ms,
    }

@router.post("/search")
async def search_documents(
query: str,
db: Session = Depends(get_db),
current_user: dict = Depends(get_current_user),
):
"""Search OCR-extracted text in documents"""

    from app.services.search import SearchService
    search_service = SearchService()

    results = await search_service.search_ocr_documents(
        query=query,
        user_id=current_user["id"],
    )

    return {
        "query": query,
        "results_count": len(results),
        "results": results,
    }

# ============================================================================

# 8. MONITORING & METRICS INTEGRATION

# ============================================================================

"""
Track OCR performance and quality metrics.
"""

# In app/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# OCR Metrics

ocr_files_processed = Counter(
"ocr_files_processed_total",
"Total OCR files processed",
["provider", "status"],
)

ocr_processing_time = Histogram(
"ocr_processing_time_seconds",
"OCR processing time in seconds",
["provider"],
)

ocr_confidence_score = Histogram(
"ocr_confidence_score",
"OCR confidence scores",
buckets=[0.0, 0.3, 0.5, 0.7, 0.9, 0.95, 1.0],
)

ocr_active_jobs = Gauge(
"ocr_active_jobs",
"Active OCR jobs",
["status"],
)

# Usage in service

async def process_with_metrics(ocr_service, file_path, provider):
import time

    start = time.time()
    try:
        result = await ocr_service.extract_text_from_file(
            file_path,
            provider=provider,
        )

        duration = time.time() - start

        # Record metrics
        ocr_files_processed.labels(
            provider=provider,
            status="success"
        ).inc()

        ocr_processing_time.labels(provider=provider).observe(duration)
        ocr_confidence_score.observe(result.overall_confidence)

        return result

    except Exception as e:
        ocr_files_processed.labels(
            provider=provider,
            status="error"
        ).inc()
        raise

# ============================================================================

# 9. NOTIFICATION INTEGRATION

# ============================================================================

"""
Notify users when OCR processing completes.
"""

# In app/services/notification.py

from app.core.email import send_email

async def notify_ocr_completion(user_id: str, document_id: str, db: Session):
"""Send email notification when OCR completes"""

    user = UserRepository(db).get(user_id)
    doc = DocumentRepository(db).get(document_id)
    ocr_job = OCRJobRepository(db).get(doc.ocr_job_id)

    await send_email(
        to=user.email,
        subject=f"Document Processing Complete: {doc.name}",
        html=f"""
        <h1>Document Processing Complete</h1>
        <p>Your document has been processed with OCR.</p>
        <ul>
            <li>Confidence: {ocr_job.overall_confidence:.2%}</li>
            <li>Words Extracted: {len(ocr_job.extracted_text.split())}</li>
            <li>Tables Found: {len(ocr_job.tables)}</li>
            <li>Processing Time: {ocr_job.processing_time_ms:.0f}ms</li>
        </ul>
        <p><a href="...">View Document</a></p>
        """,
    )

# ============================================================================

# 10. TESTING INTEGRATION

# ============================================================================

"""
Integration tests with OCR service.
"""

# In tests/test_ocr_integration.py

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
return TestClient(app)

@pytest.fixture
def auth_headers(client):
response = client.post("/api/v1/auth/login", json={
"email": "test@example.com",
"password": "password",
})
return {"Authorization": f"Bearer {response.json()['access_token']}"}

def test_ocr_extraction(client, auth_headers):
"""Test direct OCR extraction"""
with open("tests/fixtures/test_image.png", "rb") as f:
response = client.post(
"/api/v1/ocr/extract",
files={"file": f},
headers=auth_headers,
)

    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert "overall_confidence" in data
    assert data["overall_confidence"] > 0

def test_document_processing_pipeline(client, auth_headers):
"""Test complete document processing pipeline"""
with open("tests/fixtures/test_pdf.pdf", "rb") as f:
response = client.post(
"/api/v1/documents/upload-and-process",
files={"file": f},
headers=auth_headers,
)

    assert response.status_code == 200
    document_id = response.json()["document_id"]

    # Poll for completion
    for _ in range(60):  # 60 seconds timeout
        response = client.get(
            f"/api/v1/documents/{document_id}",
            headers=auth_headers,
        )
        if response.json()["status"] == "completed":
            break
        time.sleep(1)

    # Verify results
    assert response.json()["status"] == "completed"
    assert "ocr_job_id" in response.json()
