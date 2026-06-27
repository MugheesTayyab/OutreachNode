import os
import json
import logging
import time
import requests
from config.settings import OUTPUT_DIR
from middleware.ai_client import AIClient
from middleware.state_manager import StateManager
from agents.prospecting_agent import ProspectingAgent
from agents.linkedin_agent import LinkedInAgent
from agents.context_agent import ContextAgent
from agents.copywriter_agent import CopywriterAgent
from agents.proofreader_agent import ProofreaderAgent
from agents.orchestrator_agent import OrchestratorAgent
from tools.excel_tool import write_excel
from tools.tts_tool import generate_audio

logger = logging.getLogger(__name__)

def is_api_key_or_rate_limit_error(exception: Exception) -> bool:
    err_str = str(exception).lower()
    indicators = [
        "429", "resourceexhausted", "quota", "rate limit",
        "limit exceeded", "api key", "api_key", "invalid key", "not valid",
        "api key not working", "limit reach"
    ]
    return any(ind in err_str for ind in indicators)

def _fire_webhook(event: str, payload: dict):
    try:
        settings = StateManager.load_settings()
        webhook_url = settings.get("webhook_url", "")
        if webhook_url:
            requests.post(webhook_url, json={"event": event, "payload": payload}, timeout=10)
    except Exception as e:
        logger.warning(f"Webhook failed for {event}: {e}")

