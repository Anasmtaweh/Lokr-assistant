import sys
import os
import json

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modes.prevent.runner import run_prevent
from shared.llm_client import LLMClient
from lokr.service import LokrService

def test_prevent_integration():
    print("\n--- Testing Prevent Pipeline Integration ---")
    
    llm = LLMClient()
    
    # Attempt to load LokrService if paths are set
    lokr = None
    project_path = os.environ.get("TEST_PROJECT_PATH")
    lokr_path = os.environ.get("LOKR_PATH")
    
    if project_path and lokr_path:
        lokr = LokrService(project_path, lokr_path)
        if not lokr.initialized:
            lokr = None

    code = "docker-compose.yml with root user and no resource limits"
    print(f"Input Config: {code}")
    
    result = run_prevent(code, llm_client=llm, lokr_service=lokr)
    
    print(f"\nFinal Status: {result['status']}")
    print(f"Diagnosis: {result['analysis'].get('diagnosis')}")
    if 'deployment_checks' in result['action']:
        print(f"Deployment Checks: {result['action'].get('deployment_checks')}")
    print(f"Safety: {'Safe' if result['safety'].get('safe') else 'Unsafe'}")

if __name__ == "__main__":
    test_prevent_integration()
