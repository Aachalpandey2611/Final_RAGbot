import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE conversation ADD COLUMN IF NOT EXISTS summary TEXT"))
        print("Migration complete: added 'summary' column to conversation table.")

if __name__ == "__main__":
    asyncio.run(migrate())
