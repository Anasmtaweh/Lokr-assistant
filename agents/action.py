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

        import re
        # Find the first { and last }
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            json_str = text[first_brace:last_brace+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try to handle literal newlines in JSON strings by replacing them with a space
                # for initial parsing, or better, just allow them if possible.
                # Here we use a simpler replacement that avoids breaking structural newlines.
                try:
                    # Replace only newlines that are clearly inside what looks like a value
                    # A very rough but often effective hack for LLM JSON:
                    sanitized = json_str.replace('\n', '\\n')
                    # But wait, that breaks the structure too. 
                    # Let's try the strict=False approach first, then fallback to a space.
                    return json.loads(json_str, strict=False)
                except:
                    sanitized = re.sub(r'(?<!\\)\n', ' ', json_str)
                    return json.loads(sanitized)
        
        self._log(f"JSON extraction failed for response: {text[:200]}...", level="WARNING")
        # Store the raw text on the instance so we can retrieve it in run() if needed
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
        self._log("Starting action generation...")
        
        mode = state.get("mode", self.mode)

        if llm_client:
            system_prompt = get_agent_prompt("action", mode)
            
            # Check if this is a targeted revision request from Safety
            safety_feedback = state.get("safety_feedback")
            
            if safety_feedback and safety_feedback.get("rejected"):
                # FAST PATH: Targeted revision — Safety told us exactly what to fix
                import json as _json
                self._log("Building targeted revision prompt from Safety feedback...")
                
                # Get diagnosis from the preserved hypothesis
                diagnosis = ""
                if state.get("hypotheses"):
                    latest_hypothesis = state["hypotheses"][-1]
                    contrib = latest_hypothesis.get("contribution", latest_hypothesis)
                    diagnosis = contrib.get("diagnosis", "")
                    
                user_msg = f"DIAGNOSIS (from previous analysis):\n{diagnosis}\n"
                user_msg += f"\nSAFETY REJECTION — TARGETED REVISION REQUEST:\n"
                user_msg += f"The Safety Agent rejected your previous patch for these reasons:\n"
                user_msg += f"Warnings: {', '.join(safety_feedback.get('warnings', []))}\n"
                user_msg += f"Reasoning: {safety_feedback.get('reasoning', '')}\n\n"
                user_msg += f"SPECIFIC REVISIONS REQUIRED:\n"
                for i, suggestion in enumerate(safety_feedback.get("suggestions", []), 1):
                    user_msg += f"  {i}. {suggestion}\n"
                user_msg += (
                    f"\nYour task: Generate a REVISED patch that addresses ONLY the issues above. "
                    f"Keep all other fixes from the original patch intact. "
                    f"Do NOT re-analyze the entire codebase — just apply the requested revisions.\n"
                )
                
                if "original_input" in state:
                    user_msg += f"\nORIGINAL CODE:\n{state['original_input']}\n"
            else:
                # NORMAL PATH: Full patch generation from diagnosis
                diagnosis = ""
                issues_list = []
                hypothesis = ""
                if state.get("hypotheses"):
                    latest_hypothesis = state["hypotheses"][-1]
                    if "contribution" in latest_hypothesis:
                        diagnosis = latest_hypothesis["contribution"].get("diagnosis", "")
                        issues_list = latest_hypothesis["contribution"].get("issues", [])
                        hypothesis = latest_hypothesis["contribution"].get("hypothesis", "")
                    else:
                        diagnosis = latest_hypothesis.get("diagnosis", "")
                        issues_list = latest_hypothesis.get("issues", [])
                        hypothesis = latest_hypothesis.get("hypothesis", "")
                
                user_msg = f"DIAGNOSIS TO ACT UPON:\n{diagnosis}\n"
                if hypothesis:
                    user_msg += f"\nROOT CAUSE HYPOTHESIS:\n{hypothesis}\n"
                if issues_list:
                    user_msg += f"\nALL ISSUES TO FIX (you MUST address EVERY item):\n"
                    for i, issue in enumerate(issues_list, 1):
                        user_msg += f"  {i}. {issue}\n"
                    user_msg += f"\nTotal issues: {len(issues_list)}. Your patch MUST contain fixes for ALL {len(issues_list)} issues listed above.\n"
                
                if "original_input" in state:
                    user_msg += f"\nORIGINAL CODE:\n{state['original_input']}\n"
                    
                # Include safety warnings if re-running (old-style needs_revision)
                if state.get("needs_revision") and state.get("safety_reports"):
                    latest_safety = state["safety_reports"][-1]
                    s_contrib = latest_safety.get("contribution", {}) if "contribution" in latest_safety else latest_safety
                    warnings = s_contrib.get("warnings", [])
                    reasoning = s_contrib.get("reasoning", "")
                    
                    user_msg += f"\nSAFETY REJECTION FEEDBACK:\n"
                    user_msg += f"Warnings: {warnings}\n"
                    if reasoning:
                        user_msg += f"Safety reasoning for rejection: {reasoning}\n"
                    user_msg += f"Instruction: Your previous patch was rejected for safety reasons. Fix these specific issues.\n"

            self._log(f"Generating LLM action for mode: {mode}...")
            response = llm_client.generate(prompt=user_msg, system=system_prompt, temperature=0.2)
            
            if not response or not response.strip():
                raise ValueError(f"[Action] LLM returned empty response for mode '{mode}'.")
            
            parsed = self._extract_json(response)
            
            if not parsed:
                raise ValueError(
                    f"[Action] JSON extraction failed. LLM returned non-JSON: "
                    f"{response[:200]}..."
                )

            # Normalize: wrap flat responses into contribution structure
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
            
            # Mode-specific required fields
            if mode == "repair":
                required_keys = ["action_type", "patch"]
            elif mode == "review":
                required_keys = ["observations", "recommendations", "suggestion_priority"]
            elif mode == "prevent":
                required_keys = ["blockers", "warnings", "recommendations"]
            else:
                required_keys = []

            missing_keys = [k for k in required_keys if k not in contrib]
            if missing_keys:
                raise ValueError(
                    f"[Action] Mode '{mode}' requires fields {missing_keys} in contribution. "
                    f"Got keys: {list(contrib.keys())}. Response: {response[:200]}..."
                )
            
            self._log("Action generation completed successfully via LLM.")
            return parsed
        else:
            raise ValueError("[Action] No LLM client provided.")


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
