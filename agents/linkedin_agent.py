import logging
from duckduckgo_search import DDGS
from middleware.gemini_client import GeminiClient
from tools.search_tool import search_linkedin

logger = logging.getLogger(__name__)

class LinkedInAgent:
    def __init__(self, gemini_client: GeminiClient):
        self.gemini = gemini_client

    def run(self, prospect_profile: dict, research_plan: dict = None) -> dict:
        """
        Searches and gathers LinkedIn information about the prospect or company.
        When a research_plan is provided by the OrchestratorAgent, uses its
        targeted search queries instead of generic ones.
        """
        name = prospect_profile.get("name", "")
        company = prospect_profile.get("company", "")
        title = prospect_profile.get("title", "")
        linkedin_url = prospect_profile.get("linkedin_url", "")
        research_plan = research_plan or {}

        logger.info(f"LinkedIn Agent running for {name} ({company})...")

        # Use orchestrator-guided queries if available, otherwise fall back to default
        snippets = search_linkedin(name, company, linkedin_url)

        # If research plan specifies custom LinkedIn queries, run those too
        if research_plan.get("linkedin_search_queries"):
            for query_template in research_plan["linkedin_search_queries"][:3]:
                query = query_template.replace("{name}", name).replace("{company}", company)
                try:
                    with DDGS() as ddgs:
                        results = ddgs.text(query, max_results=3)
                        if results:
                            extra_snippets = [
                                f"{r.get('title', '')}: {r.get('body', '')}"
                                for r in results if r.get("body")
                            ]
                            snippets.extend(extra_snippets)
                except Exception as e:
                    logger.error(f"Orchestrator-guided LinkedIn query '{query}' failed: {str(e)}")

        linkedin_context = "\n".join([f"- {s}" for s in snippets])

        # Build the research focus context for the LLM
        research_focus = research_plan.get("research_focus", "")
        original_prompt = research_plan.get("original_prompt", "")
        linkedin_priority = research_plan.get("linkedin_priority", "medium")

        system_prompt = f"""
You are an expert social media researcher and LinkedIn analyst. Your job is to analyze search results for a prospect's or company's LinkedIn profile and extract key personal and professional highlights.

{"IMPORTANT: The outreach objective is: " + original_prompt + ". Focus your analysis on finding LinkedIn details that are DIRECTLY relevant to this objective." if original_prompt else ""}
{"Research Focus: " + research_focus if research_focus else ""}
{"LinkedIn data is a HIGH PRIORITY for this outreach campaign. Extract maximum detail." if linkedin_priority == "high" else ""}

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
            from middleware.orchestrator import is_api_key_or_rate_limit_error
            if is_api_key_or_rate_limit_error(e):
                raise e
            return {
                "linkedin_url": linkedin_url or f"https://www.linkedin.com/in/{name.lower().replace(' ', '-')}",
                "linkedin_summary": f"Professional profile of {name} at {company} on LinkedIn.",
                "linkedin_insights": [
                    f"Acts as a key decision maker at {company}.",
                    f"Maintains a professional profile indicating focus on organizational growth."
                ]
            }
