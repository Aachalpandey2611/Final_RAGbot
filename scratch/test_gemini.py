import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
print("Key prefix:", key[:8] if key else None)

genai.configure(api_key=key)

print("Listing models:")
try:
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print("Error listing models:", str(e))
