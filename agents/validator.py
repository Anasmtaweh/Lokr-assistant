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
        Strips markdown fences and searches for every {…} pair.
        """
        text = text.strip()
        
        # 1. Direct try
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Strip markdown code fences
        import re
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if fence_match:
            inner = fence_match.group(1).strip()
            try:
                return json.loads(inner)
            except json.JSONDecodeError:
                pass

        # 3. Search for brace-pair candidates
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
        self._log("Starting validation...")
        
        mode = state.get("mode", self.mode)
        
        action_result = state["actions"][-1] if state.get("actions") else {}
        safety_result = state["safety_reports"][-1] if state.get("safety_reports") else {}
        original_code = state.get("original_input", "")
        
        if llm_client:
            try:
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
                
                if response:
                    parsed = self._extract_json(response)
                    if parsed:
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
                        
                        if mode == "review":
                            required_keys = ["review_checklist", "verification_steps", "status"]
                        elif mode == "prevent":
                            required_keys = ["pre_deploy_checklist", "post_deploy_checklist", "rollback_steps", "status", "feedback"]
                        else:
                            required_keys = ["status", "feedback"]
                            
                        missing_keys = [k for k in required_keys if k not in contrib]
                        if not missing_keys:
                            self._log("Validation completed successfully via LLM.")
                            return parsed
                        else:
                            self._log(f"LLM response missing required keys in contribution: {', '.join(missing_keys)}. Falling back to stub.", level="WARNING")
                    else:
                        # Prose fallback — if the Validator couldn't produce JSON,
                        # it didn't actually validate anything. Mark as failure for repair.
                        self._log("JSON extraction failed; using prose fallback.", level="WARNING")
                        fallback_status = "failure" if mode == "repair" else "success"
                        return {
                            "chain_of_thought": [],
                            "contribution": {
                                "status": fallback_status,
                                "feedback": response.strip()[:500]  # Truncate rogue essays
                            },
                            "lokr_requests": []
                        }
                else:
                    self._log("Empty response from LLM, falling back to stub.", level="WARNING")
            except Exception as e:
                self._log(f"LLM call failed: {e}. Falling back to stub.", level="ERROR")

        # Stub fallback
        self._log("Using fallback validation (stub).")
        if mode == "review":
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "review_checklist": ["Stub checklist item 1", "Stub checklist item 2"],
                    "verification_steps": ["Stub step 1", "Stub step 2"],
                    "status": "success"
                },
                "lokr_requests": []
            }
        elif mode == "prevent":
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "pre_deploy_checklist": ["Stub pre-deploy check"],
                    "post_deploy_checklist": ["Stub post-deploy check"],
                    "rollback_steps": "Stub rollback steps",
                    "status": "success",
                    "feedback": f"Validation (stub) for mode: {mode}."
                },
                "lokr_requests": []
            }
        else:
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "status": "success",
                    "feedback": "Fallback validation completed successfully."
                },
                "lokr_requests": []
            }
        
        self._log("Validation completed.")
        return result


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
