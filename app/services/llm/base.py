class LLMProvider:
    """
    Abstract interface for Large Language Models used in RAG.
    """
    
    @property
    def model_name(self) -> str:
        """Returns the name of the LLM model being used."""
        raise NotImplementedError()
        
    async def generate_response(self, prompt: str) -> str:
        """
        Generates a text response given a fully constructed prompt.
        
        Args:
            prompt (str): The final prompt including context and user query.
            
        Returns:
            str: The generated text from the LLM.
        """
        raise NotImplementedError()

    from typing import AsyncGenerator
    async def generate_response_stream(self, prompt: str) -> 'AsyncGenerator[str, None]':
        """
        Generates a streamed text response given a fully constructed prompt.
        
        Args:
            prompt (str): The final prompt including context and user query.
            
        Yields:
            str: Chunks of the generated text from the LLM.
        """
        raise NotImplementedError()
        yield "" # Type hinting satisfying
