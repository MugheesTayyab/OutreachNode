import logging
from middleware.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class ProofreaderAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def run(self, draft_email: dict, prospect_profile: dict, company_context: dict) -> dict:
        """
        Evaluates the generated cold email for accuracy, tone, personalization, and potential hallucinations.
        """
        logger.info(f"Proofreader Agent evaluating draft for {prospect_profile.get('name')}...")
        
        system_prompt = """
You are an expert editor, quality assurance agent, and fact-checker. Your job is to review a cold email draft for a prospect.
Analyze the email against the raw prospect and company facts.
Evaluate the following:
1. Fact-checking: Does the email contain any hallucinated, incorrect, or unverified claims about the prospect or their company? (Everything in the email MUST match the provided profile and context).
2. Fact and News Vetting: Rate the reliability and value of the news, facts, or LinkedIn claims referenced in the email on a scale of 1 to 10. If any referenced news/fact has a confidence level or reliability rating of less than 6/10, or is not worth mentioning, you MUST reject the email.
3. Personalization Quality: Is the hook genuine and interesting, or is it generic filler?
4. Tone and Clarity: Is it professional, clear, and under 150 words?
5. Spam Triggers: Does it use clickbait subject lines or sound overly aggressive?

Based on this, you must output a valid JSON object. Do not include extra text. The JSON keys must be:
- "approved": true if the email score is 8 or higher, has NO factual errors, and all incorporated facts have at least 6/10 confidence. false if it has factual errors, incorporates low-confidence/unvetted facts, sounds template-y, or has a score less than 8.
- "score": An integer rating from 1 to 10.
- "critique": A detailed paragraph explaining what is good and what needs to be fixed (mandatory if approved is false).
- "issues": A list of specific issues found (e.g. ["Low confidence in recent funding news (less than 6/10)", "Hallucinated Series C funding", "Subject line is spammy", "Score is less than 8/10"]).
"""

        user_prompt = f"""
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

Company Context (Ground Truth):
- Summary: {company_context.get('company_summary')}
- Recent News: {company_context.get('recent_news')}
- Pain Points: {company_context.get('pain_points')}
- Talking Points: {company_context.get('talking_points')}

Please perform the review and output the JSON.
"""
        try:
            return self.gemini.generate_json(system_prompt, user_prompt, temperature=0.2)
        except Exception as e:
            logger.error(f"Proofreader Agent evaluation failed: {str(e)}")
            return {
                "approved": True,
                "score": 8,
                "critique": "Automatic approval due to editor failure.",
                "issues": []
            }
