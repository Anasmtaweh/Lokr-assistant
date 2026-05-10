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

        import re
        # Find the first { and last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            json_str = text[first_brace:last_brace+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try sanitizing unescaped newlines
                try:
                    sanitized = re.sub(r'(?<!\\)\n', '\\\\n', json_str)
                    return json.loads(sanitized)
                except:
                    pass
        
        self._log(f"JSON extraction failed for response: {text[:200]}...", level="WARNING")
        self._last_failed_text = text
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
        
        # Allow the Analyzer to autonomously request Lokr context via lokr_requests.
        # The orchestrator's loop-back logic (lines 534-556) intercepts lokr_requests,
        # resolves them via lokr_service.resolve_request(), and feeds the results back.
        skip_lokr = False

        # Optionally fetch broad Lokr context upfront (lightweight — top 2 results)
        if self.lokr_service and not skip_lokr:
            try:
                # Use the user's specific task as the query, rather than the entire code blob
                search_query = state.get("task", "") or code[:200]
                lokr_context = self.lokr_service.get_relevant_context(search_query, top_k=2)
                if lokr_context:
                    # Truncate the context if it's absurdly large to prevent 400 Bad Request
                    if len(lokr_context) > 15000:
                        lokr_context = lokr_context[:15000] + "\n...[Context truncated due to size limitations]..."
                    code += f"\n\n### ADDITIONAL LOKR CONTEXT:\n{lokr_context}"
            except Exception as e:
                self._log(f"Lokr context fetch failed: {e}", level="WARNING")

        if llm_client:
            system_prompt = get_agent_prompt("analyzer", mode)
            user_msg = code
            
            self._log(f"Generating LLM diagnosis for mode: {mode}...")
            response = llm_client.generate(prompt=user_msg, system=system_prompt, temperature=0.2)
            
            if not response or not response.strip():
                raise ValueError(f"[Analyzer] LLM returned empty response for mode '{mode}'.")
            
            parsed = self._extract_json(response)
            
            if not parsed:
                raise ValueError(
                    f"[Analyzer] JSON extraction failed. LLM returned non-JSON: "
                    f"{response[:200]}..."
                )

            # Normalize: wrap flat responses into contribution structure
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
            
            # Mode-specific required fields
            if mode == "review":
                required_keys = ["changes_summary", "files_affected", "change_type"]
            elif mode == "prevent":
                required_keys = ["commits_since_deploy", "files_changed", "findings", "execution_trace", "readiness_score", "change_summary"]
            else:
                required_keys = ["findings", "execution_trace", "confidence", "hypothesis"]
                
            missing_keys = [k for k in required_keys if k not in contrib]
            if missing_keys:
                raise ValueError(
                    f"[Analyzer] Mode '{mode}' requires fields {missing_keys} in contribution. "
                    f"Got keys: {list(contrib.keys())}. Response: {response[:200]}..."
                )
            
            self._log("Analysis completed successfully via LLM.")
            return parsed
        else:
            raise ValueError("[Analyzer] No LLM client provided.")


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
