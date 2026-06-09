import asyncio
import json
from app.core.database import AsyncSessionLocal
from app.repositories.user import UserRepository
from app.services.conversation import ConversationService
from app.services.rag.rag_service import RAGService

async def main():
    print("============================================================")
    print("RAG PIPELINE END-TO-END VERIFICATION")
    print("============================================================\n")

    async with AsyncSessionLocal() as db:
        # 1. Get Test User
        user_repo = UserRepository(db)
        test_user = await user_repo.get_by_email("testuser_e2e@example.com")
        if not test_user:
            print("[ERROR] Test user not found. Please run e2e_verify.py first to seed the database.")
            return
        
        user_id = test_user.id
        print(f"[OK] Found test user (ID: {user_id})")

        # 2. Create a new Conversation
        conv_service = ConversationService(db)
        conversation = await conv_service.create_conversation(
            user_id=user_id, 
            title="Policy Inquiry"
        )
        print(f"[OK] Created new conversation (ID: {conversation.id})")

        # 3. Initialize RAG Service
        rag_service = RAGService(db)
        
        # 4. Ask a question
        query = "What is the leave policy for full-time employees?"
        print(f"\n[USER QUESTION]: {query}")
        print("\n... Generating answer via RAG Pipeline ...\n")
        
        response = await rag_service.generate_answer(
            query=query, 
            conversation_id=conversation.id, 
            user_id=user_id
        )

        # 5. Print Results
        print("------------------------------------------------------------")
        print("AI RESPONSE:")
        print("------------------------------------------------------------")
        print(response["answer"])
        print("\n------------------------------------------------------------")
        print("CITATIONS:")
        print("------------------------------------------------------------")
        for citation in response["citations"]:
            print(f"- [Source {citation['source_index']}] {citation['filename']} (Distance: {citation['distance_score']:.4f})")
            
        print(f"\nModel Used: {response['model_used']}")

        # 6. Verify Database History
        print("\n[OK] Verifying Conversation History in Database...")
        history = await conv_service.list_messages(conversation.id, user_id)
        messages = history.get("messages", [])
        
        if len(messages) == 2:
            print("[OK] Verified exactly 2 messages in conversation history (User + Assistant).")
        else:
            print(f"[WARNING] Expected 2 messages, found {len(messages)}.")

    print("\n============================================================")
    print("ALL RAG VERIFICATION STEPS COMPLETE!")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
