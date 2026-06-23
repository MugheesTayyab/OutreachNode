import os
import unittest
from unittest.mock import MagicMock, patch
from middleware.orchestrator import Orchestrator
from middleware.state_manager import StateManager
from middleware.ai_client import AIClient
from config.settings import OUTPUT_DIR

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.campaign_id = "test_camp_123"
        self.mock_ai = MagicMock(spec=AIClient)
        
        # Patch search functions to avoid real network requests
        self.patcher_search_person = patch('agents.prospecting_agent.search_person', return_value=["search snippet"])
        self.patcher_search_linkedin = patch('agents.linkedin_agent.search_linkedin', return_value=["linkedin snippet"])
        self.patcher_search_company_news = patch('agents.context_agent.search_company_news', return_value=[{"title": "News Title", "snippet": "news snippet", "url": "http://news"}])
        self.patcher_get_company_summary = patch('agents.context_agent.get_company_summary', return_value="Google summary")
        
        # Mock DDGS class in ContextAgent
        self.mock_ddgs_instance = MagicMock()
        self.mock_ddgs_instance.text.return_value = [{"title": "Web Title", "href": "http://web", "body": "web snippet"}]
        self.patcher_ddgs_context = patch('agents.context_agent.DDGS', return_value=MagicMock(__enter__=MagicMock(return_value=self.mock_ddgs_instance)))
        
        # Mock DDGS class in LinkedInAgent (for orchestrator-guided queries)
        self.patcher_ddgs_linkedin = patch('agents.linkedin_agent.DDGS', return_value=MagicMock(__enter__=MagicMock(return_value=self.mock_ddgs_instance)))
        
        self.patcher_search_person.start()
        self.patcher_search_linkedin.start()
        self.patcher_search_company_news.start()
        self.patcher_get_company_summary.start()
        self.patcher_ddgs_context.start()
        self.patcher_ddgs_linkedin.start()
        
    def tearDown(self):
        self.patcher_search_person.stop()
        self.patcher_search_linkedin.stop()
        self.patcher_search_company_news.stop()
        self.patcher_get_company_summary.stop()
        self.patcher_ddgs_context.stop()
        self.patcher_ddgs_linkedin.stop()
        
        # Clean up any state JSON files
        filepath = os.path.join(OUTPUT_DIR, f"campaign_{self.campaign_id}.json")
        excel_path = os.path.join(OUTPUT_DIR, f"campaign_{self.campaign_id}.xlsx")
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(excel_path):
            os.remove(excel_path)

    def test_full_pipeline_run(self):
        """
        Tests the full pipeline including the OrchestratorAgent analyzing the prompt,
        then prospect processing through all agents with research_plan guidance.
        """
        # Set up mock JSON returns for each step in the pipeline
        self.mock_ai.generate_json.side_effect = [
            # OrchestratorAgent.analyze_prompt call
            {
                "research_focus": "Find their tech stack and service offerings",
                "linkedin_priority": "medium",
                "web_priority": "high",
                "linkedin_search_queries": ["{name} {company} leadership"],
                "web_search_queries": ["{company} technology services"],
                "email_angle": "Position as a complementary technology partner",
                "key_requirements": ["Reference specific services", "Suggest concrete collaboration"],
                "tone_guidance": "Confident but respectful"
            },
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
                "talking_points": ["Congrats on the AI launch"],
                "custom_alignment": "Aligns well with sustainability objective."
            },
            # Copywriter Agent call
            {
                "subject": "Outreach to Sundar",
                "body": "Hi Sundar, congrats on the AI launch...",
                "personalization_hooks": ["AI launch"]
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
            "sender_company": "Outreach Node",
            "tone": "friendly",
            "goal": "partnership",
            "custom_prompt": "Pitch our AI drone monitoring solutions for precision agriculture",
            "auto_generate_audio": False
        }
        
        StateManager.init_campaign(self.campaign_id, prospects, settings)
        
        orchestrator = Orchestrator(ai_client=self.mock_ai)
        
        # Run Campaign
        orchestrator.run_campaign(self.campaign_id)
        
        # Verify state was saved and completed
        state = StateManager.load_state(self.campaign_id)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["prospects"][0]["status"], "approved")
        self.assertEqual(state["prospects"][0]["proofread_score"], 9)
        self.assertEqual(state["prospects"][0]["email_subject"], "Outreach to Sundar")
        
        # Verify research plan was stored in state
        self.assertIn("research_plan", state)
        self.assertEqual(state["research_plan"]["linkedin_priority"], "medium")
        self.assertEqual(state["research_plan"]["web_priority"], "high")
        
        # Verify final Excel was saved
        excel_path = os.path.join(OUTPUT_DIR, f"campaign_{self.campaign_id}.xlsx")
        self.assertTrue(os.path.exists(excel_path))

    def test_pipeline_with_proofreader_rejection_and_retry(self):
        """
        Tests the self-correcting loop: proofreader rejects the first draft (score < 8),
        copywriter revises, proofreader approves the second draft.
        """
        self.mock_ai.generate_json.side_effect = [
            # OrchestratorAgent.analyze_prompt call
            {
                "research_focus": "Find service alignment",
                "linkedin_priority": "low",
                "web_priority": "high",
                "linkedin_search_queries": ["{name} {company} profile"],
                "web_search_queries": ["{company} services"],
                "email_angle": "Service partnership",
                "key_requirements": ["Reference specific services"],
                "tone_guidance": "Professional"
            },
            # Prospecting Agent
            {"name": "Test Person", "title": "CTO", "company": "TestCo", "key_interests": ["DevOps"], "career_highlights": ["Led migration"], "professional_summary": "CTO at TestCo."},
            # LinkedIn Agent
            {"linkedin_url": "https://linkedin.com/in/testperson", "linkedin_summary": "CTO at TestCo.", "linkedin_insights": ["Cloud expert"]},
            # Context Agent
            {"company_summary": "TestCo does cloud.", "recent_news": ["Cloud growth"], "pain_points": ["Scaling"], "talking_points": ["Cloud migration"], "custom_alignment": "Aligns with cloud services."},
            # Copywriter Agent (first draft)
            {"subject": "Generic subject", "body": "Generic body...", "personalization_hooks": ["Company name"]},
            # Proofreader Agent (rejects — score 6, below 7)
            {"approved": False, "relevance_score": 5, "tone_score": 7, "personalization_score": 5, "accuracy_score": 10, "score": 6, "critique": "Too generic. Needs specific service references.", "issues": ["Generic"]},
            # Copywriter Agent (revised draft)
            {"subject": "Cloud Partnership with TestCo", "body": "Hi Test, regarding your cloud migration...", "personalization_hooks": ["Cloud migration", "DevOps focus"]},
            # Proofreader Agent (approves — score 9, above 7)
            {"approved": True, "relevance_score": 9, "tone_score": 9, "personalization_score": 9, "accuracy_score": 10, "score": 9, "critique": "Much better. Well-personalized.", "issues": []}
        ]
        
        prospects = [{"name": "Test Person", "company": "TestCo", "title": "CTO", "email": "test@testco.com"}]
        settings = {
            "sender_name": "Mughees Tayyab",
            "sender_role": "Founder",
            "sender_company": "Outreach Node",
            "tone": "friendly",
            "goal": "partnership",
            "custom_prompt": "Offer cloud consulting services",
            "auto_generate_audio": False
        }
        
        StateManager.init_campaign(self.campaign_id, prospects, settings)
        orchestrator = Orchestrator(ai_client=self.mock_ai)
        orchestrator.run_campaign(self.campaign_id)
        
        state = StateManager.load_state(self.campaign_id)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["prospects"][0]["status"], "approved")
        self.assertEqual(state["prospects"][0]["proofread_score"], 9)
        # Verify the final email is the revised one
        self.assertEqual(state["prospects"][0]["email_subject"], "Cloud Partnership with TestCo")

    def test_pipeline_rate_limit_abort(self):
        """
        Tests that when a call fails with a rate limit error (429),
        the pipeline immediately terminates, marks campaign status as failed,
        and saves error_type as api_key_limit_reached.
        """
        # Mock the client call to raise an exception indicating rate limit
        self.mock_ai.generate_json.side_effect = Exception("ResourceExhausted: 429 Quota exceeded")

        prospects = [
            {"name": "Sundar Pichai", "company": "Google", "title": "CEO", "email": "sundar@google.com"},
            {"name": "Satya Nadella", "company": "Microsoft", "title": "CEO", "email": "satya@microsoft.com"}
        ]
        settings = {
            "sender_name": "Mughees Tayyab",
            "sender_role": "Founder",
            "sender_company": "Outreach Node",
            "tone": "friendly",
            "goal": "partnership",
            "custom_prompt": "Pitch drone monitoring",
            "auto_generate_audio": False
        }

        StateManager.init_campaign(self.campaign_id, prospects, settings)
        orchestrator = Orchestrator(ai_client=self.mock_ai)

        # Running should raise the exception due to our immediate re-raise
        with self.assertRaises(Exception) as context:
            orchestrator.run_campaign(self.campaign_id)

        self.assertIn("429", str(context.exception))

        # Check state saved
        state = StateManager.load_state(self.campaign_id)
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["error_type"], "api_key_limit_reached")
        self.assertIn("Rate Limit", state["error_message"])

if __name__ == '__main__':
    unittest.main()
