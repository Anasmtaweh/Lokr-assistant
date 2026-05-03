import sys
import os
import json

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modes.repair.runner import run_repair
from shared.llm_client import LLMClient
from lokr.service import LokrService

def test_repair_integration():
    print("\n--- Testing Repair Pipeline Integration ---")
    
    llm = LLMClient()
    
    # Attempt to load LokrService if paths are set
    lokr = None
    project_path = os.environ.get("TEST_PROJECT_PATH")
    lokr_path = os.environ.get("LOKR_PATH")
    
    if project_path and lokr_path:
        print(f"Initializing LokrService for integration test...")
        lokr = LokrService(project_path, lokr_path)
        if not lokr.initialized:
            lokr = None

    code = "def insecure_function(data): exec(data)"
    print(f"Input Code: {code}")
    
    result = run_repair(code, llm_client=llm, lokr_service=lokr)
    
    print(f"\nFinal Status: {result['status']}")
    print(f"Diagnosis: {result['analysis'].get('diagnosis')}")
    print(f"Action Type: {result['action'].get('action_type')}")
    if 'patch' in result['action']:
        print(f"Patch: {result['action'].get('patch')}")
    print(f"Safety: {'Safe' if result['safety'].get('safe') else 'Unsafe'} (Risk: {result['safety'].get('risk_score')})")
    print(f"Feedback: {result['validation'].get('feedback')}")

if __name__ == "__main__":
    test_repair_integration()
