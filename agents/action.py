"""
Action Agent - Takes action based on diagnosis.
"""

import json
from typing import Dict, Any, Optional
from shared.base_agent import BaseAgent
from shared.llm_client import LLMClient
from shared.prompts import get_agent_prompt


class ActionAgent(BaseAgent):
    """
    ActionAgent class responsible for generating specific outcomes (patches, 
    comments, or checks) based on a diagnosis, using an LLM.
    """

    def __init__(self, mode: str = "repair", llm_client: Optional[LLMClient] = None, lokr_service: Any = None):
        """
        Initialize the Action Agent.
        
        Args:
            mode (str): Default operating mode.
            llm_client (LLMClient, optional): Client for LLM communication.
            lokr_service (Any, optional): Service for retrieving code context.
        """
        super().__init__(name="Action")
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
        self._log("Starting action generation...")
        
        mode = state.get("mode", self.mode)
        
        # Get diagnosis from the latest hypothesis
        diagnosis = ""
        if state.get("hypotheses"):
            latest_hypothesis = state["hypotheses"][-1]
            if "contribution" in latest_hypothesis:
                diagnosis = latest_hypothesis["contribution"].get("diagnosis", "")
            else:
                diagnosis = latest_hypothesis.get("diagnosis", "")

        if llm_client:
            try:
                system_prompt = get_agent_prompt("action", mode)
                user_msg = f"DIAGNOSIS TO ACT UPON:\n{diagnosis}\n"
                
                # Include original code if available in state
                if "original_input" in state:
                    user_msg += f"\nORIGINAL CODE:\n{state['original_input']}\n"
                    
                # Include safety warnings if re-running
                if state.get("needs_revision") and state.get("safety_reports"):
                    latest_safety = state["safety_reports"][-1]
                    if "contribution" in latest_safety:
                        warnings = latest_safety["contribution"].get("warnings", [])
                    else:
                        warnings = latest_safety.get("warnings", [])
                    user_msg += f"\nSAFETY WARNINGS TO ADDRESS:\n{warnings}\n"

                self._log(f"Generating LLM action for mode: {mode}...")
                response = llm_client.generate(prompt=user_msg, system=system_prompt, temperature=0.2)
                
                if response:
                    parsed = self._extract_json(response)
                    if parsed:
                        if "contribution" not in parsed:
                            parsed["contribution"] = {
                                "action_type": parsed.pop("action_type", mode),
                                "patch": parsed.pop("patch", ""),
                                "review_comments": parsed.pop("review_comments", []),
                                "deployment_checks": parsed.pop("deployment_checks", [])
                            }
                            if "chain_of_thought" not in parsed:
                                parsed["chain_of_thought"] = []
                            if "lokr_requests" not in parsed:
                                parsed["lokr_requests"] = []
                                
                        contrib = parsed.get("contribution", {})
                        
                        # Define required keys based on mode
                        required_keys = []
                        if mode == "repair":
                            required_keys = ["action_type", "patch"]
                        elif mode == "review":
                            required_keys = ["observations", "recommendations", "suggestion_priority"]
                        elif mode == "prevent":
                            required_keys = ["blockers", "warnings", "recommendations"]

                        missing_keys = [k for k in required_keys if k not in contrib]
                        if not missing_keys:
                            self._log("Action generation completed successfully via LLM.")
                            return parsed
                        else:
                            self._log("LLM response missing required keys in contribution, falling back to stub.", level="WARNING")
                    else:
                        # Prose fallback
                        self._log("JSON extraction failed. Returning error dict.", level="ERROR")
                        return {
                            "chain_of_thought": [],
                            "contribution": {
                                "status": "failed_generation",
                                "action_type": mode,
                                "patch": "Unable to generate patch; model did not return valid JSON.",
                                "review_comments": [],
                                "deployment_checks": []
                            },
                            "lokr_requests": []
                        }
                else:
                    self._log("Empty response from LLM, falling back to stub.", level="WARNING")
            except Exception as e:
                self._log(f"LLM call failed: {e}. Falling back to stub.", level="ERROR")

        # Stub fallback
        self._log("Using fallback action generation (stub).")
        if mode == "review":
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "status": "failed_generation",
                    "observations": ["Stub observation for mode: review"],
                    "recommendations": ["Stub recommendation"],
                    "suggestion_priority": "Low"
                },
                "lokr_requests": []
            }
        elif mode == "prevent":
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "status": "failed_generation",
                    "blockers": ["Stub blocker"],
                    "warnings": ["Stub warning"],
                    "recommendations": ["Stub recommendation"]
                },
                "lokr_requests": []
            }
        else:
            result = {
                "chain_of_thought": [],
                "contribution": {"status": "failed_generation", "action_type": mode},
                "lokr_requests": []
            }
            if mode == "repair":
                result["contribution"]["patch"] = "/* stub patch */"
                
        return result


if __name__ == "__main__":
    print("Running ActionAgent LLM integration test...")
    try:
        test_client = LLMClient()
        agent = ActionAgent(mode="repair", llm_client=test_client)
        test_context = {"diagnosis": "The code lacks error handling.", "mode": "repair"}
        result = agent.run(test_context)
        print(f"Result:\n{json.dumps(result, indent=2)}")
        if isinstance(result, dict) and "action_type" in result:
            print("\nActionAgent LLM integration test passed.")
        else:
            print("\nTest failed.")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
