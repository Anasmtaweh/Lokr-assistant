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
            # Normalize: strip known suffixes so we always build from the root
            normalized = self.base_url
            for suffix in ["/v1/chat/completions", "/chat/completions", "/v1"]:
                if normalized.endswith(suffix):
                    normalized = normalized[: -len(suffix)]
                    break
            url = f"{normalized}/v1/chat/completions"
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
        import os
        import datetime
        import json
        
        # --- FORENSIC INSTRUMENTATION: LOG PAYLOAD & TOKENS ---
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        log_file = f"logs/llm_payload_{timestamp}.json"
        
        # Estimate tokens
        system_len = 0
        user_len = 0
        for m in messages:
            if m.get("role") == "system":
                system_len += len(m.get("content", ""))
            elif m.get("role") == "user":
                user_len += len(m.get("content", ""))
                
        # Estimate: ~4 chars per token
        token_estimate = (system_len + user_len) // 4
        truncation_warning = token_estimate > 20000
        
        debug_info = {
            "timestamp": timestamp,
            "model": self.model,
            "api_type": self.api_type,
            "token_estimate": token_estimate,
            "truncation_warning": truncation_warning,
            "system_chars": system_len,
            "user_chars": user_len,
            "payload": payload
        }
        
        with open(log_file, "w") as f:
            json.dump(debug_info, f, indent=2)
            
        print(f"[FORENSIC] LLM Request logged to {log_file} (Estimated Tokens: {token_estimate})")
        # ------------------------------------------------------
        
        for attempt in range(3):

            try:
                if headers:
                    response = requests.post(url, headers=headers, json=payload, timeout=120)
                else:
                    response = requests.post(url, json=payload, timeout=120)
                    
                response.raise_for_status()
                data = response.json()
                
                if self.api_type == "openai":
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    content = data.get("message", {}).get("content", "")
                
                # Handle DeepSeek/Reasoning models by stripping <think> tags
                if "<think>" in content and "</think>" in content:
                    import re
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                elif "<think>" in content: # If the model was cut off or only has opening tag
                    content = content.split("<think>")[-1].split("</think>")[-1].strip()
                    
                return content
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
