import logging
from middleware.gemini_client import GeminiClient
from tools.search_tool import search_company_news
from tools.wiki_tool import get_company_summary

logger = logging.getLogger(__name__)

class ContextAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def run(self, prospect_profile: dict) -> dict:
        """
        Analyzes the prospect's company using news search and Wikipedia, and builds a context brief.
        """
        company = prospect_profile.get("company", "")
        if not company:
            logger.warning("No company specified. Context Agent skipping search.")
            return {
                "company_summary": "No company specified.",
                "recent_news": [],
                "pain_points": ["Lack of company context"],
                "talking_points": ["Connecting with leadership"]
            }
            
        logger.info(f"Context Agent running for company: {company}...")
        
        # Gather inputs
        wiki_summary = get_company_summary(company)
        news_items = search_company_news(company)
        
        # Format news
        news_context = ""
        for i, item in enumerate(news_items, 1):
            news_context += f"News #{i}: {item['title']}\nSnippet: {item['snippet']}\n\n"
            
        system_prompt = """
You are a top-tier business strategist and intelligence analyst. Your job is to analyze a company based on its Wikipedia summary and recent news, then synthesize a strategy brief.
You must output a valid JSON object. Do not include any markdown formatting or extra text outside the JSON. The JSON keys must be:
- "company_summary": A 2-3 sentence description of what the company does, its main sector, and value proposition.
- "recent_news": A list of 2-3 major developments or updates about the company based on the provided search results.
- "pain_points": A list of 2-3 likely challenges, growth areas, or strategic needs this company is facing (e.g. scaling operations, technological transitions, market competition).
- "talking_points": A list of 2-3 highly relevant, interesting points that could be mentioned in a cold email to build rapport (e.g. congratulations on recent news, a comment on their core technology).
"""

        user_prompt = f"""
Company Name: {company}

Wikipedia Summary:
{wiki_summary or "No Wikipedia page found."}

Recent News Search:
{news_context or "No recent news found."}

Create the strategy brief. Ensure the JSON is clean and valid.
"""
        try:
            brief = self.gemini.generate_json(system_prompt, user_prompt, temperature=0.3)
            return brief
        except Exception as e:
            logger.error(f"Context Agent failed for company {company}: {str(e)}")
            return {
                "company_summary": f"{company} is a leading player in its industry.",
                "recent_news": [f"Continuing operations and product development at {company}."],
                "pain_points": ["Optimizing workflow efficiency", "Enhancing technical infrastructure"],
                "talking_points": [f"Congratulations on the ongoing work at {company}"]
            }
