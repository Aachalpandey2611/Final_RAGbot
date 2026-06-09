import asyncio
import os
import sys

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.core.database import AsyncSessionLocal, engine
from app.controllers.admin import list_users, get_system_analytics, get_all_conversations

async def main():
    print("--- Testing Admin Dashboard ---")
    
    # 1. Initialize DB Session
    async with engine.connect() as conn:
        print("Connected to database successfully.")
        
    async with AsyncSessionLocal() as db:
        print("\n1. Running User list query...")
        users = await list_users(skip=0, limit=5, db=db)
        print(f"Total Users in DB: {users['total']}")
        for u in users['users']:
            print(f"- Email: {u.email}, Role: {u.role}, Active: {u.is_active}")
            
        print("\n2. Running System Analytics query...")
        analytics = await get_system_analytics(db=db)
        print(f"Analytics Summary: {analytics}")
        
        print("\n3. Running Conversations audit query...")
        convs = await get_all_conversations(skip=0, limit=5, db=db)
        print(f"Total conversations audited: {len(convs)}")
        for c in convs:
            print(f"- Title: {c.title}, Owner: {getattr(c, 'owner_email', 'None')}, Messages: {getattr(c, 'message_count', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
