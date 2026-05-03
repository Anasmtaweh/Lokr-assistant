"""
LLM Client module for interacting with Ollama.
"""

import requests
import json
from typing import List, Dict, Optional


class LLMClient:
    """
    Client for interacting with a local Ollama instance.
    """

    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://localhost:11434", api_type: str = "ollama", api_key: str = ""):
        """
        Initialize the LLMClient.

        Args:
            model (str): The name of the model to use. Defaults to "qwen2.5-coder:7b".
            base_url (str): The base URL of the Ollama API. Defaults to "http://localhost:11434".
            api_type (str): "ollama" or "openai". Defaults to "ollama".
            api_key (str): API key for OpenAI-compatible endpoints.
        """
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.api_type = api_type
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        """
        Send a chat request to the Ollama API.

        Args:
            messages (list): A list of message dictionaries (e.g., [{"role": "user", "content": "..."}]).
            temperature (float): The sampling temperature. Defaults to 0.2.

        Returns:
            str: The content of the model's response.
        """
        if self.api_type == "openai":
            url = f"{self.base_url}/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature
            }
        else:
            url = f"{self.base_url}/api/chat"
            headers = None
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }

        import time
        for attempt in range(3):
            try:
                if headers:
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                else:
                    response = requests.post(url, json=payload, timeout=30)
                    
                response.raise_for_status()
                data = response.json()
                
                if self.api_type == "openai":
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    return data.get("message", {}).get("content", "")
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    print(f"Error communicating with LLM API after 3 attempts: {e}")
                    return ""
                time.sleep(1 + attempt)  # simple backoff

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.2) -> str:
        """
        Convenience method to generate a response from a single prompt.

        Args:
            prompt (str): The user prompt.
            system (str, optional): An optional system prompt.
            temperature (float): The sampling temperature. Defaults to 0.2.

        Returns:
            str: The content of the model's response.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return self.chat(messages, temperature=temperature)
