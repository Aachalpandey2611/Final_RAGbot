import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.repositories.conversation import ConversationRepository, MessageRepository
from app.services.embeddings.factory import get_embedding_provider
from app.services.vector_store import get_vector_store
from app.services.llm import get_llm_provider

logger = logging.getLogger(__name__)

class ConversationMemoryService:
    """
    Manages multi-tier conversation memory:
    - Session Memory (Sliding window of recent messages)
    - Long-term Memory (Semantic search over past messages using ChromaDB)
    - Context Compression (LLM-based summarization of historical messages)
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)
        self.embedding_provider = get_embedding_provider("huggingface")
        self.vector_store = get_vector_store()
        self.llm = get_llm_provider("gemini")

    async def get_memory_context(
        self, 
        conversation_id: int, 
        user_id: int, 
        query: str, 
        session_window: int = 6
    ) -> Tuple[Optional[str], List[Dict[str, Any]], List[Message]]:
        """
        Retrieves the running summary (compressed context), 
        long-term semantically matching past messages, 
        and the recent active session messages (Session Window).
        """
        # 1. Fetch running summary and messages from conversation model
        conversation = await self.conv_repo.get_with_messages(conversation_id, user_id)
        if not conversation:
            return None, [], []

        all_messages = conversation.messages
        if not all_messages:
            return None, [], []

        # 2. Extract Session Memory (Recent Window)
        session_messages = all_messages[-session_window:]
        session_message_ids = {msg.id for msg in session_messages}

        # 3. Retrieve Long-term Memory (Vector matches from older messages)
        long_term_memories = []
        try:
            query_emb = await self.embedding_provider.embed_text(query)
            search_results = await self.vector_store.search(
                collection_name="conversation_messages",
                query_embedding=query_emb,
                limit=3,
                where={"conversation_id": conversation_id}
            )
            for res in search_results:
                msg_id = int(res['id'])
                # Filter out messages currently in the active session window
                if msg_id not in session_message_ids:
                    long_term_memories.append({
                        "role": res["metadata"].get("role"),
                        "content": res["text"]
                    })
            logger.info(f"Retrieved {len(long_term_memories)} relevant long-term messages.")
        except Exception as e:
            logger.error(f"Error querying long-term conversation memory: {str(e)}")

        return conversation.summary, long_term_memories, session_messages

    async def index_message(self, message: Message, user_id: int):
        """
        Indexes a newly created chat message in ChromaDB for future long-term retrieval.
        """
        try:
            emb = await self.embedding_provider.embed_text(message.content)
            await self.vector_store.insert(
                collection_name="conversation_messages",
                ids=[str(message.id)],
                embeddings=[emb],
                metadatas=[{
                    "conversation_id": message.conversation_id,
                    "user_id": user_id,
                    "role": str(message.role),
                    "created_at": message.created_at.isoformat()
                }],
                documents=[message.content]
            )
            logger.info(f"Indexed message {message.id} to conversation_messages collection.")
        except Exception as e:
            logger.error(f"Failed to index message {message.id}: {str(e)}")

    async def compress_context(self, conversation_id: int, user_id: int, threshold: int = 10, keep_recent: int = 4):
        """
        Triggers summary compression if history exceeds the threshold.
        Summarizes older messages while keeping the most recent active messages clear.
        """
        conversation = await self.conv_repo.get_with_messages(conversation_id, user_id)
        if not conversation or len(conversation.messages) <= threshold:
            return

        logger.info(f"Compressing context for conversation_id={conversation_id}...")
        
        # Keep the most recent messages untouched
        messages_to_summarize = conversation.messages[:-keep_recent]
        
        formatted_history = "\n".join([
            f"{str(msg.role).upper()}: {msg.content}"
            for msg in messages_to_summarize
        ])
        
        prompt = (
            f"You are a system assistant. Condense and summarize the following chat history "
            f"into a concise summary (max 3 sentences) that captures key facts, preferences, "
            f"and themes mentioned by the user and assistant. Include any previous summary context "
            f"if helpful.\n\n"
            f"Previous Summary Context: {conversation.summary or 'None'}\n\n"
            f"Chat History to Compress:\n{formatted_history}\n\n"
            f"Concise Summary:"
        )
        
        try:
            summary_text = await self.llm.generate_response(prompt)
            # Update database
            await self.conv_repo.update(conversation, {"summary": summary_text})
            logger.info(f"Context compression complete. Summary: {summary_text}")
        except Exception as e:
            logger.error(f"Failed to compress context/summarize conversation: {str(e)}")
