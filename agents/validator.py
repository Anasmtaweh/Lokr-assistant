"""
Validator Agent - Validates results and closes the loop.
"""

import json
from typing import Dict, Any, Optional
from shared.base_agent import BaseAgent
from shared.llm_client import LLMClient
from shared.prompts import get_agent_prompt


class ValidatorAgent(BaseAgent):
    """
    ValidatorAgent class responsible for validating the final results
    of the pipeline using an LLM.
    """

    def __init__(self, mode: str = "repair", llm_client: Optional[LLMClient] = None, lokr_service: Any = None):
        """
        Initialize the Validator Agent.
        
        Args:
            mode (str): Default operating mode.
            llm_client (LLMClient, optional): Client for LLM communication.
            lokr_service (Any, optional): Service for retrieving code context.
        """
        super().__init__(name="Validator")
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
        self._log("Starting validation...")
        
        mode = state.get("mode", self.mode)
        
        action_result = state["actions"][-1] if state.get("actions") else {}
        safety_result = state["safety_reports"][-1] if state.get("safety_reports") else {}
        original_code = state.get("original_input", "")
        
        if llm_client:
            system_prompt = get_agent_prompt("validator", mode)
            
            context_for_llm = {
                "action_result": action_result,
                "safety_result": safety_result,
                "original_code": original_code,
                "mode": mode
            }
            user_msg = f"PIPELINE CONTEXT FOR VALIDATION:\n{json.dumps(context_for_llm, indent=2)}\n"

            self._log(f"Generating LLM validation for mode: {mode}...")
            response = llm_client.generate(prompt=user_msg, system=system_prompt, temperature=0.1)
            
            if not response or not response.strip():
                raise ValueError(f"[Validator] LLM returned empty response for mode '{mode}'.")
            
            parsed = self._extract_json(response)
            
            if not parsed:
                raise ValueError(
                    f"[Validator] JSON extraction failed. LLM returned non-JSON: "
                    f"{response[:200]}..."
                )

            # Normalize: wrap flat responses into contribution structure
            if "contribution" not in parsed:
                parsed["contribution"] = {
                    "status": parsed.pop("status", "success" if parsed.get("safe", True) else "failure"),
                    "feedback": parsed.pop("feedback", parsed.get("response", parsed.get("summary", "Validation completed.")))
                }
            if "chain_of_thought" not in parsed:
                parsed["chain_of_thought"] = []
            if "lokr_requests" not in parsed:
                parsed["lokr_requests"] = []
                    
            contrib = parsed.get("contribution", {})
            
            # Mode-specific required fields
            if mode == "review":
                required_keys = ["review_checklist", "verification_steps", "status"]
            elif mode == "prevent":
                required_keys = ["pre_deploy_checklist", "post_deploy_checklist", "rollback_steps", "status", "feedback"]
            else:
                required_keys = ["status", "feedback"]
                
            missing_keys = [k for k in required_keys if k not in contrib]
            if missing_keys:
                raise ValueError(
                    f"[Validator] Mode '{mode}' requires fields {missing_keys} in contribution. "
                    f"Got keys: {list(contrib.keys())}. Response: {response[:200]}..."
                )
            
            self._log("Validation completed successfully via LLM.")
            return parsed
        else:
            raise ValueError("[Validator] No LLM client provided.")
        
        self._log("Validation completed.")


if __name__ == "__main__":
    print("Running ValidatorAgent LLM integration test...")
    try:
        test_client = LLMClient()
        agent = ValidatorAgent(mode="repair", llm_client=test_client)
        test_context = {
            "action_result": {"patch": "fixed bug"},
            "safety_result": {"safe": True},
            "original_code": "def bug(): pass",
            "mode": "repair"
        }
        result = agent.run(test_context)
        print(f"Result:\n{json.dumps(result, indent=2)}")
        if isinstance(result, dict) and "status" in result:
            print("\nValidatorAgent LLM integration test passed.")
        else:
            print("\nTest failed.")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
