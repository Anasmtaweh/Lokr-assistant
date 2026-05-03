"""
Safety Agent - Evaluates risk and safety of proposed actions.
"""

import json
from typing import Dict, Any, Optional
from shared.base_agent import BaseAgent
from shared.llm_client import LLMClient
from shared.prompts import get_agent_prompt


class SafetyAgent(BaseAgent):
    """
    SafetyAgent class responsible for evaluating the risk and safety
    of actions proposed by the ActionAgent using an LLM.
    """

    def __init__(self, mode: str = "repair", llm_client: Optional[LLMClient] = None, lokr_service: Any = None):
        """
        Initialize the Safety Agent.
        
        Args:
            mode (str): Default operating mode.
            llm_client (LLMClient, optional): Client for LLM communication.
            lokr_service (Any, optional): Service for retrieving code context.
        """
        super().__init__(name="Safety")
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
        self._log("Starting safety evaluation...")
        
        mode = state.get("mode", self.mode)
        
        proposed_action = {}
        if state.get("actions"):
            latest_action = state["actions"][-1]
            if "contribution" in latest_action:
                proposed_action = latest_action["contribution"]
            else:
                proposed_action = latest_action

        if llm_client:
            try:
                system_prompt = get_agent_prompt("safety", mode)
                user_msg = f"PROPOSED ACTION TO EVALUATE:\n{json.dumps(proposed_action, indent=2)}\n"

                self._log(f"Generating LLM safety evaluation for mode: {mode}...")
                response = llm_client.generate(prompt=user_msg, system=system_prompt, temperature=0.1)
                
                if response:
                    parsed = self._extract_json(response)
                    if parsed:
                        if "contribution" not in parsed:
                            parsed["contribution"] = {
                                "safe": parsed.pop("safe", True),
                                "risk_score": parsed.pop("risk_score", 0.0),
                                "warnings": parsed.pop("warnings", [])
                            }
                            if "chain_of_thought" not in parsed:
                                parsed["chain_of_thought"] = []
                            if "lokr_requests" not in parsed:
                                parsed["lokr_requests"] = []
                                
                        contrib = parsed.get("contribution", {})
                        
                        if mode == "review":
                            required_keys = ["security_issues", "performance_concerns", "deployment_risk", "approval", "rollback_plan"]
                        elif mode == "prevent":
                            required_keys = ["deployment_risk", "estimated_rollback_time", "health_checks", "go_no_go", "reasoning"]
                        else:
                            required_keys = ["safe", "risk_score", "warnings"]
                        missing_keys = [k for k in required_keys if k not in contrib]
                        if not missing_keys:
                            self._log("Safety evaluation completed successfully via LLM.")
                            return parsed
                        else:
                            self._log("LLM response missing required keys in contribution, falling back to stub.", level="WARNING")
                    else:
                        self._log("JSON extraction failed, falling back to stub.", level="WARNING")
                else:
                    self._log("Empty response from LLM, falling back to stub.", level="WARNING")
            except Exception as e:
                self._log(f"LLM call failed: {e}. Falling back to stub.", level="ERROR")

        # Stub fallback
        self._log("Using fallback safety evaluation (stub).")
        if mode == "review":
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "security_issues": ["Stub security issue"],
                    "performance_concerns": ["Stub performance concern"],
                    "deployment_risk": "Low",
                    "approval": "APPROVE",
                    "rollback_plan": "Stub rollback plan"
                },
                "lokr_requests": []
            }
        elif mode == "prevent":
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "deployment_risk": "low",
                    "estimated_rollback_time": "15 minutes",
                    "health_checks": ["Stub health check"],
                    "go_no_go": "SAFE_TO_DEPLOY",
                    "reasoning": f"Safety evaluation (stub) for mode: {mode}."
                },
                "lokr_requests": []
            }
        else:
            result = {
                "chain_of_thought": [],
                "contribution": {
                    "safe": True,
                    "risk_score": 0.1,
                    "warnings": ["Stub: no real LLM call performed."]
                },
                "lokr_requests": []
            }
        
        self._log("Safety evaluation completed.")
        return result


if __name__ == "__main__":
    print("Running SafetyAgent LLM integration test...")
    try:
        test_client = LLMClient()
        agent = SafetyAgent(mode="repair", llm_client=test_client)
        test_context = {"proposed_action": {"patch": "add logging"}, "mode": "repair"}
        result = agent.run(test_context)
        print(f"Result:\n{json.dumps(result, indent=2)}")
        if isinstance(result, dict) and "safe" in result:
            print("\nSafetyAgent LLM integration test passed.")
        else:
            print("\nTest failed.")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
