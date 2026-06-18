import logging
from middleware.gemini_client import GeminiClient
from tools.search_tool import search_person

logger = logging.getLogger(__name__)

class ProspectingAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def run(self, raw_prospect: dict) -> dict:
        """
        Gathers info about the prospect using web search and synthesizes a professional profile.
        """
        name = raw_prospect.get("name", "")
        company = raw_prospect.get("company", "")
        title = raw_prospect.get("title", "")
        linkedin_url = raw_prospect.get("linkedin_url", "")
        
        logger.info(f"Prospecting Agent running for {name} ({title} at {company})...")
        
        # Search for details
        search_snippets = search_person(name, company)
        search_context = "\n".join([f"- {s}" for s in search_snippets])
        
        system_prompt = """
You are an expert executive researcher. Your job is to compile a structured professional profile for a prospect based on basic info and web search snippets.
You must output a valid JSON object. Do not include any markdown formatting or extra text outside the JSON. The JSON keys must be:
- "name": The prospect's name.
- "title": The prospect's job title.
- "company": The prospect's company.
- "key_interests": A list of 2-4 professional interests or focus areas.
- "career_highlights": A list of 2-3 significant accomplishments or experience points.
- "professional_summary": A brief 2-3 sentence overview of their professional background.
"""

        user_prompt = f"""
Prospect Name: {name}
Company: {company}
Reported Title: {title}
LinkedIn URL: {linkedin_url}

Web Search Context:
{search_context}

Create the structured professional profile. Ensure the JSON is clean and valid.
"""
        try:
            profile = self.gemini.generate_json(system_prompt, user_prompt, temperature=0.3)
            # Ensure basic fields remain intact if LLM misses them
            profile["name"] = profile.get("name") or name
            profile["title"] = profile.get("title") or title
            profile["company"] = profile.get("company") or company
            return profile
        except Exception as e:
            logger.error(f"Prospecting Agent failed for {name}: {str(e)}")
            # Fallback profile
            return {
                "name": name,
                "title": title,
                "company": company,
                "key_interests": ["Technology Leadership", "Industry Innovation"],
                "career_highlights": [f"Senior leadership position at {company}"],
                "professional_summary": f"Professional serving as {title} at {company}."
            }
