import logging
from middleware.ai_client import AIClient

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    LLM-powered orchestrator that analyzes the user's outreach prompt and
    generates a structured research plan to guide downstream agents
    (LinkedIn, Web/Context, Copywriter, Proofreader).
    """

    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client

    def analyze_prompt(self, outreach_prompt: str, settings: dict) -> dict:
        """
        Analyzes the outreach prompt and produces a research plan dict:
        - research_focus: what specific information to look for
        - linkedin_priority: high / medium / low
        - web_priority: high / medium / low
        - linkedin_search_queries: targeted LinkedIn search queries
        - web_search_queries: targeted web/company search queries
        - email_angle: the main hook/angle the email should take
        - key_requirements: what the email MUST include based on the prompt
        - tone_guidance: additional tone notes beyond the basic setting
        """
        logger.info("Orchestrator Agent analyzing outreach prompt...")

        sender_name = settings.get("sender_name", "")
        sender_company = settings.get("sender_company", "")
        sender_role = settings.get("sender_role", "")
        tone = settings.get("tone", "friendly")
        goal = settings.get("goal", "partnership")
        prompt_doc_content = settings.get("prompt_doc_content", "")
        prompt_doc_filename = settings.get("prompt_doc_filename", "")

        system_prompt = """
You are an elite outreach strategist and research director. Your job is to analyze a user's outreach prompt and generate a structured research plan that will guide multiple AI agents (LinkedIn researcher, web researcher, copywriter, proofreader) to produce highly relevant, personalized cold emails.

You must deeply understand the user's intent, identify what information needs to be gathered about each target company, and specify how to angle the emails.

You must output a valid JSON object. Do not include any markdown formatting or extra text outside the JSON. The JSON keys must be:

- "research_focus": A 2-3 sentence description of exactly what information the research agents should prioritize finding about each company (e.g., "Find their current tech stack, recent product launches, and any gaps in their service offerings that align with our AI solutions").

- "linkedin_priority": One of "high", "medium", or "low". Set to "high" if the prompt involves connecting with specific people, understanding org structure, or leveraging professional relationships. Set to "low" if the prompt is purely about company services/products.

- "web_priority": One of "high", "medium", or "low". Set to "high" if the prompt involves understanding their products, services, tech stack, news, or market position. Set to "low" if the prompt is purely about personal connections.

- "linkedin_search_queries": A list of 2-3 search query templates where {company} and {name} are placeholders. These should find LinkedIn data relevant to the outreach prompt (e.g., ["{name} {company} technology leadership", "{company} engineering team culture linkedin"]).

- "web_search_queries": A list of 2-3 search query templates where {company} is a placeholder. These should find web data relevant to the outreach prompt (e.g., ["{company} services technology stack", "{company} recent partnerships announcements"]).

- "email_angle": A 1-2 sentence description of the main hook/angle the cold email should use (e.g., "Position ourselves as a complementary technology partner who can enhance their existing AI capabilities with our specialized drone monitoring solutions").

- "key_requirements": A list of 3-5 specific things the email MUST include or address to properly satisfy the outreach prompt (e.g., ["Reference their specific services that align with our offering", "Mention a concrete benefit or ROI", "Include a specific collaboration idea"]).

- "tone_guidance": A 1-2 sentence note on how the tone should be adapted specifically for this outreach objective, beyond the basic tone setting (e.g., "Since we're pitching to tech leaders, use confident language but avoid overselling. Show genuine curiosity about their work.").
"""

        doc_section = ""
        if prompt_doc_content:
            doc_section = f"""
Reference Document ("{prompt_doc_filename}"):
The user attached the following document for context. Use its content to deeply understand the offering, requirements, or background being promoted:
--- BEGIN DOCUMENT ---
{prompt_doc_content}
--- END DOCUMENT ---
"""

        user_prompt = f"""
Outreach Prompt from User:
"{outreach_prompt}"
{doc_section}
Sender Context:
- Name: {sender_name}
- Role: {sender_role}
- Company: {sender_company}
- Requested Tone: {tone}
- Campaign Goal: {goal}

Analyze this outreach prompt and the attached reference document (if any) and generate the research plan. The plan must enable the downstream agents to find exactly the right information to write compelling, prompt-aligned cold emails.
"""
        try:
            plan = self.ai_client.generate_json(system_prompt, user_prompt, temperature=0.3)

            # Validate and ensure all required keys exist with sensible defaults
            plan["research_focus"] = plan.get("research_focus") or (
                f"Research each company's services, recent developments, and alignment "
                f"with the outreach objective: {outreach_prompt}"
            )
            plan["linkedin_priority"] = plan.get("linkedin_priority", "medium")
            plan["web_priority"] = plan.get("web_priority", "high")
            plan["linkedin_search_queries"] = plan.get("linkedin_search_queries") or [
                "{name} {company} professional profile",
                "{company} leadership team linkedin",
            ]
            plan["web_search_queries"] = plan.get("web_search_queries") or [
                "{company} services products solutions",
                "{company} recent news technology updates",
            ]
            plan["email_angle"] = plan.get("email_angle") or (
                f"Connect with the prospect based on: {outreach_prompt}"
            )
            plan["key_requirements"] = plan.get("key_requirements") or [
                "Reference specific company details",
                "Align with the outreach objective",
                "Include a clear call to action",
            ]
            plan["tone_guidance"] = plan.get("tone_guidance") or (
                f"Maintain a {tone} tone throughout while staying relevant to the outreach goal."
            )

            # Store the original prompt in the plan for downstream reference
            plan["original_prompt"] = outreach_prompt

            logger.info(
                f"Orchestrator Agent generated research plan. "
                f"LinkedIn priority: {plan['linkedin_priority']}, "
                f"Web priority: {plan['web_priority']}, "
                f"Email angle: {plan['email_angle'][:80]}..."
            )
            return plan

        except Exception as e:
            logger.error(f"Orchestrator Agent failed to analyze prompt: {str(e)}")
            from middleware.orchestrator import is_api_key_or_rate_limit_error
            if is_api_key_or_rate_limit_error(e):
                raise e
            # Return a sensible fallback plan so the pipeline doesn't break
            return {
                "research_focus": (
                    f"Research each company's services, products, and recent news "
                    f"to find alignment with: {outreach_prompt}"
                ),
                "linkedin_priority": "medium",
                "web_priority": "high",
                "linkedin_search_queries": [
                    "{name} {company} professional profile",
                    "{company} leadership team linkedin",
                ],
                "web_search_queries": [
                    "{company} services products solutions",
                    "{company} recent news technology updates",
                ],
                "email_angle": f"Connect based on the outreach objective: {outreach_prompt}",
                "key_requirements": [
                    "Reference specific company details",
                    "Align with the outreach objective",
                    "Include a clear call to action",
                ],
                "tone_guidance": f"Maintain a {tone} tone while addressing the outreach goal.",
                "original_prompt": outreach_prompt,
            }
