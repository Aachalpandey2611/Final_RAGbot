import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.retrieval.retrieval_orchestrator import RetrievalOrchestrator
from app.models.document import DocumentChunk, Document

async def generate_report():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI_ASYNC)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    questions = [
        "How does Bill Inquiry determine whether to route to RJIL, JPL or JPL-RR?",
        "Describe the full flow of getBillingCreditDetails.",
        "A Postpaid customer initiates a Bill Plan Change through MyJio and provides payment details along with an EWallet Reservation Reference ID."
    ]
    
    with open("retrieval_report.md", "w", encoding="utf-8") as f:
        f.write("# Retrieval Debug Report\n\n")
        
        async with async_session() as db:
            orchestrator = RetrievalOrchestrator(db)
            
            for i, q in enumerate(questions, 1):
                f.write(f"## Question {i}: {q}\n\n")
                
                # We need to simulate the orchestrator process to log intermediate steps
                f.write("### 1. Vector Search Candidates\n")
                vector_res = await orchestrator.vector_search(q, user_id=None, top_k=20)
                for res in vector_res[:5]: # just show top 5 vector
                    chunk = res['chunk']
                    f.write(f"- ID: {chunk.id}, Document: {getattr(chunk, 'document_id', 'Unknown')}, Score: {res['score']:.4f}\n")
                    f.write(f"  Preview: {chunk.content[:100]}...\n")
                
                f.write("\n### 2. BM25 Candidates\n")
                bm25_res = await orchestrator.bm25_search(q, user_id=None, top_k=20)
                for res in bm25_res[:5]:
                    chunk = res['chunk']
                    f.write(f"- ID: {chunk.id}, Document: {getattr(chunk, 'document_id', 'Unknown')}, Score: {res['score']:.4f}\n")
                    f.write(f"  Preview: {chunk.content[:100]}...\n")
                
                f.write("\n### 3. Final Retrieval (Top 8)\n")
                results = await orchestrator.retrieve(q, top_k=8, user_id=None)
                chunks = results["chunks"]
                scores = results["retrieval_scores"]
                
                for idx, chunk in enumerate(chunks):
                    # fetch document name
                    doc_name = f"DocID: {getattr(chunk, 'document_id', 'Unknown')}"
                    
                    score = scores.get(chunk.id, 0.0)
                    f.write(f"**Rank {idx+1} | Score: {score:.4f} | Chunk ID: {chunk.id} | Document: {doc_name}**\n")
                    f.write(f"```text\n{chunk.content[:250]}...\n```\n\n")
                    
                f.write("---\n\n")

if __name__ == "__main__":
    asyncio.run(generate_report())
