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

        import re
        # Find the first { and last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            json_str = text[first_brace:last_brace+1]
            try:
                # Try standard load
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try sanitizing unescaped newlines and common LLM artifacts
                try:
                    # Replace literal newlines inside strings with \n
                    sanitized = re.sub(r'(?<!\\)\n', '\\\\n', json_str)
                    return json.loads(sanitized)
                except:
                    # Attempt a more aggressive regex-based extraction of key fields if all else fails
                    self._log("Aggressive regex extraction fallback for malformed JSON.", level="DEBUG")
                    result = {}
                    for key in ["safe", "risk_score", "approval", "go_no_go", "reasoning"]:
                        match = re.search(f'"{key}"\\s*:\\s*("(.*?)"|(\\w+))', json_str, re.DOTALL)
                        if match:
                            val = match.group(2) if match.group(2) else match.group(3)
                            if val == "true": result[key] = True
                            elif val == "false": result[key] = False
                            elif val and val.replace(".", "").isdigit(): result[key] = float(val)
                            else: result[key] = val
                    if result: return result
        
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
        self._log("Starting safety evaluation...")
        
        mode = state.get("mode", self.mode)
        
        proposed_action = {}
        if state.get("actions"):
            latest_action = state["actions"][-1]
            if "contribution" in latest_action:
                proposed_action = latest_action["contribution"]
            else:
                proposed_action = latest_action

        # Get the original code and diagnosis for cross-file consistency checking
        original_code = state.get("original_input", "")
        diagnosis_issues = []
        diagnosis_text = ""
        if state.get("hypotheses"):
            latest_hyp = state["hypotheses"][-1]
            contrib = latest_hyp.get("contribution", latest_hyp)
            diagnosis_text = contrib.get("diagnosis", "")
            diagnosis_issues = contrib.get("issues", [])

        if llm_client:
            system_prompt = get_agent_prompt("safety", mode)
            user_msg = f"PROPOSED ACTION TO EVALUATE:\n{json.dumps(proposed_action, indent=2)}\n"
            
            # Include the original code context so the Safety Agent can verify
            # cross-file consistency (e.g., middleware role checks vs route requirements)
            if original_code:
                user_msg += f"\nORIGINAL CODE CONTEXT (for cross-file verification):\n{original_code}\n"
            if diagnosis_issues:
                user_msg += f"\nDIAGNOSED ISSUES (verify ALL are addressed):\n"
                for i, issue in enumerate(diagnosis_issues, 1):
                    user_msg += f"  {i}. {issue}\n"
            if diagnosis_text:
                user_msg += f"\nDIAGNOSIS: {diagnosis_text}\n"

            self._log(f"Generating LLM safety evaluation for mode: {mode}...")
            response = llm_client.generate(prompt=user_msg, system=system_prompt, temperature=0.1)
            
            if not response or not response.strip():
                raise ValueError(f"[Safety] LLM returned empty response for mode '{mode}'.")
            
            parsed = self._extract_json(response)
            
            if not parsed:
                raise ValueError(
                    f"[Safety] JSON extraction failed. LLM returned non-JSON: "
                    f"{response[:200]}..."
                )

            # Normalize: wrap flat responses into contribution structure
            if "contribution" not in parsed:
                parsed["contribution"] = {
                    "safe": parsed.pop("safe", True),
                    "risk_score": parsed.pop("risk_score", 0.0),
                    "warnings": parsed.pop("warnings", []),
                    "reasoning": parsed.pop("reasoning", "")
                }
            else:
                if "reasoning" not in parsed["contribution"]:
                    parsed["contribution"]["reasoning"] = parsed.get("reasoning", "")
            if "chain_of_thought" not in parsed:
                parsed["chain_of_thought"] = []
            if "lokr_requests" not in parsed:
                parsed["lokr_requests"] = []
                    
            contrib = parsed.get("contribution", {})
            
            # Mode-specific required fields
            if mode == "review":
                required_keys = ["security_issues", "performance_concerns", "deployment_risk", "approval", "rollback_plan"]
            elif mode == "prevent":
                required_keys = ["deployment_risk", "estimated_rollback_time", "health_checks", "go_no_go", "reasoning"]
            else:
                required_keys = ["safe", "risk_score", "warnings"]
            
            missing_keys = [k for k in required_keys if k not in contrib]
            if missing_keys:
                raise ValueError(
                    f"[Safety] Mode '{mode}' requires fields {missing_keys} in contribution. "
                    f"Got keys: {list(contrib.keys())}. Response: {response[:200]}..."
                )
            
            self._log("Safety evaluation completed successfully via LLM.")
            return parsed
        else:
            raise ValueError("[Safety] No LLM client provided.")
        
        self._log("Safety evaluation completed.")


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
