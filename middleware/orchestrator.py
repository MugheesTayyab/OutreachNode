import os
import logging
import time
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
    # Check for API key or rate limit indicators
    indicators = [
        "429", "resourceexhausted", "quota", "rate limit", 
        "limit exceeded", "api key", "api_key", "invalid key", "not valid",
        "api key not working", "limit reach"
    ]
    return any(ind in err_str for ind in indicators)

class Orchestrator:
    def __init__(self, ai_client: AIClient = None):
        self.ai_client = ai_client or AIClient()
        self.orchestrator_agent = OrchestratorAgent(self.ai_client)
        self.prospecting_agent = ProspectingAgent(self.ai_client)
        self.linkedin_agent = LinkedInAgent(self.ai_client)
        self.context_agent = ContextAgent(self.ai_client)
        self.copywriter_agent = CopywriterAgent(self.ai_client)
        self.proofreader_agent = ProofreaderAgent(self.ai_client)

    def run_campaign(self, campaign_id: str, callback_fn=None):
        """
        Runs the full multi-agent pipeline for all prospects in a campaign.
        Updates state in real-time.
        
        Flow:
        1. Orchestrator Agent analyzes the outreach prompt → research plan
        2. For each prospect:
           a. Prospecting Agent gathers profile info
           b. LinkedIn Agent (guided by research plan) gathers LinkedIn intelligence
           c. Context/Web Agent (guided by research plan) gathers company intelligence
           d. Copywriter Agent (guided by research plan) drafts a personalized email
           e. Proofreader Agent (guided by research plan) evaluates & loops if score ≤ 7
        """
        logger.info(f"Starting Campaign {campaign_id}...")
        state = StateManager.load_state(campaign_id)
        if not state:
            logger.error(f"Campaign {campaign_id} not found in state.")
            return
            
        settings = state.get("settings", {})
        prospects = state.get("prospects", [])
        
        # Mark campaign as running
        state["status"] = "running"
        StateManager.save_state(campaign_id, state)
        
        if callback_fn:
            callback_fn(campaign_id, "campaign_started", None)

        # ═══════════════════════════════════════════════════════════════
        # STEP 0: Orchestrator Agent — Analyze the outreach prompt
        # ═══════════════════════════════════════════════════════════════
        custom_prompt = settings.get("custom_prompt", "")
        research_plan = {}

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
                if callback_fn:
                    callback_fn(campaign_id, "campaign_failed", {"error": str(e)})
                raise e
            prompt_duration = round(time.time() - prompt_start, 1)

            # Store the research plan in state for visibility
            state["research_plan"] = research_plan
            state["orchestrator_duration"] = prompt_duration
            StateManager.save_state(campaign_id, state)

            logger.info(
                f"Orchestrator Agent completed in {prompt_duration}s. "
                f"LinkedIn priority: {research_plan.get('linkedin_priority')}, "
                f"Web priority: {research_plan.get('web_priority')}"
            )
        else:
            logger.info("No custom prompt provided. Skipping Orchestrator Agent analysis.")

        # ═══════════════════════════════════════════════════════════════
        # PROCESS EACH PROSPECT
        # ═══════════════════════════════════════════════════════════════
        completed_list = []

        for p in prospects:
            prospect_id = p["id"]
            logger.info(f"Processing prospect {prospect_id}: {p['name']}...")
            timeline = {"orchestrator": prompt_duration if custom_prompt else 0, "prospecting": 0, "linkedin": 0, "context": 0, "copywriting": 0, "proofreading": 0}
            
            try:
                # 1. Prospecting
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
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "prospect_data": prospect_data,
                    "agent_timeline": timeline
                })

                # 1b. LinkedIn Research (guided by research plan)
                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "linkedin"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "linkedin"})
                    
                linkedin_data = self.linkedin_agent.run(prospect_data, research_plan)
                timeline["linkedin"] = round(time.time() - start, 1)
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "linkedin_data": linkedin_data,
                    "agent_timeline": timeline
                })

                # 2. Context / Website Deep Search (guided by research plan)
                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "context"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "context"})
                    
                context_data = self.context_agent.run(prospect_data, linkedin_data, settings, research_plan)
                timeline["context"] = round(time.time() - start, 1)
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "context_data": context_data,
                    "agent_timeline": timeline
                })

                # 3. Copywriting & 4. Proofreading Loop (both guided by research plan)
                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "copywriting"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "copywriting"})
                    
                draft = self.copywriter_agent.run(prospect_data, linkedin_data, context_data, settings, research_plan)
                timeline["copywriting"] = round(time.time() - start, 1)
                StateManager.update_prospect(campaign_id, prospect_id, {"agent_timeline": timeline})
                
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
                        StateManager.update_prospect(campaign_id, prospect_id, {"agent_timeline": timeline})
                        attempts += 1
                    else:
                        break
                
                # Update with final draft results
                status = "approved" if approved else "rejected"
                
                # Check for autogen audio settings
                audio_path = ""
                if settings.get("auto_generate_audio", False) and approved:
                    StateManager.update_prospect(campaign_id, prospect_id, {"stage": "generating_audio"})
                    if callback_fn:
                        callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "generating_audio"})
                    
                    # Call TTS tool
                    audio_filename = f"audio_{campaign_id}_{prospect_id}.mp3"
                    audio_full_path = os.path.join("static", "audio", audio_filename)
                    # Use a short version of the body for the audio voicemail
                    audio_text = f"Hi {prospect_data['name']}. This is {settings.get('sender_name')} from {settings.get('sender_company')}. I sent you an email about your work at {prospect_data['company']}. Talk soon!"
                    generate_audio(audio_text, audio_full_path)
                    audio_path = f"/static/audio/{audio_filename}"

                # Update state
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
                    "audio_path": audio_path
                }
                StateManager.update_prospect(campaign_id, prospect_id, updates)
                
                # Retrieve the full prospect to compile Excel later
                p_updated = p.copy()
                p_updated.update(updates)
                p_updated["prospect_summary"] = prospect_data.get("professional_summary", "")
                p_updated["company_summary"] = context_data.get("company_summary", "")
                p_updated["recent_news"] = "\n".join(context_data.get("recent_news", []))
                p_updated["pain_points"] = "\n".join(context_data.get("pain_points", []))
                p_updated["linkedin_summary"] = linkedin_data.get("linkedin_summary", "")
                p_updated["custom_alignment"] = context_data.get("custom_alignment", "")
                completed_list.append(p_updated)
                
                if callback_fn:
                    callback_fn(campaign_id, "prospect_completed", {"id": prospect_id, "status": status})

            except Exception as e:
                logger.error(f"Pipeline error for prospect {prospect_id}: {str(e)}")
                
                # If API rate limit/key error, fail the campaign immediately
                if is_api_key_or_rate_limit_error(e):
                    state = StateManager.load_state(campaign_id)
                    if state:
                        state["status"] = "failed"
                        state["error_type"] = "api_key_limit_reached"
                        state["error_message"] = f"API Key or Rate Limit reached: {str(e)}"
                        StateManager.save_state(campaign_id, state)
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

        # Save Final Excel
        excel_path = os.path.join(OUTPUT_DIR, f"campaign_{campaign_id}.xlsx")
        write_excel(completed_list, excel_path)
        
        # Mark campaign as completed
        state = StateManager.load_state(campaign_id)
        state["status"] = "completed"
        StateManager.save_state(campaign_id, state)
        
        logger.info(f"Campaign {campaign_id} fully completed. Excel saved to {excel_path}.")
        if callback_fn:
            callback_fn(campaign_id, "campaign_completed", None)
