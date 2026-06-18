import os
import unittest
from unittest.mock import MagicMock
from middleware.orchestrator import Orchestrator
from middleware.state_manager import StateManager
from middleware.gemini_client import GeminiClient
from config.settings import OUTPUT_DIR

class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.campaign_id = "test_camp_123"
        self.mock_gemini = MagicMock(spec=GeminiClient)
        
    def tearDown(self):
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
            # Context Agent call
            {
                "company_summary": "Google is web giant.",
                "recent_news": ["AI updates"],
                "pain_points": ["Competition"],
                "talking_points": ["Congrats on Gemini 2.0"]
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
