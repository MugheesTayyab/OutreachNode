import os
import unittest
from unittest.mock import MagicMock, patch
from middleware.orchestrator import Orchestrator
from middleware.state_manager import StateManager
from middleware.gemini_client import GeminiClient
from config.settings import OUTPUT_DIR

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.campaign_id = "test_camp_123"
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
        
        # Clean up any state JSON files
        filepath = os.path.join(OUTPUT_DIR, f"campaign_{self.campaign_id}.json")
        excel_path = os.path.join(OUTPUT_DIR, f"campaign_{self.campaign_id}.xlsx")
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(excel_path):
            os.remove(excel_path)

    def test_full_pipeline_run(self):
        # Set up mock JSON returns for each step in the pipeline
        # ProspectingAgent mock return
        self.mock_gemini.generate_json.side_effect = [
            # Prospecting Agent call
            {
                "name": "Sundar Pichai",
                "title": "CEO",
                "company": "Google",
                "key_interests": ["AI"],
                "career_highlights": ["Google CEO"],
                "professional_summary": "Pichai is CEO."
            },
            # LinkedIn Agent call
            {
                "linkedin_url": "https://linkedin.com/in/sundarpichai",
                "linkedin_summary": "Sundar Pichai is the CEO of Alphabet and Google.",
                "linkedin_insights": ["Enjoys talking about AI advancements"]
            },
            # Context Agent call
            {
                "company_summary": "Google is web giant.",
                "recent_news": ["AI updates"],
                "pain_points": ["Competition"],
                "talking_points": ["Congrats on Gemini 2.0"],
                "custom_alignment": "Aligns well with sustainability objective."
            },
            # Copywriter Agent call
            {
                "subject": "Outreach to Sundar",
                "body": "Hi Sundar, congrats on Gemini 2.0...",
                "personalization_hooks": ["Gemini 2.0"]
            },
            # Proofreader Agent call
            {
                "approved": True,
                "relevance_score": 9,
                "tone_score": 9,
                "personalization_score": 9,
                "accuracy_score": 10,
                "score": 9,
                "critique": "Looks excellent.",
                "issues": []
            }
        ]
        
        # Init campaign state
        prospects = [{"name": "Sundar Pichai", "company": "Google", "title": "CEO", "email": "sundar@google.com"}]
        settings = {
            "sender_name": "Mughees Tayyab",
            "sender_role": "Founder",
            "sender_company": "GreenFactor",
            "tone": "friendly",
            "goal": "partnership",
            "auto_generate_audio": False
        }
        
        StateManager.init_campaign(self.campaign_id, prospects, settings)
        
        orchestrator = Orchestrator(gemini_client=self.mock_gemini)
        
        # Run Campaign
        orchestrator.run_campaign(self.campaign_id)
        
        # Verify state was saved and completed
        state = StateManager.load_state(self.campaign_id)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["prospects"][0]["status"], "approved")
        self.assertEqual(state["prospects"][0]["proofread_score"], 9)
        self.assertEqual(state["prospects"][0]["email_subject"], "Outreach to Sundar")
        
        # Verify final Excel was saved
        excel_path = os.path.join(OUTPUT_DIR, f"campaign_{self.campaign_id}.xlsx")
        self.assertTrue(os.path.exists(excel_path))

if __name__ == '__main__':
    unittest.main()
