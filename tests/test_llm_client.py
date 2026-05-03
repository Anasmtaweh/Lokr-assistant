"""
Smoke test for LLMClient.
"""

import sys
import os

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.llm_client import LLMClient


def test_llm_client():
    """
    Test the LLMClient generate method.
    """
    print("Initializing LLMClient...")
    client = LLMClient()
    
    prompt = "Say 'hello world' in one short line."
    print(f"Sending prompt: {prompt}")
    
    response = client.generate(prompt)
    
    print(f"Response from Ollama:\n{response}")
    
    assert isinstance(response, str), "Response must be a string."
    assert len(response.strip()) > 0, "Response must not be empty."


if __name__ == "__main__":
    try:
        test_llm_client()
        print("\nLLM client test passed.")
    except Exception as e:
        print(f"\nLLM client test failed: {e}")
        sys.exit(1)
