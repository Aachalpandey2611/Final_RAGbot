import asyncio
import sys
import importlib
import types
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Workaround: avoid importing app.models.__init__ which pulls in many models and
# may have cross-relationship issues. Inject a minimal app.models package and
# load only app.models.base and app.models.binary.
from importlib.machinery import SourceFileLoader
from pathlib import Path

# Load app.models.base directly from file (avoid executing app.models.__init__)
base_path = Path(__file__).resolve().parents[1] / 'app' / 'models' / 'base.py'
loader = SourceFileLoader('app.models.base', str(base_path))
module_base = types.ModuleType('app.models.base')
loader.exec_module(module_base)
sys.modules['app.models.base'] = module_base

# Create a minimal app.models package and attach the base module to it
mod = types.ModuleType('app.models')
mod.base = module_base
models_dir = Path(__file__).resolve().parents[1] / 'app' / 'models'
mod.__path__ = [str(models_dir)]
sys.modules['app.models'] = mod

from app.models.base import Base
from importlib import import_module
# Now import the binary models submodule without triggering app.models.__init__
binary_models = import_module('app.models.binary')
BinaryJob = binary_models.BinaryJob
BinaryFile = binary_models.BinaryFile
BinaryRelationship = binary_models.BinaryRelationship

from app.services.binary.extractor import BinaryExtractor
import io, zipfile

DB_URL = "sqlite+aiosqlite:///:memory:"

async def run():
    engine = create_async_engine(DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    # create a small zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('hello.txt', 'hello world')
        z.writestr('dir/readme.md', '# readme')
    data = buf.getvalue()

    extractor = BinaryExtractor()
    res = extractor.extract('test.zip', data, job_id='inttest')
    print('Extracted files:', len(res.extracted_files))

    # Persist directly using the ORM models to avoid importing package-level repository init
    async with AsyncSessionLocal() as db:
        job = BinaryJob(id='inttest', filename='test.zip', status='pending', job_metadata=res.metadata)
        db.add(job)
        await db.flush()
        for f in res.extracted_files:
            bf = BinaryFile(job_id='inttest', path=f.get('path'), size=f.get('size'), sha256=f.get('sha256'), mime_type=f.get('mime_type'), extra={k: v for k, v in f.items() if k not in ('path','size','sha256','mime_type')})
            db.add(bf)
        for r in res.relationships:
            br = BinaryRelationship(job_id='inttest', parent=r.get('parent'), child=r.get('child'), relation_type=r.get('type','contains'))
            db.add(br)
        await db.flush()

        # Load back details
        from sqlalchemy import select
        job_q = select(BinaryJob).where(BinaryJob.id == 'inttest')
        job_res = await db.execute(job_q)
        job_loaded = job_res.scalar_one()
        files_q = select(BinaryFile).where(BinaryFile.job_id == 'inttest')
        files_res = await db.execute(files_q)
        files_loaded = files_res.scalars().all()
        print('Persisted job:', job_loaded.id, 'files:', len(files_loaded))

if __name__ == '__main__':
    asyncio.run(run())
