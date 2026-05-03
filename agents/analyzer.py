"""
Analyzer Agent - Ingests code and context to produce a structured diagnosis.
"""

import json
from typing import Dict, Any, Optional
from shared.base_agent import BaseAgent
from shared.llm_client import LLMClient
from shared.prompts import get_agent_prompt


class AnalyzerAgent(BaseAgent):
    """
    AnalyzerAgent class responsible for ingesting code and context
    and producing a structured diagnosis using an LLM.
    """

    def __init__(self, mode: str = "repair", llm_client: Optional[LLMClient] = None, lokr_service: Any = None):
        """
        Initialize the Analyzer Agent.
        
        Args:
            mode (str): Default operating mode.
            llm_client (LLMClient, optional): Client for LLM communication.
            lokr_service (Any, optional): Service for retrieving code context.
        """
        super().__init__(name="Analyzer")
        self.mode = mode
        self.llm_client = llm_client if llm_client is not None else LLMClient()
        self.lokr_service = lokr_service
    def _extract_json(self, text: str) -> dict:
        """
        Aggressively extract and parse JSON from the LLM response.
        Searches for every occurrence of { and matching } in the text.
        """
        text = text.strip()
        
        # 1. Direct try
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Search for candidates
        brace_indices = [i for i, char in enumerate(text) if char == '{']
        end_brace_indices = [i for i, char in enumerate(text) if char == '}']
        
        for start in brace_indices:
            for end in reversed(end_brace_indices):
                if end > start:
                    candidate = text[start : end + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        continue

        self._log(f"JSON extraction failed for response: {text[:200]}...", level="WARNING")
        return {}

    def run(self, state: Dict[str, Any], llm_client: Any, lokr_service: Any) -> Dict[str, Any]:
        """
        Run the agent's main logic on the given state and return a result dict.
        
        Args:
            state (dict): The full shared orchestration state.
            llm_client: The LLM client to use.
            lokr_service: The Lokr service to use.
            
        Returns:
            dict: Contains 'chain_of_thought', 'contribution', and 'lokr_requests'.
        """
        self._log("Starting analysis...")
        
        # Extract needed context from state
        mode = state.get("mode", self.mode)
        # Prefer the structured analyzer input (with USER BUG REPORT / RELEVANT CODE SNIPPET sections)
        code = state.get("analyzer_input", state.get("original_input", ""))
        skip_lokr = True  # Lokr context is already embedded via the orchestrator's triage phase

        # Fetch additional context from Lokr if available and not skipped
        if self.lokr_service and not skip_lokr:
            try:
                lokr_context = self.lokr_service.get_relevant_context(code, top_k=2)
                if lokr_context:
                    code += f"\n\n### ADDITIONAL LOKR CONTEXT:\n{lokr_context}"
            except Exception as e:
                self._log(f"Lokr context fetch failed: {e}", level="WARNING")

        if llm_client:
            try:
                system_prompt = get_agent_prompt("analyzer", mode)
                
                # Use the code as-is
                user_msg = code
                
                self._log(f"Generating LLM diagnosis for mode: {mode}...")
                response = llm_client.generate(prompt=user_msg, system=system_prompt, temperature=0.2)
                
                if response:
                    parsed = self._extract_json(response)
                    
                    if not parsed and response.strip():
                        self._log("JSON extraction failed, treating raw response as prose diagnosis.", level="INFO")
                        parsed = {
                            "chain_of_thought": [],
                            "contribution": {
                                "diagnosis": response.strip(),
                                "issues": [],
                                "confidence": 0.5,
                                "hypothesis": "Unknown root cause",
                                "evidence_used": []
                            },
                            "lokr_requests": []
                        }

                    if parsed:
                        if "contribution" not in parsed:
                            parsed["contribution"] = {
                                "diagnosis": parsed.pop("diagnosis", "Unknown diagnosis"),
                                "issues": parsed.pop("issues", []),
                                "confidence": parsed.pop("confidence", 0.5),
                                "hypothesis": parsed.pop("hypothesis", "Unknown root cause"),
                                "evidence_used": parsed.pop("evidence_used", [])
                            }
                            if "chain_of_thought" not in parsed:
                                parsed["chain_of_thought"] = []
                            if "lokr_requests" not in parsed:
                                parsed["lokr_requests"] = []

                        contrib = parsed.get("contribution", {})
                        
                        # Ensure required keys are present based on mode
                        if mode == "review":
                            required_keys = ["changes_summary", "files_affected", "change_type"]
                        elif mode == "prevent":
                            required_keys = ["commits_since_deploy", "files_changed", "breaking_changes", "outstanding_todos", "readiness_score", "change_summary"]
                        else:
                            required_keys = ["diagnosis", "issues", "confidence", "hypothesis"]
                            
                        missing_keys = [k for k in required_keys if k not in contrib]
                        if not missing_keys:
                            self._log("Analysis completed successfully via LLM.")
                            return parsed
                        else:
                            self._log(f"LLM response missing required keys in contribution: {', '.join(missing_keys)}. Falling back to stub.", level="WARNING")
                    else:
                        self._log("Empty response or extraction failed, falling back to stub.", level="WARNING")
                else:
                    self._log("Empty response from LLM, falling back to stub.", level="WARNING")
                    
            except Exception as e:
                self._log(f"LLM call failed: {e}. Falling back to stub.", level="ERROR")

        # Stub fallback
        self._log("Using fallback analysis (stub).")
        if mode == "review":
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "changes_summary": f"Code analysis (stub) for mode: {mode}.",
                    "files_affected": ["stub_file.js"],
                    "functions_modified": ["stubFunction"],
                    "change_type": "refactor",
                    "risk_indicators": ["Stub: no real LLM call or LLM failed"]
                },
                "lokr_requests": []
            }
        elif mode == "prevent":
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "commits_since_deploy": 0,
                    "files_changed": ["stub_file.js"],
                    "breaking_changes": ["Stub breaking change"],
                    "outstanding_todos": ["Stub TODO"],
                    "readiness_score": 0.5,
                    "change_summary": f"Prevent analysis (stub) for mode: {mode}."
                },
                "lokr_requests": []
            }
        else:
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "diagnosis": f"Code analysis (stub) for mode: {mode}. Code snippet: {code[:100]}...",
                    "issues": ["Stub: no real LLM call or LLM failed"],
                    "confidence": 0.5,
                    "hypothesis": "Stub hypothesis",
                    "evidence_used": []
                },
                "lokr_requests": []
            }
        self._log("Analysis completed.")
        return result


if __name__ == "__main__":
    # Simple integration test
    print("Running AnalyzerAgent LLM integration test...")
    try:
        # Instantiate LLMClient (assuming Ollama is running)
        test_client = LLMClient()
        agent = AnalyzerAgent(mode="repair", llm_client=test_client)
        
        test_context = {
            "code": "def add(a, b): return a+b",
            "mode": "repair"
        }
        
        result = agent.run(test_context)
        print(f"Result:\n{json.dumps(result, indent=2)}")
        
        if isinstance(result, dict) and "diagnosis" in result:
            print("\nAnalyzerAgent LLM integration test passed.")
        else:
            print("\nTest failed: Result missing diagnosis.")
            
    except Exception as e:
        print(f"\nTest failed with error: {e}")
