"""
Base Agent Module

This module provides the BaseAgent class, which serves as the foundational 
class for all agents in the multi-agent system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BaseAgent(ABC):
    """
    Base class for all agents.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the base agent.

        Args:
            name (str): The name of the agent.
            config (dict, optional): Configuration dictionary for the agent. Defaults to None.
        """
        self.name = name
        self.config = config if config is not None else {}

    def _log(self, message: str, level: str = "INFO"):
        """
        Simple logging mechanism for the agent.
        
        Args:
            message (str): The message to log.
            level (str): The log level. Defaults to "INFO".
        """
        print(f"[Agent: {self.name}] {level}: {message}")

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent's main logic on the given context and return a result dict.

        Args:
            context (dict): The input context for the agent.

        Returns:
            dict: The result of the agent's execution.
            
        Raises:
            NotImplementedError: If the subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

    def validate_result(self, result: Dict[str, Any], required_keys: List[str]) -> bool:
        """
        Validate that the result dictionary contains all required keys.

        Args:
            result (dict): The result dictionary to validate.
            required_keys (list): A list of required key strings.

        Returns:
            bool: True if valid, False otherwise.
        """
        if not isinstance(result, dict):
            self._log("Result is not a dictionary.", level="ERROR")
            return False
            
        for key in required_keys:
            if key not in result:
                self._log(f"Result is missing required key: '{key}'", level="ERROR")
                return False
                
        return True

    def __repr__(self) -> str:
        """
        String representation of the agent.
        """
        return f"<Agent: {self.name}>"
