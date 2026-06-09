import json
import logging
from typing import Dict, Any, List, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.conversation import ConversationService
from app.services.llm import get_llm_provider
try:
    from app.services.retrieval.retrieval_orchestrator import RetrievalOrchestrator as RetrievalImpl
except Exception:
    from .retriever import Retriever as RetrievalImpl
from .context_builder import ContextBuilder
from .prompt_builder import PromptBuilder
from app.services.rag.memory import ConversationMemoryService
from app.services.rag.validation import ValidationService

logger = logging.getLogger(__name__)

class RAGService:
    """
    Orchestrates the entire Retrieval-Augmented Generation pipeline.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_service = ConversationService(db)
        # Use RetrievalOrchestrator when available, fallback to legacy Retriever
        self.retriever = RetrievalImpl(db)
        self.validator = ValidationService()
        self.memory_service = ConversationMemoryService(db)
        self.llm = get_llm_provider("gemini")

    async def generate_answer(self, query: str, conversation_id: int, user_id: int) -> Dict[str, Any]:
        """
        Executes the RAG pipeline to generate an answer.
        """
        logger.info(f"RAG Service starting for query: '{query}'")
        
        # 1. Save user's question to DB
        user_msg = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=query
        )
        
        # Index user message for long-term memory
        await self.memory_service.index_message(user_msg, user_id)
        
        # 2. Get Memory Context
        summary, long_term, recent_history = await self.memory_service.get_memory_context(
            conversation_id=conversation_id,
            user_id=user_id,
            query=query,
            session_window=6
        )
        
        # 3. Query Expansion
        try:
            expansion_prompt = f"Extract 5 critical keywords, entities, and routing identifiers from this query: '{query}'. Return ONLY space-separated keywords."
            keywords = await self.llm.generate_response(expansion_prompt)
            search_query = f"{query} {keywords}"
        except Exception:
            search_query = query

        # 4. First Retrieval Pass
        retrieval_res = await self.retriever.retrieve(search_query, top_k=8, user_id=user_id)
        if isinstance(retrieval_res, dict):
            chunks = retrieval_res.get("chunks", [])
            retrieval_scores = retrieval_res.get("retrieval_scores", [])
        else:
            chunks = retrieval_res
            retrieval_scores = []
            
        # 5. Multi-Hop Retrieval & Validation
        is_valid, confidence = self.validator.validate(retrieval_scores, len(chunks))
        if len(chunks) > 0 and confidence < 0.8:
            try:
                top_context = " ".join([getattr(c, 'content', '') for c in chunks[:3]])
                hop_prompt = f"Identify missing logic conditions or routing branches related to: '{query}' based on this partial context: '{top_context[:1000]}'. Return ONLY 3-5 keywords for a follow-up search."
                hop_keywords = await self.llm.generate_response(hop_prompt)
                
                hop_res = await self.retriever.retrieve(f"{query} {hop_keywords}", top_k=5, user_id=user_id)
                if isinstance(hop_res, dict):
                    hop_chunks = hop_res.get("chunks", [])
                    existing_ids = set([getattr(c, 'id', -1) for c in chunks])
                    for hc in hop_chunks:
                        hc_id = getattr(hc, 'id', -1)
                        if hc_id not in existing_ids:
                            chunks.append(hc)
                            existing_ids.add(hc_id)
            except Exception as e:
                logger.error(f"Multi-hop failed: {e}")

        # Validation: ensure retrieved context is reliable before calling LLM
        is_valid, confidence = self.validator.validate(retrieval_scores, len(chunks))
        if not is_valid:
            fallback = "I could not find reliable information in the knowledge base."
            citations = []
            # Save assistant response and index, keep behavior consistent
            assistant_msg = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=fallback,
            )
            await self.memory_service.index_message(assistant_msg, user_id)
            await self.memory_service.compress_context(conversation_id, user_id, threshold=10)
            logger.info(f"RAG Service aborted: validation failed (confidence={confidence})")
            return {"answer": fallback, "citations": citations, "model_used": self.llm.model_name}

        # 4. Build Context & Citations
        context_string, citations = ContextBuilder.build_context(chunks)
        
        # 5. Build Prompt
        prompt = PromptBuilder.build(
            query=query,
            context=context_string,
            history=recent_history,
            summary=summary,
            long_term_memory=long_term,
            response_mode="normal",
            response_length="standard"
        )
        
        # 6. Generate Response from LLM
        response_text = await self.llm.generate_response(prompt)
        
        # 7. Save AI's response to DB
        assistant_msg = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=response_text
        )
        
        # Index assistant response for long-term memory
        await self.memory_service.index_message(assistant_msg, user_id)
        
        # Compress history if it exceeds threshold
        await self.memory_service.compress_context(conversation_id, user_id, threshold=10)
        
        logger.info("RAG Service completed successfully.")
        
        return {
            "answer": response_text,
            "citations": citations,
            "model_used": self.llm.model_name
        }

    async def stream_answer(self, query: str, conversation_id: int, user_id: int, response_mode: str = "normal", response_length: str = "standard") -> AsyncGenerator[str, None]:
        """
        Executes the RAG pipeline and yields SSE formatted strings.
        """
        logger.info(f"RAG Service streaming starting for query: '{query}'")
        
        # 1. Save user's question
        user_msg = await self.conversation_service.add_message(
            conversation_id=conversation_id, user_id=user_id, role="user", content=query
        )
        
        # Index user message for long-term memory
        await self.memory_service.index_message(user_msg, user_id)
        
        # 2. Get history
        summary, long_term, recent_history = await self.memory_service.get_memory_context(
            conversation_id=conversation_id,
            user_id=user_id,
            query=query,
            session_window=6
        )
        
        # 3. Query Expansion & Source Detection
        try:
            expansion_prompt = f"Extract critical keywords, technical entities, and system names from this query: '{query}'. Return ONLY a space-separated list of 5-8 exact terms to use for a search engine. Include implicit related terms if known."
            keywords = await self.llm.generate_response(expansion_prompt)
            search_query = f"{query} {keywords}"
            logger.info(f"Query expanded from '{query}' to '{search_query}'")
            
            # Detect explicit source mentions
            source_prompt = f"Does this query mention any specific file names, document titles, or sources to search in? Query: '{query}'. If YES, extract ONLY the file names as a comma-separated list. If NO, reply EXACTLY 'NONE'."
            source_response = await self.llm.generate_response(source_prompt)
            
            target_filenames = None
            if source_response and source_response.strip().upper() != "NONE":
                target_filenames = [s.strip() for s in source_response.split(",") if s.strip()]
                logger.info(f"Detected explicit target sources: {target_filenames}")
                
        except Exception:
            search_query = query
            target_filenames = None

        # 4. First Retrieval Pass
        retrieval_res = await self.retriever.retrieve(search_query, top_k=8, user_id=user_id, target_filenames=target_filenames)
        if isinstance(retrieval_res, dict):
            chunks = retrieval_res.get("chunks", [])
            retrieval_scores = retrieval_res.get("retrieval_scores", [])
        else:
            chunks = retrieval_res
            retrieval_scores = []
            
        # 5. Multi-Hop Retrieval & Validation
        is_valid, confidence = self.validator.validate(retrieval_scores, len(chunks))
        
        # Check if query implies routing or decision logic but the context might be missing it
        requires_routing = any(kw in query.lower() for kw in ["route", "determine", "flow", "logic", "how does", "condition"])
        
        if len(chunks) > 0 and (confidence < 0.8 or requires_routing):
            try:
                top_context = " ".join([getattr(c, 'content', '') for c in chunks[:3]])
                hop_prompt = f"Given the query: '{query}' and this partial context: '{top_context[:1500]}'. Are we missing the final routing decision, variable conditions, or flow steps? If YES, reply with exactly 3-5 keywords to search for the missing piece. If NO, reply with exactly 'NONE'."
                hop_response = await self.llm.generate_response(hop_prompt)
                
                if hop_response and hop_response.strip().upper() != "NONE":
                    logger.info(f"Triggering multi-hop retrieval with keywords: {hop_response}")
                    hop_res = await self.retriever.retrieve(f"{query} {hop_response}", top_k=5, user_id=user_id, target_filenames=target_filenames)
                    if isinstance(hop_res, dict):
                        hop_chunks = hop_res.get("chunks", [])
                        existing_ids = set([getattr(c, 'id', -1) for c in chunks])
                        for hc in hop_chunks:
                            hc_id = getattr(hc, 'id', -1)
                            if hc_id not in existing_ids:
                                chunks.append(hc)
                                existing_ids.add(hc_id)
                    
                    # Re-validate
                    is_valid, confidence = self.validator.validate(retrieval_scores, len(chunks))
            except Exception as e:
                logger.error(f"Multi-hop failed: {e}")

        # 6. Fallback Logic for Target Filenames
        fallback_used = False
        if not is_valid and target_filenames:
            logger.info("Filtered retrieval failed. Falling back to general retrieval without filename filters.")
            retrieval_res = await self.retriever.retrieve(search_query, top_k=8, user_id=user_id)
            if isinstance(retrieval_res, dict):
                chunks = retrieval_res.get("chunks", [])
                retrieval_scores = retrieval_res.get("retrieval_scores", [])
            else:
                chunks = retrieval_res
                retrieval_scores = []
                
            is_valid, confidence = self.validator.validate(retrieval_scores, len(chunks))
            if is_valid:
                fallback_used = True

        # Validation before streaming
        if not is_valid:
            fallback = "I could not find reliable information in the knowledge base to answer this completely."
            citations = []
            # Yield citations (empty) then the fallback content and done
            yield f'data: {json.dumps({"type": "citations", "citations": citations, "model": self.llm.model_name})}\n\n'
            yield f'data: {json.dumps({"type": "content", "content": fallback})}\n\n'
            yield f'data: {json.dumps({"type": "done"})}\n\n'
            # Save assistant message
            assistant_msg = await self.conversation_service.add_message(
                conversation_id=conversation_id, user_id=user_id, role="assistant", content=fallback
            )
            await self.memory_service.index_message(assistant_msg, user_id)
            await self.memory_service.compress_context(conversation_id, user_id, threshold=10)
            logger.info(f"RAG Service stream aborted: validation failed (confidence={confidence})")
            return
        
        # 4. Build Context & Citations
        context_string, citations = ContextBuilder.build_context(chunks)
        
        if fallback_used:
            context_string = "SYSTEM INSTRUCTION: The user asked to find the answer in a specific source, but the answer was NOT found in that source. However, it was found in OTHER sources. You MUST start your reply by stating: 'The mentioned source doesn't have this answer, but it is present in this other source:' and then provide the answer.\n\n" + context_string
        
        prompt = PromptBuilder.build(
            query=query,
            context=context_string,
            history=recent_history,
            summary=summary,
            long_term_memory=long_term,
            response_mode=response_mode,
            response_length=response_length
        )
        
        # Yield citations first
        yield f'data: {json.dumps({"type": "citations", "citations": citations, "model": self.llm.model_name})}\n\n'
        
        full_response = ""
        # Yield tokens
        async for chunk in self.llm.generate_response_stream(prompt):
            full_response += chunk
            # Avoid sending raw newlines in SSE data, json encode the chunk
            yield f'data: {json.dumps({"type": "content", "content": chunk})}\n\n'
            
        # Yield done
        yield f'data: {json.dumps({"type": "done"})}\n\n'
        
        # Save response
        assistant_msg = await self.conversation_service.add_message(
            conversation_id=conversation_id, user_id=user_id, role="assistant", content=full_response
        )
        
        # Index assistant response for long-term memory
        await self.memory_service.index_message(assistant_msg, user_id)
        
        # Compress history if it exceeds threshold
        await self.memory_service.compress_context(conversation_id, user_id, threshold=10)
        
        # Generate smart follow-up suggestions
        try:
            suggestion_prompt = PromptBuilder.build_suggestions(query, full_response)
            suggestion_text = await self.llm.generate_response(suggestion_prompt)
            # Parse numbered lines like "1. ...\n2. ...\n3. ..."
            suggestions = []
            for line in suggestion_text.strip().split("\n"):
                line = line.strip()
                if line and len(line) > 3:
                    # Remove leading number + dot/paren
                    cleaned = line
                    for prefix in ["1.", "2.", "3.", "1)", "2)", "3)"]:
                        if cleaned.startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()
                            break
                    if cleaned:
                        suggestions.append(cleaned)
            suggestions = suggestions[:3]
            if suggestions:
                yield f'data: {json.dumps({"type": "suggestions", "suggestions": suggestions})}\n\n'
        except Exception as e:
            logger.error(f"Follow-up suggestion generation failed: {e}")
        
        logger.info("RAG Service stream completed.")

