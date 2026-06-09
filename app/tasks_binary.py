import asyncio
from app.core.celery_app import celery_app
from app.services.binary import BinaryExtractor
from app.core.database import AsyncSessionLocal
from app.repositories import binary as binary_repo


@celery_app.task(name="app.tasks_binary.process_binary")
def process_binary(job_id: str, filename: str, data: bytes):
    extractor = BinaryExtractor()
    result = extractor.extract(filename, data, job_id=job_id)

    async def _persist():
        async with AsyncSessionLocal() as db:
            await binary_repo.create_job(db, job_id, filename, result.metadata)
            await binary_repo.add_files(db, job_id, result.extracted_files)
            await binary_repo.add_relationships(db, job_id, result.relationships)
            await binary_repo.set_job_status(db, job_id, "completed")

    asyncio.run(_persist())
    return {"job_id": job_id, "files_count": len(result.extracted_files)}
