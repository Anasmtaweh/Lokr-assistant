import sys
import os
import json

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modes.review.runner import run_review
from shared.llm_client import LLMClient
from lokr.service import LokrService

def test_review_integration():
    print("\n--- Testing Review Pipeline Integration ---")
    
    llm = LLMClient()
    
    # Attempt to load LokrService if paths are set
    lokr = None
    project_path = os.environ.get("TEST_PROJECT_PATH")
    lokr_path = os.environ.get("LOKR_PATH")
    
    if project_path and lokr_path:
        lokr = LokrService(project_path, lokr_path)
        if not lokr.initialized:
            lokr = None

    code_diff = """
--- a/auth.py
+++ b/auth.py
@@ -10,5 +10,5 @@
 def login(user, pwd):
-    if user == 'admin' and pwd == '1234':
+    if user == 'admin' and check_password_hash(pwd):
         return True
"""
    print(f"Input Diff: {code_diff}")
    
    result = run_review(code_diff, llm_client=llm, lokr_service=lokr)
    
    print(f"\nFinal Status: {result['status']}")
    print(f"Diagnosis: {result['analysis'].get('diagnosis')}")
    if 'review_comments' in result['action']:
        print(f"Review Comments: {result['action'].get('review_comments')}")
    print(f"Safety: {'Safe' if result['safety'].get('safe') else 'Unsafe'}")

if __name__ == "__main__":
    test_review_integration()
