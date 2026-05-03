"""
Test file for LokrService.
"""

import sys
import os
import argparse
import json

# Ensure the root directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lokr.service import LokrService

def test_lokr_service(project_path: str):
    """
    Test the initialization and methods of LokrService.
    """
    print(f"Testing LokrService with project path: {project_path}")
    service = LokrService(project_path=project_path)
    
    assert service.initialized == True, "LokrService failed to initialize."
    
    print("\nProject Summary:")
    summary = service.get_project_summary()
    print(json.dumps(summary, indent=2))
    
    print("\nSearch for 'authentication':")
    search_results = service.search_code("authentication", top_k=3)
    if search_results:
        first_result = search_results[0]
        print(f"First result keys: {list(first_result.keys())}")
        print(f"First result node_id: {first_result.get('node_id')}")
    else:
        print("No search results found.")
        
    print("\nRelevant Context for 'authentication':")
    context = service.get_relevant_context("authentication", top_k=3)
    print(context[:200] + ("..." if len(context) > 200 else ""))
    
    print("\nFunction Dependencies for 'login':")
    deps = service.get_function_dependencies("login")
    if "error" not in deps:
        print(f"Function: {deps.get('function_name')} (ID: {deps.get('node_id')})")
        print(f"Callers count: {len(deps.get('callers', []))}")
        print(f"Callees count: {len(deps.get('callees', []))}")
    else:
        print(f"Dependency error: {deps.get('error')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test LokrService")
    parser.add_argument(
        "--project-path", 
        type=str, 
        default=os.environ.get("TEST_PROJECT_PATH", "."),
        help="Path to the project to test against."
    )
    
    args = parser.parse_args()
    
    try:
        test_lokr_service(args.project_path)
        print("\nLokr service test passed.")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
