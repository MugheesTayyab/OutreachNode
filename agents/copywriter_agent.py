import logging
from middleware.ai_client import AIClient

logger = logging.getLogger(__name__)

class CopywriterAgent:
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client

    def run(self, prospect_profile: dict, linkedin_data: dict, company_context: dict, campaign_settings: dict, research_plan: dict = None, calendly_url: str = "") -> dict:
        """
        Generates a highly personalized cold email draft.
        When a research_plan is provided, uses its email_angle and key_requirements
        to ensure the email directly addresses the outreach prompt.
        """
        research_plan = research_plan or {}
        email_angle = research_plan.get("email_angle", "")
        key_requirements = research_plan.get("key_requirements", [])
        tone_guidance = research_plan.get("tone_guidance", "")
        original_prompt = research_plan.get("original_prompt", "")

        logger.info(f"Copywriter Agent generating email for {prospect_profile.get('name')} at {prospect_profile.get('company')}...")

        # Build key requirements block for the system prompt
        key_req_section = ""
        if key_requirements:
            key_req_section = "\n\nCRITICAL — The email MUST satisfy these requirements from the outreach strategy:\n"
            for i, req in enumerate(key_requirements, 1):
                key_req_section += f"  {i}. {req}\n"

        # Build email angle guidance
        angle_section = ""
        if email_angle:
            angle_section = f"\n\nEMAIL ANGLE (from strategy): {email_angle}\nYou MUST use this angle as the core approach for the email.\n"

        # Build tone guidance
        tone_section = ""
        if tone_guidance:
            tone_section = f"\n\nTONE GUIDANCE (from strategy): {tone_guidance}\n"

        calendly_section = ""
        if calendly_url:
            calendly_section = f"\n\nCALENDLY LINK: {calendly_url}\nYou may optionally suggest the prospect book a time directly using this link in the CTA.\n"

        system_prompt = f"""
You are a world-class B2B copywriter specializing in highly personalized, high-converting cold outreach designed to help business developers find clients, and students or job seekers find career opportunities.
Your task is to write a short, compelling, and professional cold email.

Outreach Purpose & Strategy:
- For Business Development / Finding Clients: Focus on how your service/product specifically addresses a service gap, pain point, or growth initiative identified on their website.
- For Job Seekers / Students: Focus on demonstrating genuine knowledge of their projects/tech stack, expressing admiration for their engineering/design culture, and suggesting how you can contribute.
- Length: Keep it brief (under 150 words, ideally 3-5 sentences). Be direct and respect their time.
- Hook: Open with a highly personalized comment or congratulations based on their LinkedIn profile/insights or company news/website research. Never say "Hope this email finds you well" or "My name is...".
- Objective: Draft the email to specifically satisfy the user's custom outreach prompt/objective.
- Value: Concisely connect the company's specific services or website details with your value proposition, showing how you can benefit them.
- Unique Personalization: DO NOT reuse the same structure or phrases for different companies. Each email must feel completely handcrafted, logical, and unique to the specific prospect.
- CTA: Include a low-friction, single call to action (e.g. "Do you have 5 minutes for a quick chat next Tuesday?" or "Would you be open to a brief chat about upcoming projects?").
- Tone: Match the tone requested by the user.
{angle_section}{key_req_section}{tone_section}{calendly_section}
Output a valid JSON object. Do not include any extra text. The JSON keys must be:
- "subject": A catchy, personalized subject line (no spammy clickbait).
- "subject_b": An alternative subject line (A/B variant B) — different angle or hook from subject A.
- "body": The full body of the email.
- "personalization_hooks": A list of the specific facts, news, or LinkedIn details you incorporated to make it personalized.
"""

        user_prompt = f"""
Prospect Profile:
- Name: {prospect_profile.get('name')}
- Title: {prospect_profile.get('title')}
- Company: {prospect_profile.get('company')}
- Key Interests: {prospect_profile.get('key_interests')}
- Career Highlights: {prospect_profile.get('career_highlights')}
- Professional Summary: {prospect_profile.get('professional_summary')}

LinkedIn Insights:
- URL: {linkedin_data.get('linkedin_url')}
- Summary: {linkedin_data.get('linkedin_summary')}
- Specific Insights: {linkedin_data.get('linkedin_insights')}

Company Context & Website Research:
- Summary: {company_context.get('company_summary')}
- Recent News: {company_context.get('recent_news')}
- Pain Points: {company_context.get('pain_points')}
- Talking Points: {company_context.get('talking_points')}
- Website Alignment with Outreach Objective: {company_context.get('custom_alignment')}

Campaign Settings:
- Sender Name: {campaign_settings.get('sender_name', 'Mughees Tayyab')}
- Sender Role: {campaign_settings.get('sender_role', 'Founder')}
- Sender Company: {campaign_settings.get('sender_company', 'Outreach Node')}
- Tone: {campaign_settings.get('tone', 'friendly')} (options: formal, friendly, bold)
- Goal: {campaign_settings.get('goal', 'partnership')} (options: meeting, demo, partnership)
- Outreach Prompt / Custom Objective: {original_prompt or campaign_settings.get('custom_prompt', 'Introduce our services and suggest a brief call.')}

Write the email and output the JSON.
"""
        try:
            return self.ai_client.generate_json(system_prompt, user_prompt, temperature=0.7)
        except Exception as e:
            logger.error(f"Copywriter Agent generation failed: {str(e)}")
            from middleware.orchestrator import is_api_key_or_rate_limit_error
            if is_api_key_or_rate_limit_error(e):
                raise e
            return {
                "subject": f"Quick question regarding {prospect_profile.get('company')} growth",
                "subject_b": f"Thoughts on {prospect_profile.get('company')}'s recent work?",
                "body": f"Hi {prospect_profile.get('name')},\n\nI've been following {prospect_profile.get('company')}'s updates recently, especially your work as {prospect_profile.get('title')}.\n\nHere at {campaign_settings.get('sender_company')}, we help companies address core efficiency goals. I'd love to connect and see if we can support your initiatives.\n\nDo you have a few minutes for a quick call next week?\n\nBest regards,\n\n{campaign_settings.get('sender_name')}\n{campaign_settings.get('sender_role')}, {campaign_settings.get('sender_company')}",
                "personalization_hooks": ["Job title", "Company name"]
            }

    def revise(self, original_draft: dict, critique: str, prospect_profile: dict, linkedin_data: dict, company_context: dict, campaign_settings: dict, research_plan: dict = None) -> dict:
        """
        Revises the cold email draft incorporating feedback from the Proofreader Agent.
        Uses the research_plan to maintain alignment with the outreach prompt during revision.
        """
        research_plan = research_plan or {}
        email_angle = research_plan.get("email_angle", "")
        key_requirements = research_plan.get("key_requirements", [])
        original_prompt = research_plan.get("original_prompt", "")

        logger.info(f"Copywriter Agent revising draft based on critique: '{critique}'")

        # Build key requirements reminder for revision
        key_req_reminder = ""
        if key_requirements:
            key_req_reminder = "\n\nREMINDER — The revised email MUST satisfy these outreach requirements:\n"
            for i, req in enumerate(key_requirements, 1):
                key_req_reminder += f"  {i}. {req}\n"

        system_prompt = f"""
You are a world-class B2B copywriter. You have been given an email draft that was REJECTED by a proofreader/editor.
Your job is to revise the email draft to fully address the critique while keeping the email engaging, brief, and personalized.
Make sure you leverage the LinkedIn profile info and deep company website alignment to make the email uniquely fit this prospect.
{"EMAIL ANGLE to maintain: " + email_angle if email_angle else ""}
{key_req_reminder}
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

LinkedIn Insights:
- URL: {linkedin_data.get('linkedin_url')}
- Summary: {linkedin_data.get('linkedin_summary')}
- Specific Insights: {linkedin_data.get('linkedin_insights')}

Company Context:
- Summary: {company_context.get('company_summary')}
- Talking Points: {company_context.get('talking_points')}
- Website Alignment with Outreach Objective: {company_context.get('custom_alignment')}

Campaign Settings:
- Sender Name: {campaign_settings.get('sender_name')}
- Sender Role: {campaign_settings.get('sender_role')}
- Sender Company: {campaign_settings.get('sender_company')}
- Outreach Prompt / Custom Objective: {original_prompt or campaign_settings.get('custom_prompt', 'Introduce our services.')}

Please revise the email to address all points in the critique. Output the clean JSON.
"""
        try:
            return self.ai_client.generate_json(system_prompt, user_prompt, temperature=0.5)
        except Exception as e:
            logger.error(f"Copywriter Agent revision failed: {str(e)}")
            from middleware.orchestrator import is_api_key_or_rate_limit_error
            if is_api_key_or_rate_limit_error(e):
                raise e
            return original_draft
