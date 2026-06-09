from typing import List, Optional
from app.models.conversation import Message

class PromptBuilder:
    """
    Constructs the final prompt injected into the LLM.
    """
    
    SYSTEM_PROMPT = """You are a helpful and intelligent AI assistant. 
You are provided with a Conversation History and a set of Retrieved Context Sources.
Use the context to answer the user's question accurately. 
If the context does not contain the answer, say "I don't know based on the provided context." 
Always cite your sources by referencing the [Source X] marker in your response if you use information from it.

Never answer with generic statements if specific logic or conditions exist in the retrieved context. Be exact and precise.

IMPORTANT - Multilingual Rule: Look ONLY at the LATEST User Question to determine the language and script. Do NOT let previous chat history change your language.
- If the latest question is in Hindi using English letters (Hinglish/Roman Hindi), you MUST reply in Hinglish using English letters. ABSOLUTELY DO NOT use the Devanagari script (हिंदी) under any circumstances.
- If the latest question is in pure English, you MUST reply in pure English.
- Keep all technical terms (like 'API', 'consumer system', 'timeout', etc.) in pure English.
"""

    MODE_INSTRUCTIONS = {
        "simple": "\n--- RESPONSE STYLE ---\nRespond in simple, everyday language. Avoid jargon and technical terms. Use short sentences and bullet points. Explain concepts as if talking to someone with no technical background.\n",
        "normal": "",
        "technical": "\n--- RESPONSE STYLE ---\nProvide a deep, technically detailed response. Use precise terminology, include implementation specifics, data structures, algorithms, code patterns, and system architecture details where relevant. Target an audience of experienced software developers and engineers.\n",
    }

    LENGTH_INSTRUCTIONS = {
        "quick": "\n--- ANSWER LENGTH ---\nAnswer briefly and directly in 3 to 8 lines.\nProvide only essential information. DO NOT use long structured sections, headers, or detailed flow steps. Use bullet points if it helps clarity.\n",
        "standard": "\n--- ANSWER LENGTH ---\nProvide a balanced answer with moderate detail. Use bullet points if needed for readability.\n",
        "detailed": "\n--- ANSWER LENGTH ---\nProvide a comprehensive answer with explanations, examples, reasoning, and structured sections.\nIf answering about process flows or architecture, use explicit sections like 'Summary', 'Decision Logic', and 'Flow Steps'.\n",
    }

    @classmethod
    def build(
        cls, 
        query: str, 
        context: str, 
        history: List[Message], 
        summary: Optional[str] = None, 
        long_term_memory: Optional[List[dict]] = None,
        response_mode: Optional[str] = None,
        response_length: Optional[str] = None
    ) -> str:
        """
        Combines system prompt, chat history, context, and the new query.
        """
        prompt_parts = [cls.SYSTEM_PROMPT]

        # Inject response mode instruction
        mode = (response_mode or "normal").lower()
        mode_instruction = cls.MODE_INSTRUCTIONS.get(mode, "")
        if mode_instruction:
            prompt_parts.append(mode_instruction)

        # Inject answer length instruction
        length = (response_length or "standard").lower()
        length_instruction = cls.LENGTH_INSTRUCTIONS.get(length, "")
        if length_instruction:
            prompt_parts.append(length_instruction)
        
        # Add summary if exists
        if summary:
            prompt_parts.append("\n--- CONVERSATION SUMMARY (PAST CONTEXT) ---")
            prompt_parts.append(summary)
            prompt_parts.append("------------------------------------------\n")

        # Add long-term memory if exists
        if long_term_memory:
            prompt_parts.append("\n--- RELEVANT PAST CONVERSATIONS ---")
            for msg in long_term_memory:
                role = "User" if msg["role"] == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")
            prompt_parts.append("------------------------------------\n")
        
        # Add context
        prompt_parts.append("--- RETRIEVED CONTEXT ---")
        prompt_parts.append(context)
        prompt_parts.append("--------------------------\n")
        
        # Add history
        if history:
            prompt_parts.append("--- CONVERSATION HISTORY (RECENT) ---")
            for msg in history:
                role = "User" if msg.role == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg.content}")
            prompt_parts.append("-------------------------------------\n")
            
        # Add latest query
        prompt_parts.append(f"User Question: {query}")
        prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)

    @classmethod
    def build_suggestions(cls, query: str, answer: str) -> str:
        """
        Builds a prompt to generate 3 smart follow-up questions.
        """
        return f"""Based on this question and answer, generate exactly 3 short follow-up questions the user might want to ask next.
The follow-up questions should be specific, relevant, and help the user explore the topic deeper.

CRITICAL LANGUAGE RULE: Look ONLY at the "Original Question" below to determine the language and script for your output.
- If the Original Question is in Hindi using English letters (Hinglish), you MUST output the follow-ups in Hinglish using English letters. NEVER use Devanagari script.
- If the Original Question is in pure English, you MUST output the follow-ups in pure English.

Original Question: {query}
Answer Summary: {answer[:500]}

Return ONLY the 3 questions, one per line, numbered 1. 2. 3. Do not add any other text."""
