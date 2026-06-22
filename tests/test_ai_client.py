import unittest
from unittest.mock import patch, MagicMock
import os

class TestAIClientRouting(unittest.TestCase):
    def setUp(self):
        # Backup environment variables
        self.original_env = {
            "API_KEY": os.environ.get("API_KEY"),
            "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
            "SURF_API_KEY": os.environ.get("SURF_API_KEY"),
            "SURF_BASE_URL": os.environ.get("SURF_BASE_URL"),
        }

    def tearDown(self):
        # Restore environment variables
        for k, v in self.original_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    @patch("requests.post")
    def test_unlimited_surf_routing_by_api_key(self, mock_post):
        # Configure env variables to simulate ua_ prefix in API_KEY
        os.environ["API_KEY"] = "ua_testkey123"
        os.environ.pop("SURF_API_KEY", None)
        os.environ["SURF_BASE_URL"] = "https://unlimited.surf/v1"

        # Mock requests.post response in Anthropic style
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Hello from Surf!"}]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Import and instantiate client
        from middleware.ai_client import AIClient
        client = AIClient()
        
        response = client.generate("system prompt", "user prompt")
        
        self.assertEqual(response, "Hello from Surf!")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://unlimited.surf/v1/messages")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer ua_testkey123")

    @patch("requests.post")
    def test_unlimited_surf_routing_by_surf_api_key(self, mock_post):
        # Configure env variables to simulate SURF_API_KEY
        os.environ["API_KEY"] = "some_other_key"
        os.environ["SURF_API_KEY"] = "ua_surfkey999"
        os.environ["SURF_BASE_URL"] = "https://custom.surf/v1/"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Hello from Custom Surf!"}]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        from middleware.ai_client import AIClient
        client = AIClient()
        
        response = client.generate("system prompt", "user prompt")
        
        self.assertEqual(response, "Hello from Custom Surf!")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://custom.surf/v1/messages")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer ua_surfkey999")

    @patch("requests.post")
    def test_openrouter_routing(self, mock_post):
        # Configure env variables for OpenRouter
        os.environ["API_KEY"] = "sk-or-testkey"
        os.environ.pop("SURF_API_KEY", None)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from OpenRouter!"}}]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        from middleware.ai_client import AIClient
        client = AIClient()
        
        response = client.generate("system", "user")
        
        self.assertEqual(response, "Hello from OpenRouter!")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-or-testkey")

    @patch("requests.post")
    def test_openai_routing(self, mock_post):
        # Configure env variables for OpenAI (sk- but not sk-or-)
        os.environ["API_KEY"] = "sk-openaikey123"
        os.environ.pop("SURF_API_KEY", None)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello from OpenAI!"}}]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        from middleware.ai_client import AIClient
        client = AIClient()
        
        response = client.generate("system", "user")
        
        self.assertEqual(response, "Hello from OpenAI!")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-openaikey123")

if __name__ == '__main__':
    unittest.main()
