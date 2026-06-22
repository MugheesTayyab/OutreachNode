import logging
from middleware.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class ProofreaderAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def run(self, draft_email: dict, prospect_profile: dict, linkedin_data: dict, company_context: dict, campaign_settings: dict = None, research_plan: dict = None) -> dict:
        """
        Evaluates the generated cold email for accuracy, tone, personalization,
        relevance to outreach prompt, and potential hallucinations.
        
        When a research_plan is provided, uses its email_angle and key_requirements
        as additional evaluation criteria to judge if the email truly addresses
        the user's outreach prompt.
        """
        logger.info(f"Proofreader Agent evaluating draft for {prospect_profile.get('name')}...")
        
        campaign_settings = campaign_settings or {}
        research_plan = research_plan or {}
        custom_prompt = campaign_settings.get("custom_prompt", "Introduce our services and suggest a brief call.")
        expected_tone = campaign_settings.get("tone", "friendly")
        
        # Extract orchestrator guidance for stricter evaluation
        email_angle = research_plan.get("email_angle", "")
        key_requirements = research_plan.get("key_requirements", [])
        original_prompt = research_plan.get("original_prompt", custom_prompt)
        tone_guidance = research_plan.get("tone_guidance", "")
        
        # Build key requirements evaluation criteria
        key_req_section = ""
        if key_requirements:
            key_req_section = "\n\nADDITIONAL EVALUATION CRITERIA — The outreach strategy requires the email to:\n"
            for i, req in enumerate(key_requirements, 1):
                key_req_section += f"  {i}. {req}\n"
            key_req_section += "If the email fails to address any of these requirements, lower the relevance_score accordingly.\n"

        # Build angle check
        angle_section = ""
        if email_angle:
            angle_section = f"\n\nEXPECTED EMAIL ANGLE: {email_angle}\nCheck whether the email actually uses this angle. If it diverges significantly, lower the relevance_score.\n"
        
        system_prompt = f"""
You are an expert editor, quality assurance agent, and strict business communication fact-checker.
Your job is to perform a rigorous multi-dimensional validation of a cold outreach email draft against the ground truth facts and settings.

You must evaluate the following four dimensions and assign an integer score (1 to 10) for each:
1. Relevance to Outreach Objective (relevance_score): Does the email directly address the user's specific outreach prompt/objective (e.g. job application, client pitch, partnership)? Is the connection to the prospect's company logical and compelling? Reject generic or irrelevant pitches.
2. Tone Match (tone_score): Does the email body match the requested tone ({expected_tone})? {"Additional tone guidance: " + tone_guidance if tone_guidance else ""}
3. Personalization Quality (personalization_score): Does the email naturally weave in specific, high-value facts from the company website research and LinkedIn insights? Or does it sound like a generic copy-paste template with swapped names?
4. Factual Accuracy (accuracy_score): Does the email contain any hallucinated, unverified, or incorrect claims about the prospect, their LinkedIn details, or their company? Any unverified detail gets a lower accuracy score.
{angle_section}{key_req_section}
Approval Rules:
- The overall score (score) is the average of these 4 sub-scores (rounded to the nearest integer).
- The email is approved (approved = true) ONLY if:
  a) The overall score is 8 or higher (above 7/10).
  b) Factual Accuracy (accuracy_score) is 10/10 (absolutely NO factual errors or hallucinations).
  c) Relevance to Outreach Objective (relevance_score) is 8/10 or higher.
  d) Personalization Quality (personalization_score) is 8/10 or higher.
- If ANY of these conditions fail, approved MUST be set to false.

Output a valid JSON object. Do not include extra text outside the JSON. The JSON keys must be:
- "approved": true/false
- "relevance_score": integer (1-10)
- "tone_score": integer (1-10)
- "personalization_score": integer (1-10)
- "accuracy_score": integer (1-10)
- "score": overall score (1-10)
- "critique": a detailed paragraph explaining what is good and what MUST be fixed (mandatory, especially if approved is false).
- "issues": a list of specific issues found (e.g. ["Did not mention the job seeking intent", "Falsely claimed they won an award", "Tone is too formal for friendly settings"]).
"""

        user_prompt = f"""
Campaign Settings (Target Settings):
- Requested Tone: {expected_tone}
- Outreach Objective / Custom Prompt: {original_prompt}

Email Draft:
Subject: {draft_email.get('subject')}
Body: {draft_email.get('body')}

Prospect Profile (Ground Truth):
- Name: {prospect_profile.get('name')}
- Title: {prospect_profile.get('title')}
- Company: {prospect_profile.get('company')}
- Key Interests: {prospect_profile.get('key_interests')}
- Career Highlights: {prospect_profile.get('career_highlights')}
- Professional Summary: {prospect_profile.get('professional_summary')}

LinkedIn Insights (Ground Truth):
- URL: {linkedin_data.get('linkedin_url')}
- Summary: {linkedin_data.get('linkedin_summary')}
- Insights: {linkedin_data.get('linkedin_insights')}

Company Context (Ground Truth):
- Summary: {company_context.get('company_summary')}
- Recent News: {company_context.get('recent_news')}
- Pain Points: {company_context.get('pain_points')}
- Talking Points: {company_context.get('talking_points')}
- Website Alignment: {company_context.get('custom_alignment')}

Please perform the review and output the JSON.
"""
        try:
            res = self.gemini.generate_json(system_prompt, user_prompt, temperature=0.2)
            # Guarantee structure
            res["approved"] = res.get("approved", False)
            res["score"] = res.get("score", 5)
            return res
        except Exception as e:
            logger.error(f"Proofreader Agent evaluation failed: {str(e)}")
            from middleware.orchestrator import is_api_key_or_rate_limit_error
            if is_api_key_or_rate_limit_error(e):
                raise e
            return {
                "approved": False,
                "relevance_score": 5,
                "tone_score": 5,
                "personalization_score": 5,
                "accuracy_score": 5,
                "score": 5,
                "critique": f"Evaluation error: {str(e)}",
                "issues": [f"Evaluation error: {str(e)}"]
            }
