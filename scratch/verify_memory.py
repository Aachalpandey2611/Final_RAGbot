import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Ensure backend directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.conversation import Message, Conversation
from app.services.rag.memory import ConversationMemoryService

async def main():
    print("--- Testing Conversation Memory ---")
    
    # 1. Initialize memory service with mock DB session
    mock_db = MagicMock()
    memory_service = ConversationMemoryService(mock_db)
    
    # Stub repositories
    memory_service.conv_repo = AsyncMock()
    memory_service.msg_repo = AsyncMock()
    
    # Mock conversation with messages
    mock_conv = Conversation(id=1, title="Test", user_id=1, summary="Old Summary Context")
    mock_conv.messages = [
        Message(id=101, conversation_id=1, role="user", content="Hello, I like pizza."),
        Message(id=102, conversation_id=1, role="assistant", content="Nice! Pizza is delicious."),
        Message(id=103, conversation_id=1, role="user", content="I prefer pepperoni topping."),
        Message(id=104, conversation_id=1, role="assistant", content="Got it. Pepperoni."),
        Message(id=105, conversation_id=1, role="user", content="Let's write some code now."),
        Message(id=106, conversation_id=1, role="assistant", content="Sure! What language?"),
    ]
    
    memory_service.conv_repo.get_with_messages.return_value = mock_conv
    
    print("\n1. Testing Context Retrieval (Session + Long-term)...")
    # Mock vector store search to return some historical context
    memory_service.vector_store.search = AsyncMock(return_value=[
        {
            "id": "101", # Belongs to early history
            "text": "Hello, I like pizza.",
            "metadata": {"role": "user"}
        },
        {
            "id": "106", # Part of session window, should be filtered out
            "text": "Sure! What language?",
            "metadata": {"role": "assistant"}
        }
    ])
    
    summary, long_term, recent = await memory_service.get_memory_context(
        conversation_id=1, user_id=1, query="What food do I like?", session_window=4
    )
    
    print(f"Loaded Summary: {summary}")
    print(f"Long-term Memories (excluding active session): {long_term}")
    print(f"Recent Active Messages (last 4): {[m.content for m in recent]}")
    
    # Assertions check
    assert len(long_term) == 1, f"Expected 1 filtered long term memory, got {len(long_term)}"
    assert long_term[0]["content"] == "Hello, I like pizza."
    print("Success: Session / Long-term separation verified!")
    
    # 2. Testing Context Compression (Summarization)
    print("\n2. Testing Context Compression trigger...")
    # Add more mock messages to exceed threshold (12 messages > 10 threshold)
    mock_conv.messages = [
        Message(id=i, conversation_id=1, role="user" if i % 2 == 0 else "assistant", content=f"Message {i}")
        for i in range(12)
    ]
    
    memory_service.llm.generate_response = AsyncMock(return_value="Condensation of the user's coding request.")
    
    await memory_service.compress_context(conversation_id=1, user_id=1, threshold=10, keep_recent=4)
    called_args = memory_service.conv_repo.update.call_args
    assert called_args is not None, "Expected update to be called on repository"
    print(f"Updated Summary in DB: {called_args[0][1]['summary']}")
    print("Success: Context Compression verified!")

if __name__ == "__main__":
    asyncio.run(main())
