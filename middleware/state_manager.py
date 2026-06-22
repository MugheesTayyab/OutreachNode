import os
import json
import logging
from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)

class StateManager:
    @staticmethod
    def _get_path(campaign_id: str) -> str:
        return os.path.join(OUTPUT_DIR, f"campaign_{campaign_id}.json")

    @classmethod
    def save_state(cls, campaign_id: str, state: dict):
        try:
            filepath = cls._get_path(campaign_id)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state for campaign {campaign_id}: {str(e)}")

    @classmethod
    def load_state(cls, campaign_id: str) -> dict:
        filepath = cls._get_path(campaign_id)
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state for campaign {campaign_id}: {str(e)}")
            return {}

    @classmethod
    def init_campaign(cls, campaign_id: str, prospects: list[dict], settings: dict) -> dict:
        """
        Initializes a campaign structure in state.
        """
        state = {
            "campaign_id": campaign_id,
            "status": "pending",
            "settings": settings,
            "research_plan": {},
            "orchestrator_duration": 0,
            "current_stage": "pending",
            "prospects": []
        }
        
        for idx, p in enumerate(prospects):
            state["prospects"].append({
                "id": idx,
                "name": p.get("name", ""),
                "email": p.get("email", ""),
                "company": p.get("company", ""),
                "title": p.get("title", ""),
                "linkedin_url": p.get("linkedin_url", ""),
                "stage": "pending",  # pending, prospecting, context, copywriting, proofreading, approved, rejected, failed
                "prospect_data": {},
                "context_data": {},
                "email_subject": "",
                "email_body": "",
                "proofread_score": 0,
                "proofread_critique": "",
                "email_sent": False,
                "audio_path": "",
                "status": "pending"
            })
            
        cls.save_state(campaign_id, state)
        return state

    @classmethod
    def update_prospect(cls, campaign_id: str, prospect_id: int, updates: dict):
        """
        Update fields on a specific prospect in a campaign.
        """
        state = cls.load_state(campaign_id)
        if not state:
            return
            
        for p in state.get("prospects", []):
            if p["id"] == prospect_id:
                p.update(updates)
                break
                
        cls.save_state(campaign_id, state)
        
    @classmethod
    def list_campaigns(cls) -> list[dict]:
        """
        List all saved campaign summaries.
        """
        campaigns = []
        if not os.path.exists(OUTPUT_DIR):
            return []
            
        for file in os.listdir(OUTPUT_DIR):
            if file.startswith("campaign_") and file.endswith(".json"):
                campaign_id = file.replace("campaign_", "").replace(".json", "")
                state = cls.load_state(campaign_id)
                if state:
                    total = len(state.get("prospects", []))
                    completed = sum(1 for p in state.get("prospects", []) if p["status"] in ["completed", "approved", "sent"])
                    campaigns.append({
                        "campaign_id": campaign_id,
                        "status": state.get("status", "unknown"),
                        "total_prospects": total,
                        "completed_prospects": completed,
                        "settings": state.get("settings", {})
                    })
        return campaigns
