import time
import os
import json
import logging
from config.settings import API_KEY, MODEL_NAME, MAX_RETRIES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIClient:
    def __init__(self):
        self.model_name = MODEL_NAME
        api_key = os.getenv("API_KEY") or os.getenv("GEMINI_API_KEY")
        surf_key = os.getenv("SURF_API_KEY")
        
        self.is_surf = (api_key and api_key.startswith("ua_")) or bool(surf_key)
        self.is_openrouter = api_key and api_key.startswith("sk-or-")
        self.is_openai = not (self.is_surf or self.is_openrouter)

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
        """
        Generate content using OpenRouter, Unlimited Surf, or OpenAI with retry mechanism.
        """
        api_key = os.getenv("API_KEY") or os.getenv("GEMINI_API_KEY")
        surf_key = os.getenv("SURF_API_KEY")
        surf_base_url = os.getenv("SURF_BASE_URL", "https://unlimited.surf/v1")
        
        is_surf = (api_key and api_key.startswith("ua_")) or bool(surf_key)
        is_openrouter = api_key and api_key.startswith("sk-or-")
        
        if is_surf:
            provider_name = "Unlimited Surf"
            active_key = surf_key if surf_key else api_key
            base_url = surf_base_url.rstrip("/")
            url = f"{base_url}/messages"
            headers = {
                "Authorization": f"Bearer {active_key}",
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
        elif is_openrouter:
            provider_name = "OpenRouter"
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Saliha-Noor/OutreachNode",
                "X-Title": "Outreach Node Outreach Emailer"
            }
        else:
            provider_name = "OpenAI"
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        
        if is_surf:
            payload = {
                "model": self.model_name,
                "system": system_prompt or "",
                "messages": [{"role": "user", "content": user_prompt}],
                "max_tokens": 4096,
                "temperature": temperature
            }
        else:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Generating content via {provider_name} using {self.model_name} (Attempt {attempt}/{MAX_RETRIES})...")
                import requests
                response = requests.post(url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                res_json = response.json()
                
                if "choices" in res_json and res_json["choices"]:
                    content = res_json["choices"][0]["message"]["content"]
                elif "content" in res_json and res_json["content"]:
                    if isinstance(res_json["content"], list):
                        parts = [c["text"] for c in res_json["content"] if c.get("type") == "text"]
                        content = "".join(parts)
                    else:
                        content = res_json["content"]
                elif "error" in res_json:
                    raise ValueError(f"{provider_name} API error: {res_json['error']}")
                else:
                    raise ValueError(f"{provider_name} unrecognized response structure: {response.text}")
                    
                if not content:
                    raise ValueError(f"Received empty content from {provider_name} API.")
                return content
            except Exception as e:
                logger.error(f"{provider_name} Error on attempt {attempt}: {str(e)}")
                if attempt == MAX_RETRIES:
                    raise e
                time.sleep(2 ** attempt)

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        """
        Generate JSON content and return it parsed as a Python dictionary.
        """
        response_text = self.generate(system_prompt, user_prompt, temperature, json_mode=True)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response_text}")
            raise e
