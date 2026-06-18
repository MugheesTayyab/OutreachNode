import logging
from middleware.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class CopywriterAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def run(self, prospect_profile: dict, company_context: dict, campaign_settings: dict) -> dict:
        """
        Generates a highly personalized cold email draft.
        """
        logger.info(f"Copywriter Agent generating email for {prospect_profile.get('name')} at {prospect_profile.get('company')}...")
        
        system_prompt = """
You are a world-class B2B copywriter specializing in highly personalized, high-converting cold outreach.
Your task is to write a short, compelling, and professional cold email.
Guidelines:
- Length: Keep it brief (under 150 words).
- Hook: Open with a highly personalized comment or congratulations based on their profile or company news. Avoid generic templates.
- Objective: You must draft the email to specifically satisfy the user's custom outreach prompt/objective.
- Value: Clearly and concisely state the value proposition or how you can solve a likely pain point.
- CTA: Include a low-friction, single call to action (e.g. "Do you have 5 minutes for a quick chat next Tuesday?").
- Tone: Match the tone requested by the user.
- Formatting: Use clean spacing. Use brackets like [Sender Name] for placeholders only if you don't have the sender info.

Output a valid JSON object. Do not include any extra text. The JSON keys must be:
- "subject": A catchy, personalized subject line (no spammy clickbait).
- "body": The full body of the email.
- "personalization_hooks": A list of the specific facts or news you incorporated to make it personalized.
"""

        user_prompt = f"""
Prospect Profile:
- Name: {prospect_profile.get('name')}
- Title: {prospect_profile.get('title')}
- Company: {prospect_profile.get('company')}
- Key Interests: {prospect_profile.get('key_interests')}
- Career Highlights: {prospect_profile.get('career_highlights')}
- Professional Summary: {prospect_profile.get('professional_summary')}

Company Context:
- Summary: {company_context.get('company_summary')}
- Recent News: {company_context.get('recent_news')}
- Pain Points: {company_context.get('pain_points')}
- Talking Points: {company_context.get('talking_points')}

Campaign Settings:
- Sender Name: {campaign_settings.get('sender_name', 'Mughees Tayyab')}
- Sender Role: {campaign_settings.get('sender_role', 'Founder')}
- Sender Company: {campaign_settings.get('sender_company', 'GreenFactor')}
- Tone: {campaign_settings.get('tone', 'friendly')} (options: formal, friendly, bold)
- Goal: {campaign_settings.get('goal', 'partnership')} (options: meeting, demo, partnership)
- Outreach Prompt / Custom Objective: {campaign_settings.get('custom_prompt', 'Introduce our services and suggest a brief call.')}

Write the email and output the JSON.
"""
        try:
            return self.gemini.generate_json(system_prompt, user_prompt, temperature=0.7)
        except Exception as e:
            logger.error(f"Copywriter Agent generation failed: {str(e)}")
            return {
                "subject": f"Quick question regarding {prospect_profile.get('company')} growth",
                "body": f"Hi {prospect_profile.get('name')},\n\nI've been following {prospect_profile.get('company')}'s updates recently, especially your work as {prospect_profile.get('title')}.\n\nHere at {campaign_settings.get('sender_company')}, we help companies address core efficiency goals. I'd love to connect and see if we can support your initiatives.\n\nDo you have a few minutes for a quick call next week?\n\nBest regards,\n\n{campaign_settings.get('sender_name')}\n{campaign_settings.get('sender_role')}, {campaign_settings.get('sender_company')}",
                "personalization_hooks": ["Job title", "Company name"]
            }

    def revise(self, original_draft: dict, critique: str, prospect_profile: dict, company_context: dict, campaign_settings: dict) -> dict:
        """
        Revises the cold email draft incorporating feedback from the Proofreader Agent.
        """
        logger.info(f"Copywriter Agent revising draft based on critique: '{critique}'")
        
        system_prompt = """
You are a world-class B2B copywriter. You have been given an email draft that was REJECTED by a proofreader/editor.
Your job is to revise the email draft to fully address the critique while keeping the email engaging, brief, and personalized.
You must output a valid JSON object. Do not include any extra text. The JSON keys must be:
- "subject": The revised subject line.
- "body": The revised body of the email.
- "personalization_hooks": A list of the specific facts or news you incorporated.
"""

        user_prompt = f"""
Original Draft:
Subject: {original_draft.get('subject')}
Body: {original_draft.get('body')}

Proofreader Critique:
{critique}

Prospect Details:
- Name: {prospect_profile.get('name')}
- Title: {prospect_profile.get('title')}
- Company: {prospect_profile.get('company')}
- Key Interests: {prospect_profile.get('key_interests')}

Company Context:
- Summary: {company_context.get('company_summary')}
- Talking Points: {company_context.get('talking_points')}

Campaign Settings:
- Sender Name: {campaign_settings.get('sender_name')}
- Sender Role: {campaign_settings.get('sender_role')}
- Sender Company: {campaign_settings.get('sender_company')}
- Outreach Prompt / Custom Objective: {campaign_settings.get('custom_prompt', 'Introduce our services.')}

Please revise the email to address all points in the critique. Output the clean JSON.
"""
        try:
            return self.gemini.generate_json(system_prompt, user_prompt, temperature=0.5)
        except Exception as e:
            logger.error(f"Copywriter Agent revision failed: {str(e)}")
            return original_draft
