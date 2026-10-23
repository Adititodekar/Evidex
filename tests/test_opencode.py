import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from eval.official_eval import OpenCodeClient

def test_opencode_connection():
    api_key = os.getenv("OPENCODE_API_KEY")
    assert api_key, "OPENCODE_API_KEY is not set in .env!"
    
    print(f"Testing OpenCode API with key prefix: {api_key[:12]}...")
    client = OpenCodeClient(api_key=api_key)
    res = client.call_structured(
        system_prompt="You are a helpful assistant. Respond strictly with JSON.",
        user_prompt='Respond with JSON: {"status": "ok", "message": "connection successful"}'
    )
    print("OpenCode API returned:", res)
    assert isinstance(res, dict), "Expected dict response"
    print("OpenCode connection TEST PASSED!")

if __name__ == "__main__":
    test_opencode_connection()
