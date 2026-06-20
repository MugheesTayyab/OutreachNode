import os
import logging
import time
from config.settings import OUTPUT_DIR
from middleware.gemini_client import GeminiClient
from middleware.state_manager import StateManager
from agents.prospecting_agent import ProspectingAgent
from agents.linkedin_agent import LinkedInAgent
from agents.context_agent import ContextAgent
from agents.copywriter_agent import CopywriterAgent
from agents.proofreader_agent import ProofreaderAgent
from tools.excel_tool import write_excel
from tools.tts_tool import generate_audio

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, gemini_client: GeminiClient = None):
        self.gemini = gemini_client or GeminiClient()
        self.prospecting_agent = ProspectingAgent(self.gemini)
        self.linkedin_agent = LinkedInAgent(self.gemini)
        self.context_agent = ContextAgent(self.gemini)
        self.copywriter_agent = CopywriterAgent(self.gemini)
        self.proofreader_agent = ProofreaderAgent(self.gemini)

    def run_campaign(self, campaign_id: str, callback_fn=None):
        """
        Runs the full multi-agent pipeline for all prospects in a campaign.
        Updates state in real-time.
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

        completed_list = []

        for p in prospects:
            prospect_id = p["id"]
            logger.info(f"Processing prospect {prospect_id}: {p['name']}...")
            timeline = {"prospecting": 0, "linkedin": 0, "context": 0, "copywriting": 0, "proofreading": 0}
            
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

                # 1b. LinkedIn Research
                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "linkedin"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "linkedin"})
                    
                linkedin_data = self.linkedin_agent.run(prospect_data)
                timeline["linkedin"] = round(time.time() - start, 1)
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "linkedin_data": linkedin_data,
                    "agent_timeline": timeline
                })

                # 2. Context / Website Deep Search
                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "context"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "context"})
                    
                context_data = self.context_agent.run(prospect_data, linkedin_data, settings)
                timeline["context"] = round(time.time() - start, 1)
                StateManager.update_prospect(campaign_id, prospect_id, {
                    "context_data": context_data,
                    "agent_timeline": timeline
                })

                # 3. Copywriting & 4. Proofreading Loop
                start = time.time()
                StateManager.update_prospect(campaign_id, prospect_id, {"stage": "copywriting"})
                if callback_fn:
                    callback_fn(campaign_id, "prospect_update", {"id": prospect_id, "stage": "copywriting"})
                    
                draft = self.copywriter_agent.run(prospect_data, linkedin_data, context_data, settings)
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
                        
                    evaluation = self.proofreader_agent.run(draft, prospect_data, linkedin_data, context_data, settings)
                    
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
                        draft = self.copywriter_agent.revise(draft, critique, prospect_data, linkedin_data, context_data, settings)
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