def _estimate_tokens(text: str) -> int:
    return max(1, len(str(text)) // 4)

class Orchestrator:
    def __init__(self, ai_client: AIClient = None):
        self.ai_client = ai_client or AIClient()
        self.orchestrator_agent = OrchestratorAgent(self.ai_client)
        self.prospecting_agent = ProspectingAgent(self.ai_client)
        self.linkedin_agent = LinkedInAgent(self.ai_client)
        self.context_agent = ContextAgent(self.ai_client)
        self.copywriter_agent = CopywriterAgent(self.ai_client)
        self.proofreader_agent = ProofreaderAgent(self.ai_client)

    def _is_cancelled(self, campaign_id: str) -> bool:
        state = StateManager.load_state(campaign_id)
        return state.get("cancel_requested", False) or state.get("status") in ("paused", "cancelled")

    def _check_pause(self, campaign_id: str) -> bool:
        """Returns True if campaign should continue, False if paused/cancelled."""
        state = StateManager.load_state(campaign_id)
        if state.get("cancel_requested"):
            state["status"] = "cancelled"
            state.pop("cancel_requested", None)
            StateManager.save_state(campaign_id, state)
            _fire_webhook("campaign.cancelled", {"campaign_id": campaign_id})
            logger.info(f"Campaign {campaign_id} cancelled.")
            return False
        if state.get("status") == "paused":
            logger.info(f"Campaign {campaign_id} paused. Waiting...")
            while True:
                time.sleep(5)
                state = StateManager.load_state(campaign_id)
                if state.get("cancel_requested"):
                    state["status"] = "cancelled"
                    state.pop("cancel_requested", None)
                    StateManager.save_state(campaign_id, state)
                    _fire_webhook("campaign.cancelled", {"campaign_id": campaign_id})
                    return False
                if state.get("status") == "running":
                    logger.info(f"Campaign {campaign_id} resumed.")
                    return True
        return True

    def run_campaign(self, campaign_id: str, callback_fn=None):
        logger.info(f"Starting Campaign {campaign_id}...")
        state = StateManager.load_state(campaign_id)
        if not state:
            logger.error(f"Campaign {campaign_id} not found in state.")
            return

        settings = state.get("settings", {})
        prospects = state.get("prospects", [])

        state["status"] = "running"
        StateManager.save_state(campaign_id, state)

        _fire_webhook("campaign.started", {"campaign_id": campaign_id})
        if callback_fn:
            callback_fn(campaign_id, "campaign_started", None)

        total_tokens = 0
        total_cost = 0.0

        custom_prompt = settings.get("custom_prompt", "")
        research_plan = {}
        prompt_duration = 0

        if custom_prompt:
            logger.info("Orchestrator Agent analyzing outreach prompt...")
            state["current_stage"] = "analyzing_prompt"
            StateManager.save_state(campaign_id, state)
            if callback_fn:
                callback_fn(campaign_id, "stage_update", {"stage": "analyzing_prompt"})

            prompt_start = time.time()
            try:
                research_plan = self.orchestrator_agent.analyze_prompt(custom_prompt, settings)
            except Exception as e:
                logger.error(f"Orchestrator Agent analysis failed: {str(e)}")
                state = StateManager.load_state(campaign_id)
                if state:
                    state["status"] = "failed"
                    if is_api_key_or_rate_limit_error(e):
                        state["error_type"] = "api_key_limit_reached"
                        state["error_message"] = f"API Key or Rate Limit reached: {str(e)}"
                    else:
                        state["error_type"] = "general_error"
                        state["error_message"] = str(e)
                    StateManager.save_state(campaign_id, state)
                _fire_webhook("campaign.failed", {"campaign_id": campaign_id, "error": str(e)})
                if callback_fn:
                    callback_fn(campaign_id, "campaign_failed", {"error": str(e)})
                raise e
            prompt_duration = round(time.time() - prompt_start, 1)
            state["research_plan"] = research_plan
            state["orchestrator_duration"] = prompt_duration
            StateManager.save_state(campaign_id, state)

            prompt_text = json.dumps(research_plan)
            total_tokens += len(prompt_text) // 4

        else:
            logger.info("No custom prompt provided. Skipping Orchestrator Agent analysis.")

        completed_list = []

        for p in prospects:
            prospect_id = p["id"]

            if self._is_cancelled(campaign_id):
                break
            if not self._check_pause(campaign_id):
                break

            logger.info(f"Processing prospect {prospect_id}: {p['name']}...")
            timeline = {"orchestrator": prompt_duration if custom_prompt else 0, "prospecting": 0, "linkedin": 0, "context": 0, "copywriting": 0, "proofreading": 0}

            try:
                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "stage": "prospecting",
                    "status": "processing",
                    "agent_timeline": timeline
                })
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "prospecting"})

                prospect_data = self.prospecting_agent.run(p)
                timeline["prospecting"] = round(time.time() - start, 1)
                total_tokens += _estimate_tokens(str(prospect_data))
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "prospect_data": prospect_data,
                    "agent_timeline": timeline
                })

                if not self._check_pause(campaign_id):
                    break

                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "linkedin"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "linkedin"})

                linkedin_data = self.linkedin_agent.run(prospect_data, research_plan)
                timeline["linkedin"] = round(time.time() - start, 1)
                total_tokens += _estimate_tokens(str(linkedin_data))
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "linkedin_data": linkedin_data,
                    "agent_timeline": timeline
                })

                if not self._check_pause(campaign_id):
                    break

                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "context"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "context"})

                context_data = self.context_agent.run(prospect_data, linkedin_data, settings, research_plan)
                timeline["context"] = round(time.time() - start, 1)
                total_tokens += _estimate_tokens(str(context_data))
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "context_data": context_data,
                    "agent_timeline": timeline
                })

                if not self._check_pause(campaign_id):
                    break

                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "copywriting"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "copywriting"})

                calendly_url = StateManager.load_settings().get("calendly_url", "")
                draft = self.copywriter_agent.run(prospect_data, linkedin_data, context_data, settings, research_plan, calendly_url=calendly_url)
                timeline["copywriting"] = round(time.time() - start, 1)
                total_tokens += _estimate_tokens(str(draft))

                ab_variant = "A"
                if settings.get("ab_test") and research_plan:
                    ab_variant = "A" if prospect_id % 2 == 0 else "B"

                StateManager.update_prospect(campaign_id, prospect_id, {"ab_variant": ab_variant, "agent_timeline": timeline})

                attempts = 1
                max_attempts = 3
                approved = False
                score = 0
                critique = ""
                proof_durations = []

                while attempts <= max_attempts and not approved:
                    attempt_start = time.time()
                    StateManager.update_prospect(campaign_id, prospect_id, {
                        "stage": f"proofreading_attempt_{attempts}",
                        "email_subject": draft.get("subject", ""),
                        "email_body": draft.get("body", "")
                    })
                    if callback_fn:
                        callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": f"proofreading_attempt_{attempts}"})

                    evaluation = self.proofreader_agent.run(draft, prospect_data, linkedin_data, context_data, settings, research_plan)

                    approved = evaluation.get("approved", False)
                    score = evaluation.get("score", 0)
                    critique = evaluation.get("critique", "")

                    total_tokens += _estimate_tokens(str(evaluation))

                    logger.info(
                        f"Proofreader Evaluation (Attempt {attempts}): Score={score}, Approved={approved}, "
                        f"Sub-scores: Relevance={evaluation.get('relevance_score')}/10, Tone={evaluation.get('tone_score')}/10, "
                        f"Personalization={evaluation.get('personalization_score')}/10, Accuracy={evaluation.get('accuracy_score')}/10"
                    )

                    proof_durations.append(round(time.time() - attempt_start, 1))
                    timeline["proofreading"] = round(sum(proof_durations), 1)
                    StateManager.update_prospect(campaign_id, prospect_id, {"agent_timeline": timeline})

                    if not approved and attempts < max_attempts:
                        logger.info(f"Draft rejected (Score: {score}). Revising (Attempt {attempts + 1})...")
                        copy_start = time.time()
                        draft = self.copywriter_agent.revise(draft, critique, prospect_data, linkedin_data, context_data, settings, research_plan)
                        timeline["copywriting"] = round(timeline["copywriting"] + (time.time() - copy_start), 1)
                        total_tokens += _estimate_tokens(str(draft))
                        StateManager.update_prospect(campaign_id, prospect_id, {"agent_timeline": timeline})
                        attempts += 1
                    else:
                        break

                status = "approved" if approved else "rejected"

                audio_path = ""
                if settings.get("auto_generate_audio", False) and approved:
                    StateManager.update_prospect(campaign_id, prospect_id, {"stage": "generating_audio"})
                    if callback_fn:
                        callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "generating_audio"})
                    audio_filename = f"audio_{campaign_id}_{prospect_id}.mp3"
                    audio_full_path = os.path.join("static", "audio", audio_filename)
                    audio_text = f"Hi {prospect_data['name']}. This is {settings.get('sender_name')} from {settings.get('sender_company')}. I sent you an email about your work at {prospect_data['company']}. Talk soon!"
                    generate_audio(audio_text, audio_full_path)
                    audio_path = f"/static/audio/{audio_filename}"

                lead_score = self._compute_lead_score(prospect_data, linkedin_data, context_data, score)

                updates = {
                    "stage": "completed",
                    "email_subject": draft.get("subject", ""),
                    "email_body": draft.get("body", ""),
                    "proofread_score": score,
                    "proofread_critique": critique,
                    "relevance_score": evaluation.get("relevance_score", 0),
                    "tone_score": evaluation.get("tone_score", 0),
                    "personalization_score": evaluation.get("personalization_score", 0),
                    "accuracy_score": evaluation.get("accuracy_score", 0),
                    "status": status,
                    "audio_path": audio_path,
                    "lead_score": lead_score
                }
                StateManager.update_prospect(campaign_id, prospect_id, updates)

                p_updated = p.copy()
                p_updated.update(updates)
                p_updated["prospect_summary"] = prospect_data.get("professional_summary", "")
                p_updated["company_summary"] = context_data.get("company_summary", "")
                p_updated["recent_news"] = "\n".join(context_data.get("recent_news", []))
                p_updated["pain_points"] = "\n".join(context_data.get("pain_points", []))
                p_updated["linkedin_summary"] = linkedin_data.get("linkedin_summary", "")
                p_updated["custom_alignment"] = context_data.get("custom_alignment", "")
                completed_list.append(p_updated)

                _fire_webhook("prospect.completed", {"campaign_id": campaign_id, "prospect_id": prospect_id, "status": status})

                if callback_fn:
                    callback_fn(campaign_id, "prospect_completed", {"id": prospect_id, "status": status})

            except Exception as e:
                logger.error(f"Pipeline error for prospect {prospect_id}: {str(e)}")
                if is_api_key_or_rate_limit_error(e):
                    state = StateManager.load_state(campaign_id)
                    if state:
                        state["status"] = "failed"
                        state["error_type"] = "api_key_limit_reached"
                        state["error_message"] = f"API Key or Rate Limit reached: {str(e)}"
                        StateManager.save_state(campaign_id, state)
                    _fire_webhook("campaign.failed", {"campaign_id": campaign_id, "error": str(e)})
                    if callback_fn:
                        callback_fn(campaign_id, "campaign_failed", {"error": str(e)})
                    raise e

                updates = {
                    "stage": "failed",
                    "status": "failed",
                    "proofread_critique": f"Pipeline failed: {str(e)}"
                }
                StateManager.update_prospect(campaign_id, prospect_id, updates)

                p_failed = p.copy()
                p_failed.update(updates)
                completed_list.append(p_failed)

                if callback_fn:
                    callback_fn(campaign_id, "prospect_failed", {"id": prospect_id})

        total_cost = round(total_tokens / 1000 * 0.015, 4)
        state = StateManager.load_state(campaign_id)
        state["total_tokens"] = total_tokens
        state["total_cost"] = total_cost
        StateManager.save_state(campaign_id, state)

        excel_path = os.path.join(OUTPUT_DIR, f"campaign_{campaign_id}.xlsx")
        write_excel(completed_list, excel_path)

        state = StateManager.load_state(campaign_id)
        if state.get("status") not in ("cancelled", "failed"):
            state["status"] = "completed"
        StateManager.save_state(campaign_id, state)

        logger.info(f"Campaign {campaign_id} completed. Tokens: {total_tokens}, Cost: ${total_cost}. Excel saved to {excel_path}.")
        _fire_webhook("campaign.completed", {"campaign_id": campaign_id, "total_tokens": total_tokens, "total_cost": total_cost})
        if callback_fn:
            callback_fn(campaign_id, "campaign_completed", None)

    def _compute_lead_score(self, prospect_data: dict, linkedin_data: dict, context_data: dict, proofread_score: int) -> int:
        score = 50
        if proofread_score >= 8:
            score += 15
        elif proofread_score >= 6:
            score += 5
        if prospect_data.get("professional_summary"):
            score += 10
        if linkedin_data.get("linkedin_insights"):
            score += 10
        if context_data.get("recent_news"):
            score += 10
        if context_data.get("pain_points"):
            score += 5
        return min(score, 100)
