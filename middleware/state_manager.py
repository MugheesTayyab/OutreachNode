import os
import json
import logging
import uuid
from config.settings import OUTPUT_DIR, TEMPLATES_DIR, SETTINGS_FILE, SUPPRESSED_FILE

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
        import datetime
        state = {
            "campaign_id": campaign_id,
            "status": "pending",
            "created_at": datetime.datetime.now().isoformat(),
            "settings": settings,
            "research_plan": {},
            "orchestrator_duration": 0,
            "current_stage": "pending",
            "total_tokens": 0,
            "total_cost": 0.0,
            "tags": settings.get("tags", ""),
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
                "stage": "pending",
                "prospect_data": {},
                "linkedin_data": {},
                "context_data": {},
                "email_subject": "",
                "email_body": "",
                "ab_variant": "",
                "proofread_score": 0,
                "proofread_critique": "",
                "relevance_score": 0,
                "tone_score": 0,
                "personalization_score": 0,
                "accuracy_score": 0,
                "email_sent": False,
                "audio_path": "",
                "status": "pending",
                "lead_score": 0,
                "follow_ups": [],
                "tags": ""
            })

        cls.save_state(campaign_id, state)
        return state

    @classmethod
    def update_prospect(cls, campaign_id: str, prospect_id: int, updates: dict):
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
                    avg_score = 0
                    scores = [p.get("proofread_score", 0) for p in state.get("prospects", []) if p.get("proofread_score", 0) > 0]
                    if scores:
                        avg_score = round(sum(scores) / len(scores), 1)
                    campaigns.append({
                        "campaign_id": campaign_id,
                        "status": state.get("status", "unknown"),
                        "total_prospects": total,
                        "completed_prospects": completed,
                        "avg_score": avg_score,
                        "tags": state.get("tags", ""),
                        "total_tokens": state.get("total_tokens", 0),
                        "total_cost": state.get("total_cost", 0.0),
                        "settings": state.get("settings", {}),
                        "created_at": state.get("created_at")
                    })
        return campaigns

    # ── Templates ──
    @classmethod
    def save_template(cls, name: str, config: dict) -> str:
        tid = str(uuid.uuid4())[:8]
        tmpl = {"id": tid, "name": name, "config": config}
        path = os.path.join(TEMPLATES_DIR, f"{tid}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(tmpl, f, indent=4)
        return tid

    @classmethod
    def load_template(cls, template_id: str) -> dict:
        path = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def list_templates(cls) -> list[dict]:
        templates = []
        if not os.path.exists(TEMPLATES_DIR):
            return templates
        for file in os.listdir(TEMPLATES_DIR):
            if file.endswith(".json"):
                path = os.path.join(TEMPLATES_DIR, file)
                with open(path, 'r', encoding='utf-8') as f:
                    tmpl = json.load(f)
                    templates.append({"id": tmpl.get("id"), "name": tmpl.get("name")})
        return templates

    @classmethod
    def delete_template(cls, template_id: str):
        path = os.path.join(TEMPLATES_DIR, f"{template_id}.json")
        if os.path.exists(path):
            os.remove(path)

    # ── Persistent Settings ──
    @classmethod
    def save_settings(cls, data: dict):
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_settings(cls) -> dict:
        if not os.path.exists(SETTINGS_FILE):
            return {}
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ── Suppression List ──
    @classmethod
    def is_suppressed(cls, email: str) -> bool:
        if not os.path.exists(SUPPRESSED_FILE):
            return False
        with open(SUPPRESSED_FILE, 'r', encoding='utf-8') as f:
            return email.strip().lower() in [line.strip().lower() for line in f]

    @classmethod
    def add_suppressed(cls, email: str):
        os.makedirs(os.path.dirname(SUPPRESSED_FILE), exist_ok=True)
        with open(SUPPRESSED_FILE, 'a', encoding='utf-8') as f:
            f.write(email.strip().lower() + '\n')

    @classmethod
    def list_suppressed(cls) -> list[str]:
        if not os.path.exists(SUPPRESSED_FILE):
            return []
        with open(SUPPRESSED_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    # ── Campaign Management ──
    @classmethod
    def delete_campaign(cls, campaign_id: str):
        path = cls._get_path(campaign_id)
        if os.path.exists(path):
            os.remove(path)
        excel_path = os.path.join(OUTPUT_DIR, f"campaign_{campaign_id}.xlsx")
        if os.path.exists(excel_path):
            os.remove(excel_path)

    @classmethod
    def clear_all_campaigns(cls):
        if not os.path.exists(OUTPUT_DIR):
            return
        for file in os.listdir(OUTPUT_DIR):
            if file.startswith("campaign_") and (file.endswith(".json") or file.endswith(".xlsx")):
                os.remove(os.path.join(OUTPUT_DIR, file))

    @classmethod
    def set_campaign_cancel_requested(cls, campaign_id: str):
        state = cls.load_state(campaign_id)
        if state:
            state["cancel_requested"] = True
            cls.save_state(campaign_id, state)

    @classmethod
    def clear_cancel_requested(cls, campaign_id: str):
        state = cls.load_state(campaign_id)
        if state:
            state.pop("cancel_requested", None)
            cls.save_state(campaign_id, state)
