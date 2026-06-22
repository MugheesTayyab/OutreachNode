import logging
from duckduckgo_search import DDGS
from middleware.ai_client import AIClient
from tools.search_tool import search_company_news
from tools.wiki_tool import get_company_summary

logger = logging.getLogger(__name__)

class ContextAgent:
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client

    def run(self, prospect_profile: dict, linkedin_data: dict = None, campaign_settings: dict = None, research_plan: dict = None) -> dict:
        """
        Analyzes the prospect's company using news, Wikipedia, website searches, and custom prompt alignment.
        When a research_plan is provided by the OrchestratorAgent, uses its targeted search queries
        and research focus instead of generating new ones.
        """
        company = prospect_profile.get("company", "")
        if not company:
            logger.warning("No company specified. Context Agent skipping search.")
            return {
                "company_summary": "No company specified.",
                "recent_news": [],
                "pain_points": ["Lack of company context"],
                "talking_points": ["Connecting with leadership"],
                "custom_alignment": "No custom alignment possible without company information."
            }
            
        campaign_settings = campaign_settings or {}
        linkedin_data = linkedin_data or {}
        research_plan = research_plan or {}
        custom_prompt = campaign_settings.get("custom_prompt", "Introduce our services and suggest a brief call.")
        
        # Extract orchestrator guidance
        research_focus = research_plan.get("research_focus", "")
        original_prompt = research_plan.get("original_prompt", custom_prompt)
        web_priority = research_plan.get("web_priority", "medium")
        key_requirements = research_plan.get("key_requirements", [])
        email_angle = research_plan.get("email_angle", "")
        
        logger.info(f"Context Agent running deep website/prompt analysis for company: {company}...")
        
        # 1. Gather general inputs
        wiki_summary = get_company_summary(company)
        news_items = search_company_news(company)
        
        # Format news
        news_context = ""
        for i, item in enumerate(news_items, 1):
            news_context += f"News #{i}: {item['title']}\nSnippet: {item['snippet']}\n\n"
            
        # 2. Find website URL
        website_snippets = []
        website_query = f"{company} official website domain homepage"
        try:
            with DDGS() as ddgs:
                results = ddgs.text(website_query, max_results=3)
                if results:
                    website_snippets = [f"{r.get('title', '')}: {r.get('href', '')} - {r.get('body', '')}" for r in results]
        except Exception as e:
            logger.error(f"Error finding website for {company}: {str(e)}")

        # 3. Determine search queries — use orchestrator plan if available, otherwise generate via AI
        queries = []
        
        if research_plan.get("web_search_queries"):
            # Use the orchestrator-provided queries directly
            logger.info(f"Using orchestrator-guided web search queries for {company}")
            queries = [
                q.replace("{company}", company)
                for q in research_plan["web_search_queries"][:3]
            ]
        else:
            # Fallback: Ask AI to generate queries (original behavior)
            system_gen_prompt = """
You are an expert search specialist. Your job is to output 2-3 search queries that will help find deep information on a company's website about their services, technology stack, and how they align with a specific outreach prompt.
Output only the search queries, one per line. Do not include numbers, bullet points, quotes, or any extra text.
"""
            user_gen_prompt = f"""
Company: {company}
Found Website Snippets:
{"\n".join(website_snippets)}

Outreach Objective / Custom Prompt:
{original_prompt}
"""
            try:
                queries_text = self.ai_client.generate(system_gen_prompt, user_gen_prompt, temperature=0.3)
                queries = [q.strip() for q in queries_text.split("\n") if q.strip()]
            except Exception as e:
                logger.error(f"Failed to generate custom queries for {company}: {str(e)}")
            
        if not queries:
            queries = [
                f"{company} services products solutions",
                f"{company} technology stack case studies portfolio",
                f"{company} recent news updates"
            ]

        # 4. Execute deep searches — scale effort based on web_priority
        max_results_per_query = 4 if web_priority != "high" else 6
        deep_search_snippets = []
        for query in queries[:3]:
            try:
                with DDGS() as ddgs:
                    res = ddgs.text(query, max_results=max_results_per_query)
                    if res:
                        deep_search_snippets.extend([f"Query [{query}] -> {r.get('title')}: {r.get('body')}" for r in res if r.get("body")])
            except Exception as e:
                logger.error(f"Deep search query '{query}' failed for {company}: {str(e)}")
                
        deep_search_context = "\n".join([f"- {s}" for s in deep_search_snippets])

        # 5. Build key requirements context for the synthesis prompt
        key_req_text = ""
        if key_requirements:
            key_req_text = "\n\nThe email being written for this company MUST address these specific requirements from the outreach strategy:\n"
            for i, req in enumerate(key_requirements, 1):
                key_req_text += f"  {i}. {req}\n"
            key_req_text += "\nYour analysis should specifically surface information that helps satisfy these requirements."

        # 6. Synthesize Brief
        system_prompt = f"""
You are a top-tier business strategist and intelligence analyst. Your job is to analyze a company based on its Wikipedia summary, recent news, website snippets, and LinkedIn insights, then synthesize a strategy brief that highlights how the company aligns with the user's outreach prompt.

{"RESEARCH FOCUS: " + research_focus if research_focus else ""}
{"EMAIL ANGLE: The email should approach this company from this angle: " + email_angle if email_angle else ""}
{key_req_text}

You must output a valid JSON object. Do not include any markdown formatting or extra text outside the JSON. The JSON keys must be:
- "company_summary": A 2-3 sentence description of what the company does, its main sector, and value proposition.
- "recent_news": A list of 2-3 major developments or updates about the company.
- "pain_points": A list of 2-3 likely challenges, growth areas, or strategic needs this company is facing (e.g. scaling operations, technological transitions, market competition).
- "talking_points": A list of 2-3 highly relevant, interesting points that could be mentioned in a cold email to build rapport (e.g. congratulations on recent news, a comment on their core technology, or a project they completed).
- "custom_alignment": A 2-3 sentence analysis of how the company's specific services, products, or technology stack align with the user's custom outreach prompt. Provide specific connections that show why this outreach is highly relevant to them.
"""

        user_prompt = f"""
Company Name: {company}
Outreach Objective / Custom Prompt:
{original_prompt}

Wikipedia Summary:
{wiki_summary or "No Wikipedia page found."}

Recent News Search:
{news_context or "No recent news found."}

LinkedIn Insights:
{linkedin_data.get('linkedin_summary', '')}
Insights list: {linkedin_data.get('linkedin_insights', [])}

Website Deep Search context:
{deep_search_context or "No deep search details found."}

Create the strategy brief. Ensure the JSON is clean and valid.
"""
        try:
            brief = self.ai_client.generate_json(system_prompt, user_prompt, temperature=0.3)
            # Ensure keys exist
            brief["company_summary"] = brief.get("company_summary") or f"{company} is a leading player in its industry."
            brief["recent_news"] = brief.get("recent_news") or [f"Continuing operations and product development at {company}."]
            brief["pain_points"] = brief.get("pain_points") or ["Optimizing workflow efficiency", "Enhancing technical infrastructure"]
            brief["talking_points"] = brief.get("talking_points") or [f"Congratulations on the ongoing work at {company}"]
            brief["custom_alignment"] = brief.get("custom_alignment") or f"Potential alignment with outreach objective: {original_prompt}"
            return brief
        except Exception as e:
            logger.error(f"Context Agent failed for company {company}: {str(e)}")
            from middleware.orchestrator import is_api_key_or_rate_limit_error
            if is_api_key_or_rate_limit_error(e):
                raise e
            return {
                "company_summary": f"{company} is a leading player in its industry.",
                "recent_news": [f"Continuing operations and product development at {company}."],
                "pain_points": ["Optimizing workflow efficiency", "Enhancing technical infrastructure"],
                "talking_points": [f"Congratulations on the ongoing work at {company}"],
                "custom_alignment": f"Potential alignment with outreach objective: {original_prompt}"
            }
