"""
Tests for the LokrClient stub.
"""

import sys
import os

# Add the project root to the python path to allow importing the lokr package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lokr.client import LokrClient

def test_stub():
    """
    Test the behavior of the LokrClient stub.
    
    Instantiates the client, calls analyze with dummy inputs, and verifies
    the structure and types of the returned response.
    """
    client = LokrClient()
    code_snippet = "def add(x, y): return x + y"
    question = "What are the parameters?"
    
    result = client.analyze(code_snippet, question)
    
    print("Analyze Result:")
    print(result)
    
    assert isinstance(result, dict), "Result should be a dictionary"
    
    required_keys = ["summary", "entities", "relations", "confidence"]
    for key in required_keys:
        assert key in result, f"Result is missing key: '{key}'"
        
    assert isinstance(result["confidence"], float), "Confidence key should be of type float"

if __name__ == "__main__":
    try:
        test_stub()
        print("Lokr client stub test passed.")
    except AssertionError as e:
        print(f"AssertionError: {e}")
