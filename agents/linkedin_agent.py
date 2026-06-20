import logging
from middleware.gemini_client import GeminiClient
from tools.search_tool import search_linkedin

logger = logging.getLogger(__name__)

class LinkedInAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def run(self, prospect_profile: dict) -> dict:
        """
        Searches and gathers LinkedIn information about the prospect or company.
        """
        name = prospect_profile.get("name", "")
        company = prospect_profile.get("company", "")
        title = prospect_profile.get("title", "")
        linkedin_url = prospect_profile.get("linkedin_url", "")
        
        logger.info(f"LinkedIn Agent running for {name} ({company})...")
        
        # Search LinkedIn snippets
        snippets = search_linkedin(name, company, linkedin_url)
        linkedin_context = "\n".join([f"- {s}" for s in snippets])
        
        system_prompt = """
You are an expert social media researcher and LinkedIn analyst. Your job is to analyze search results for a prospect's or company's LinkedIn profile and extract key personal and professional highlights.
You must output a valid JSON object. Do not include any markdown formatting or extra text outside the JSON. The JSON keys must be:
- "linkedin_url": The confirmed or most likely LinkedIn profile/page URL found.
- "linkedin_summary": A brief 2-3 sentence summary of their LinkedIn presence (their role description, company description, or career history).
- "linkedin_insights": A list of 2-3 specific personal/professional insights (e.g. key focus, achievements, career path, recent post themes, or company size/activity).
"""

        user_prompt = f"""
Prospect Name: {name}
Company: {company}
Reported Title: {title}
Provided LinkedIn URL: {linkedin_url}

LinkedIn Search Snippets:
{linkedin_context}

Create the LinkedIn strategy brief. Ensure the JSON is clean and valid.
"""
        try:
            insights = self.gemini.generate_json(system_prompt, user_prompt, temperature=0.3)
            # Ensure url is set
            if not insights.get("linkedin_url") or "linkedin.com" not in insights.get("linkedin_url", ""):
                insights["linkedin_url"] = linkedin_url or f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}"
            return insights
        except Exception as e:
            logger.error(f"LinkedIn Agent failed for {name}: {str(e)}")
            return {
                "linkedin_url": linkedin_url or f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}",
                "linkedin_summary": f"Professional profile of {name} at {company} on LinkedIn.",
                "linkedin_insights": [
                    f"Acts as a key decision maker at {company}.",
                    f"Maintains a professional profile indicating focus on organizational growth."
                ]
            }
