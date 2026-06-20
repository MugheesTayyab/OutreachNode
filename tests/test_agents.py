import unittest
from unittest.mock import MagicMock, patch
from middleware.gemini_client import GeminiClient
from agents.prospecting_agent import ProspectingAgent
from agents.context_agent import ContextAgent
from agents.copywriter_agent import CopywriterAgent
from agents.proofreader_agent import ProofreaderAgent

class TestAgents(unittest.TestCase):
    def setUp(self):
        self.mock_gemini = MagicMock(spec=GeminiClient)
        
        # Patch search functions to avoid real network requests
        self.patcher_search_person = patch('agents.prospecting_agent.search_person', return_value=["search snippet"])
        self.patcher_search_linkedin = patch('agents.linkedin_agent.search_linkedin', return_value=["linkedin snippet"])
        self.patcher_search_company_news = patch('agents.context_agent.search_company_news', return_value=[{"title": "News Title", "snippet": "news snippet", "url": "http://news"}])
        self.patcher_get_company_summary = patch('agents.context_agent.get_company_summary', return_value="Google summary")
        
        # Mock DDGS class in ContextAgent
        self.mock_ddgs_instance = MagicMock()
        self.mock_ddgs_instance.text.return_value = [{"title": "Web Title", "href": "http://web", "body": "web snippet"}]
        self.patcher_ddgs = patch('agents.context_agent.DDGS', return_value=MagicMock(__enter__=MagicMock(return_value=self.mock_ddgs_instance)))
        
        self.patcher_search_person.start()
        self.patcher_search_linkedin.start()
        self.patcher_search_company_news.start()
        self.patcher_get_company_summary.start()
        self.patcher_ddgs.start()
        
    def tearDown(self):
        self.patcher_search_person.stop()
        self.patcher_search_linkedin.stop()
        self.patcher_search_company_news.stop()
        self.patcher_get_company_summary.stop()
        self.patcher_ddgs.stop()

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

    def test_linkedin_agent(self):
        from agents.linkedin_agent import LinkedInAgent
        agent = LinkedInAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "linkedin_url": "https://linkedin.com/in/sundarpichai",
            "linkedin_summary": "Sundar Pichai LinkedIn summary.",
            "linkedin_insights": ["Focused on AI growth"]
        }
        
        prospect_profile = {"name": "Sundar Pichai", "company": "Google", "title": "CEO"}
        insights = agent.run(prospect_profile)
        
        self.assertEqual(insights["linkedin_url"], "https://linkedin.com/in/sundarpichai")
        self.mock_gemini.generate_json.assert_called_once()

    def test_context_agent(self):
        agent = ContextAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "company_summary": "Google is a tech company.",
            "recent_news": ["AI growth"],
            "pain_points": ["Regulations"],
            "talking_points": ["Congrats on AI updates"],
            "custom_alignment": "Strong alignment on cloud solutions."
        }
        
        prospect_profile = {"company": "Google"}
        brief = agent.run(prospect_profile, {}, {"custom_prompt": "Sell cloud"})
        
        self.assertEqual(brief["company_summary"], "Google is a tech company.")
        self.mock_gemini.generate_json.assert_called_once()

    def test_copywriter_agent(self):
        agent = CopywriterAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "subject": "Outreach",
            "body": "Hello Sundar...",
            "personalization_hooks": ["AI work"]
        }
        
        email = agent.run({"name": "Sundar", "company": "Google"}, {}, {}, {})
        self.assertEqual(email["subject"], "Outreach")
        self.mock_gemini.generate_json.assert_called_once()

    def test_proofreader_agent(self):
        agent = ProofreaderAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "approved": True,
            "relevance_score": 9,
            "tone_score": 9,
            "personalization_score": 9,
            "accuracy_score": 10,
            "score": 9,
            "critique": "Looks great!",
            "issues": []
        }
        
        evaluation = agent.run({"subject": "Outreach", "body": "Hello Sundar..."}, {}, {}, {}, {"custom_prompt": "pitch AI"})
        self.assertTrue(evaluation["approved"])
        self.assertEqual(evaluation["score"], 9)
        self.assertEqual(evaluation["relevance_score"], 9)
        self.mock_gemini.generate_json.assert_called_once()

if __name__ == '__main__':
    unittest.main()
