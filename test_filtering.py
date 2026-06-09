import asyncio
import json
import httpx

async def test_chat(query: str):
    print(f"\n=========================================")
    print(f"QUERY: {query}")
    print(f"=========================================")
    
    # 1. Start conversation
    async with httpx.AsyncClient() as client:
        # Assuming you have a way to authenticate or bypass it for local testing
        # For this test, I will just hit the endpoint if there's an API route without auth
        pass

if __name__ == "__main__":
    pass
