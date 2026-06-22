import unittest
from unittest.mock import MagicMock, patch
from middleware.gemini_client import GeminiClient
from agents.prospecting_agent import ProspectingAgent
from agents.context_agent import ContextAgent
from agents.copywriter_agent import CopywriterAgent
from agents.proofreader_agent import ProofreaderAgent
from agents.orchestrator_agent import OrchestratorAgent

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

    def test_orchestrator_agent(self):
        agent = OrchestratorAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "research_focus": "Find their tech stack and service gaps",
            "linkedin_priority": "medium",
            "web_priority": "high",
            "linkedin_search_queries": ["{name} {company} profile"],
            "web_search_queries": ["{company} services products"],
            "email_angle": "Position as a technology partner",
            "key_requirements": ["Reference specific services", "Include ROI"],
            "tone_guidance": "Confident but not pushy"
        }
        
        plan = agent.analyze_prompt("Pitch our AI solutions", {"tone": "friendly"})
        
        self.assertEqual(plan["linkedin_priority"], "medium")
        self.assertEqual(plan["web_priority"], "high")
        self.assertIn("original_prompt", plan)
        self.assertEqual(plan["original_prompt"], "Pitch our AI solutions")
        self.mock_gemini.generate_json.assert_called_once()

    def test_orchestrator_agent_fallback(self):
        agent = OrchestratorAgent(self.mock_gemini)
        self.mock_gemini.generate_json.side_effect = Exception("API Error")
        
        plan = agent.analyze_prompt("Pitch our services", {"tone": "formal"})
        
        # Should return fallback plan, not raise
        self.assertIn("research_focus", plan)
        self.assertIn("original_prompt", plan)
        self.assertEqual(plan["original_prompt"], "Pitch our services")

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

    def test_linkedin_agent_with_research_plan(self):
        from agents.linkedin_agent import LinkedInAgent
        agent = LinkedInAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "linkedin_url": "https://linkedin.com/in/sundarpichai",
            "linkedin_summary": "CEO driving AI initiatives.",
            "linkedin_insights": ["Focused on AI growth"]
        }
        
        # Mock DDGS inside linkedin_agent for orchestrator-guided queries
        with patch('agents.linkedin_agent.DDGS') as mock_ddgs_cls:
            mock_ddgs_ctx = MagicMock()
            mock_ddgs_ctx.text.return_value = [{"title": "Extra", "body": "extra snippet"}]
            mock_ddgs_cls.return_value.__enter__ = MagicMock(return_value=mock_ddgs_ctx)
            
            research_plan = {
                "linkedin_search_queries": ["{name} {company} AI leadership"],
                "linkedin_priority": "high",
                "research_focus": "Find AI leadership details",
                "original_prompt": "Connect about AI"
            }
            
            prospect_profile = {"name": "Sundar Pichai", "company": "Google", "title": "CEO"}
            insights = agent.run(prospect_profile, research_plan)
            
            self.assertEqual(insights["linkedin_url"], "https://linkedin.com/in/sundarpichai")

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

    def test_context_agent_with_research_plan(self):
        agent = ContextAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "company_summary": "Google is a tech company.",
            "recent_news": ["AI growth"],
            "pain_points": ["Regulations"],
            "talking_points": ["Congrats on AI updates"],
            "custom_alignment": "Strong alignment on cloud solutions."
        }
        
        research_plan = {
            "web_search_queries": ["{company} AI products"],
            "web_priority": "high",
            "research_focus": "Find AI product details",
            "key_requirements": ["Reference AI products"],
            "email_angle": "AI partnership"
        }
        
        prospect_profile = {"company": "Google"}
        brief = agent.run(prospect_profile, {}, {"custom_prompt": "AI pitch"}, research_plan)
        
        self.assertEqual(brief["company_summary"], "Google is a tech company.")

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

    def test_copywriter_agent_with_research_plan(self):
        agent = CopywriterAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "subject": "AI Partnership with Google",
            "body": "Hello Sundar, regarding your AI initiatives...",
            "personalization_hooks": ["AI leadership", "Gemini launch"]
        }
        
        research_plan = {
            "email_angle": "AI partnership opportunity",
            "key_requirements": ["Reference specific AI products"],
            "tone_guidance": "Confident but curious",
            "original_prompt": "Pitch AI collaboration"
        }
        
        email = agent.run({"name": "Sundar", "company": "Google"}, {}, {}, {}, research_plan)
        self.assertEqual(email["subject"], "AI Partnership with Google")

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

    def test_proofreader_agent_with_research_plan(self):
        agent = ProofreaderAgent(self.mock_gemini)
        self.mock_gemini.generate_json.return_value = {
            "approved": False,
            "relevance_score": 5,
            "tone_score": 8,
            "personalization_score": 6,
            "accuracy_score": 10,
            "score": 7,
            "critique": "Email doesn't address the AI partnership angle.",
            "issues": ["Missing AI focus"]
        }
        
        research_plan = {
            "email_angle": "AI partnership",
            "key_requirements": ["Reference AI products"],
            "original_prompt": "Pitch AI collaboration"
        }
        
        evaluation = agent.run(
            {"subject": "Generic", "body": "Hi there..."},
            {"name": "Sundar", "company": "Google"},
            {}, {}, {"custom_prompt": "AI pitch"}, research_plan
        )
        self.assertFalse(evaluation["approved"])
        self.assertEqual(evaluation["score"], 7)

if __name__ == '__main__':
    unittest.main()
