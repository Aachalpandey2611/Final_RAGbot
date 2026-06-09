"""Minimal stub of google.generativeai for local/test runs.
This stub provides a `configure` function and a `GenerativeModel` class
with an async `generate_content_async` method that returns a simple object
with a `text` attribute. It is NOT a replacement for the real SDK.
"""
from types import SimpleNamespace

_api_key = None

def configure(api_key: str):
    global _api_key
    _api_key = api_key

class GenerativeModel:
    def __init__(self, model_name: str):
        self._model_name = model_name

    async def generate_content_async(self, prompt: str, stream: bool = False):
        # Return a simple object mimicking the real SDK's response
        class Resp:
            def __init__(self, text):
                self.text = text

            def __aiter__(self):
                # allow async iteration over streaming responses
                async def _gen():
                    yield self
                return _gen()

        # simple echo response for testing
        return Resp(f"[stubbed response for prompt: {prompt[:120]}]")
