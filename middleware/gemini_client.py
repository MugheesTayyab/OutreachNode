import time
import json
import logging
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, MODEL_NAME, MAX_RETRIES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not configured! Gemini client might fail.")

class GeminiClient:
    def __init__(self):
        self.model_name = MODEL_NAME
        self.client = genai.GenerativeModel(self.model_name)

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, json_mode: bool = False) -> str:
        """
        Generate content using Gemini API with retry mechanism and optional JSON mode.
        """
        generation_config = {
            "temperature": temperature,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        # Combine system prompt and user prompt in a structured format
        # Gemini API allows passing system instruction in GenerativeModel constructor or as config.
        # To keep it simple and robust, we can instantiate the model with the system instruction.
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
