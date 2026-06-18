import unittest
from unittest.mock import MagicMock
from middleware.gemini_client import GeminiClient
from agents.prospecting_agent import ProspectingAgent
from agents.context_agent import ContextAgent
from agents.copywriter_agent import CopywriterAgent
from agents.proofreader_agent import ProofreaderAgent

class TestAgents(unittest.TestCase):
    def setUp(self):
        self.mock_gemini = MagicMock(spec=GeminiClient)
        
    def test_prospecting_agent(self):
        agent = ProspectingAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "name": "Sundar Pichai",
            "title": "CEO",
            "company": "Google",
            "key_interests": ["AI", "Search"],
            "career_highlights": ["Google CEO since 2015"],
            "professional_summary": "Sundar Pichai is the CEO of Google."
        }
        
        raw_prospect = {"name": "Sundar Pichai", "company": "Google", "title": "CEO"}
        profile = agent.run(raw_prospect)
        
        self.assertEqual(profile["name"], "Sundar Pichai")
        self.assertEqual(profile["company"], "Google")
        self.mock_gemini.generate_json.assert_called_once()

    def test_context_agent(self):
        agent = ContextAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "company_summary": "Google is a tech company.",
            "recent_news": ["AI growth"],
            "pain_points": ["Regulations"],
            "talking_points": ["Congrats on AI updates"]
        }
        
        prospect_profile = {"company": "Google"}
        brief = agent.run(prospect_profile)
        
        self.assertEqual(brief["company_summary"], "Google is a tech company.")
        self.mock_gemini.generate_json.assert_called_once()

    def test_copywriter_agent(self):
        agent = CopywriterAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "subject": "Outreach",
            "body": "Hello Sundar...",
            "personalization_hooks": ["AI work"]
        }
        
        email = agent.run({"name": "Sundar", "company": "Google"}, {}, {})
        self.assertEqual(email["subject"], "Outreach")
        self.mock_gemini.generate_json.assert_called_once()

    def test_proofreader_agent(self):
        agent = ProofreaderAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "approved": True,
            "score": 9,
            "critique": "Looks great!",
            "issues": []
        }
        
        evaluation = agent.run({"subject": "Outreach", "body": "Hello Sundar..."}, {}, {})
        self.assertTrue(evaluation["approved"])
        self.assertEqual(evaluation["score"], 9)
        self.mock_gemini.generate_json.assert_called_once()

if __name__ == '__main__':
    unittest.main()
