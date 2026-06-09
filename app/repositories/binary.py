from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from typing import List, Dict, Any
from app.models.binary import BinaryJob, BinaryFile, BinaryRelationship


async def create_job(db: AsyncSession, job_id: str, filename: str, metadata: Dict[str, Any]) -> BinaryJob:
    job = BinaryJob(id=job_id, filename=filename, status="pending", job_metadata=metadata)
    db.add(job)
    await db.flush()
    return job


async def set_job_status(db: AsyncSession, job_id: str, status: str):
    q = select(BinaryJob).where(BinaryJob.id == job_id)
    res = await db.execute(q)
    job = res.scalar_one_or_none()
    if job:
        job.status = status
        await db.flush()
    return job


async def add_files(db: AsyncSession, job_id: str, files: List[Dict[str, Any]]):
    for f in files:
        bf = BinaryFile(job_id=job_id, path=f.get("path"), size=f.get("size"), sha256=f.get("sha256"), mime_type=f.get("mime_type"), extra={k: v for k, v in f.items() if k not in ("path", "size", "sha256", "mime_type")})
        db.add(bf)
    await db.flush()


async def add_relationships(db: AsyncSession, job_id: str, rels: List[Dict[str, str]]):
    for r in rels:
        br = BinaryRelationship(job_id=job_id, parent=r.get("parent"), child=r.get("child"), relation_type=r.get("type", "contains"))
        db.add(br)
    await db.flush()


async def get_job_details(db: AsyncSession, job_id: str) -> Dict[str, Any]:
    q = select(BinaryJob).where(BinaryJob.id == job_id)
    res = await db.execute(q)
    job = res.scalar_one_or_none()
    if not job:
        return None
    files_q = select(BinaryFile).where(BinaryFile.job_id == job_id)
    rel_q = select(BinaryRelationship).where(BinaryRelationship.job_id == job_id)
    files_res = await db.execute(files_q)
    rels_res = await db.execute(rel_q)
    files = [dict(path=f.path, size=f.size, sha256=f.sha256, mime_type=f.mime_type, extra=f.extra) for f in files_res.scalars().all()]
    rels = [dict(parent=r.parent, child=r.child, type=r.relation_type) for r in rels_res.scalars().all()]
    return {"job": {"id": job.id, "filename": job.filename, "status": job.status, "metadata": job.job_metadata}, "files": files, "relationships": rels}
