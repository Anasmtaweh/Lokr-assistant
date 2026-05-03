"""
REPAIR Mode Pipeline Runner

This module provides the run_repair function, which orchestrates the execution
of the Analyzer, Action, Safety, and Validator agents specifically for the
repair mode pipeline, with support for LLM and Lokr integration.
"""

from typing import Dict, Any, Optional
from agents.analyzer import AnalyzerAgent
from agents.action import ActionAgent
from agents.safety import SafetyAgent
from agents.validator import ValidatorAgent


def run_repair(code: str, config: Optional[Dict[str, Any]] = None, llm_client: Any = None, lokr_service: Any = None) -> Dict[str, Any]:
    """
    Run the repair pipeline on the given code snippet.
    
    Args:
        code (str): The code to be analyzed and repaired.
        config (dict, optional): Configuration overrides for agents. Defaults to None.
        llm_client (Any, optional): The LLM client to use.
        lokr_service (Any, optional): The Lokr service to use.
        
    Returns:
        dict: The final result containing the outputs of all agents and the overall status.
    """
    config = config or {}
    
    print("[REPAIR] Pipeline started...")
    
    # Instantiate agents with real LLM and Lokr service
    analyzer = AnalyzerAgent(mode="repair", llm_client=llm_client, lokr_service=lokr_service)
    action_agent = ActionAgent(mode="repair", llm_client=llm_client, lokr_service=lokr_service)
    safety_agent = SafetyAgent(mode="repair", llm_client=llm_client, lokr_service=lokr_service)
    validator_agent = ValidatorAgent(mode="repair", llm_client=llm_client, lokr_service=lokr_service)
    
    # Step 1: Analyzer
    analysis_result = analyzer.run({"code": code, "mode": "repair"})
    
    # Enrich context for Action Agent using Lokr if available
    extra_context = ""
    if lokr_service and analysis_result.get("diagnosis"):
        print("[REPAIR] Enriching action context via Lokr search...")
        extra_context = lokr_service.get_relevant_context(analysis_result["diagnosis"], top_k=3)

    # Step 2: Action
    action_result = action_agent.run({
        "diagnosis": analysis_result.get("diagnosis", ""), 
        "code": code,
        "extra_context": extra_context,
        "mode": "repair"
    })
    
    # Step 3: Safety
    safety_result = safety_agent.run({
        "proposed_action": action_result, 
        "mode": "repair"
    })
    
    # Step 4: Validator
    validation_result = validator_agent.run({
        "action_result": action_result,
        "safety_result": safety_result,
        "original_code": code,
        "mode": "repair"
    })
    
    status = "success" if validation_result.get("status") == "success" else "failure"
    
    print(f"[REPAIR] Pipeline finished with status: {status}")
    
    return {
        "analysis": analysis_result,
        "action": action_result,
        "safety": safety_result,
        "validation": validation_result,
        "status": status
    }
