import time
import os
import json
import logging
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, MODEL_NAME, MAX_RETRIES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the Gemini API dynamically if no custom provider is detected at import time
api_key = os.getenv("GEMINI_API_KEY")
surf_key = os.getenv("SURF_API_KEY")
is_surf = (api_key and api_key.startswith("ua_")) or bool(surf_key)
is_openrouter = api_key and api_key.startswith("sk-or-")
is_openai = api_key and api_key.startswith("sk-") and not api_key.startswith("sk-or-")
is_gemini = not (is_surf or is_openrouter or is_openai)

if is_gemini:
    if api_key:
        genai.configure(api_key=api_key)
    else:
        logger.warning("GEMINI_API_KEY not configured! Gemini client might fail.")

class GeminiClient:
    def __init__(self):
        self.model_name = MODEL_NAME
        api_key = os.getenv("GEMINI_API_KEY")
        surf_key = os.getenv("SURF_API_KEY")
        
        self.is_surf = (api_key and api_key.startswith("ua_")) or bool(surf_key)
        self.is_openrouter = api_key and api_key.startswith("sk-or-")
        self.is_openai = api_key and api_key.startswith("sk-") and not api_key.startswith("sk-or-")
        self.is_gemini = not (self.is_surf or self.is_openrouter or self.is_openai)
        
        if self.is_gemini:
            self.client = genai.GenerativeModel(self.model_name)

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
        """
        Generate content using Gemini API, OpenRouter, Unlimited Surf, or OpenAI with retry mechanism.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        surf_key = os.getenv("SURF_API_KEY")
        surf_base_url = os.getenv("SURF_BASE_URL", "https://unlimited.surf/v1")
        
        is_surf = (api_key and api_key.startswith("ua_")) or bool(surf_key)
        is_openrouter = api_key and api_key.startswith("sk-or-")
        is_openai = api_key and api_key.startswith("sk-") and not api_key.startswith("sk-or-")
        is_gemini = not (is_surf or is_openrouter or is_openai)
        
        if is_surf or is_openrouter or is_openai:
            if is_surf:
                provider_name = "Unlimited Surf"
                active_key = surf_key if surf_key else api_key
                base_url = surf_base_url.rstrip("/")
                url = f"{base_url}/messages"
                headers = {
                    "Authorization": f"Bearer {active_key}",
                    "Content-Type": "application/json"
                }
            elif is_openrouter:
                provider_name = "OpenRouter"
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/Saliha-Noor/GreenFactor",
                    "X-Title": "GreenFactor Outreach Emailer"
                }
            else:
                provider_name = "OpenAI"
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": temperature
            }
            if is_surf:
                payload["max_tokens"] = 4096
            if json_mode and not is_surf:
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
                            content = res_json["content"][0]["text"]
                        else:
                            content = res_json["content"]
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
        else:
            generation_config = {
                "temperature": temperature,
            }
            if json_mode:
                generation_config["response_mime_type"] = "application/json"

            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt
            )

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    logger.info(f"Generating content using {self.model_name} (Attempt {attempt}/{MAX_RETRIES})...")
                    response = model.generate_content(
                        user_prompt,
                        generation_config=generation_config
                    )
                    
                    if not response.text:
                        raise ValueError("Received empty response text from Gemini API.")
                    
                    return response.text
                    
                except Exception as e:
                    logger.error(f"Error on attempt {attempt}: {str(e)}")
                    if attempt == MAX_RETRIES:
                        raise e
                    time.sleep(2 ** attempt)  # Exponential backoff

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

