import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.services.binary import BinaryExtractor
from app.schemas.binary import BinaryExtractResponse, BinaryJobDetails
from app.core.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import binary as binary_repo
from app.services.binary.graph import build_graph_json

router = APIRouter()


@router.post("/api/v1/binary/extract", response_model=BinaryExtractResponse)
async def extract_binary(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    contents = await file.read()
    job_id = str(uuid.uuid4())
    extractor = BinaryExtractor()
    result = extractor.extract(file.filename, contents, job_id=job_id)
    # persist job and files
    await binary_repo.create_job(db, job_id, file.filename, result.metadata)
    await binary_repo.add_files(db, job_id, result.extracted_files)
    await binary_repo.add_relationships(db, job_id, result.relationships)
    await binary_repo.set_job_status(db, job_id, "completed")
    return BinaryExtractResponse(job_id=job_id, files_count=len(result.extracted_files), metadata=result.metadata)


@router.get("/api/v1/binary/job/{job_id}", response_model=BinaryJobDetails)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    details = await binary_repo.get_job_details(db, job_id)
    if not details:
        raise HTTPException(status_code=404, detail="Job not found")
    return details


@router.get("/api/v1/binary/job/{job_id}/graph")
async def get_job_graph(job_id: str, db: AsyncSession = Depends(get_db)):
    details = await binary_repo.get_job_details(db, job_id)
    if not details:
        raise HTTPException(status_code=404, detail="Job not found")
    rels = details.get("relationships", [])
    graph_json = build_graph_json(rels)
    return JSONResponse(content=graph_json)
