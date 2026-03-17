import json
import urllib.request
import urllib.error
import logging
from typing import Dict, Any

from .base import LLMBackend

logger = logging.getLogger("LifeSimulator.LLM.Cloud")

class CloudLLMBackend(LLMBackend):
    def __init__(self, api_key: str, base_url: str = "[https://openrouter.ai/api/v1](https://openrouter.ai/api/v1)", model_name: str = "meta-llama/llama-3-8b-instruct:free"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        logger.info(f"Connected to cloud LLM, driving model: [{model_name}]")

    def _make_request(self, messages: list, temperature: float, is_json: bool) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature
        }
        
        if is_json:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except urllib.error.URLError as e:
            logger.error(f"Cloud API request failed: {e}")
            return ""

    def generate_text(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        return self._make_request(messages, temperature, is_json=False).strip()

    def generate_json(self, prompt: str, system_prompt: str = "", retry: int = 2) -> Dict[str, Any]:
        sys_prompt = system_prompt + "\n【Important Instruction】You must strictly return data in the legal JSON format. Do not include any additional explanations or Markdown tags."
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt}
        ]
        
        for attempt in range(retry):
            text = self._make_request(messages, temperature=0.6, is_json=True)
            if not text: continue
            
            try:
                import re
                match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
                else:
                    return json.loads(text)
            except json.JSONDecodeError as e:
                logger.warning(f"The JSON parsing failed for the {attempt + 1}th time. Attempting to retry. Error: {e}")
                
        return None
