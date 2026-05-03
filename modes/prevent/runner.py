"""
PREVENT Mode Pipeline Runner

This module provides the run_prevent function, which orchestrates the execution
of the Analyzer, Action, Safety, and Validator agents specifically for the
prevent mode pipeline, with support for LLM and Lokr integration.
"""

from typing import Dict, Any, Optional
from agents.analyzer import AnalyzerAgent
from agents.action import ActionAgent
from agents.safety import SafetyAgent
from agents.validator import ValidatorAgent


def run_prevent(code: str, config: Optional[Dict[str, Any]] = None, llm_client: Any = None, lokr_service: Any = None) -> Dict[str, Any]:
    """
    Run the prevent pipeline on the given codebase representation.
    
    Args:
        code (str): The codebase representation or config.
        config (dict, optional): Configuration overrides for agents. Defaults to None.
        llm_client (Any, optional): The LLM client to use.
        lokr_service (Any, optional): The Lokr service to use.
        
    Returns:
        dict: The final result containing the outputs of all agents and the overall status.
    """
    config = config or {}
    
    print("[PREVENT] Pipeline started...")
    
    # Instantiate agents with real LLM and Lokr service
    analyzer = AnalyzerAgent(mode="prevent", llm_client=llm_client, lokr_service=lokr_service)
    action_agent = ActionAgent(mode="prevent", llm_client=llm_client, lokr_service=lokr_service)
    safety_agent = SafetyAgent(mode="prevent", llm_client=llm_client, lokr_service=lokr_service)
    validator_agent = ValidatorAgent(mode="prevent", llm_client=llm_client, lokr_service=lokr_service)
    
    # Step 1: Analyzer
    analysis_result = analyzer.run({"code": code, "mode": "prevent"})
    
    # Step 2: Action
    action_result = action_agent.run({
        "diagnosis": analysis_result.get("diagnosis", ""), 
        "code": code,
        "mode": "prevent"
    })
    
    # Step 3: Safety
    safety_result = safety_agent.run({
        "proposed_action": action_result, 
        "mode": "prevent"
    })
    
    # Step 4: Validator
    validation_result = validator_agent.run({
        "action_result": action_result,
        "safety_result": safety_result,
        "original_code": code,
        "mode": "prevent"
    })
    
    status = "success" if validation_result.get("status") == "success" else "failure"
    
    print(f"[PREVENT] Pipeline finished with status: {status}")
    
    return {
        "analysis": analysis_result,
        "action": action_result,
        "safety": safety_result,
        "validation": validation_result,
        "status": status
    }
