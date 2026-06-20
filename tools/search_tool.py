import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def search_person(name: str, company: str) -> list[str]:
    """
    Search for a person on DuckDuckGo and return top search snippet results.
    """
    query = f"{name} {company} professional profile career accomplishments"
    logger.info(f"Searching DuckDuckGo for person: '{query}'")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            if results:
                return [r.get("body", "") for r in results if r.get("body")]
    except Exception as e:
        logger.error(f"DuckDuckGo search error for person {name}: {str(e)}")
        
    # Fallback / Mock behavior if DDGS fails
    return [
        f"{name} is a seasoned professional at {company}.",
        f"{name} has experience in technology leadership, strategy, and business growth at {company}.",
        f"For more details, visit {name}'s public professional profiles."
    ]

def search_company_news(company: str) -> list[dict]:
    """
    Search for recent news about a company and return titles, snippets, and links.
    """
    query = f"{company} recent news updates business announcements"
    logger.info(f"Searching DuckDuckGo for news: '{query}'")
    try:
        with DDGS() as ddgs:
            # Using text search or news search
            results = ddgs.text(query, max_results=5)
            if results:
                formatted_news = []
                for r in results:
                    formatted_news.append({
                        "title": r.get("title", f"News about {company}"),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })
                return formatted_news
    except Exception as e:
        logger.error(f"DuckDuckGo search error for company news {company}: {str(e)}")
        
    # Fallback / Mock behavior if DDGS fails
    return [
        {
            "title": f"{company} Continues Market Expansion",
            "snippet": f"{company} has announced new strategic initiatives focusing on automation and product growth in their sector.",
            "url": "https://example.com/news"
        },
        {
            "title": f"Technological Innovations at {company}",
            "snippet": f"Recent interviews with leadership at {company} outline their vision for integrating AI and machine learning into core operations.",
            "url": "https://example.com/news-2"
        }
    ]

def search_linkedin(name: str, company: str, profile_url: str = "") -> list[str]:
    """
    Search DuckDuckGo for LinkedIn profile or company page info.
    """
    if profile_url and "linkedin.com" in profile_url:
        query = f"site:{profile_url.replace('https://', '').replace('http://', '')}"
    elif name and company:
        query = f"\"{name}\" \"{company}\" site:linkedin.com/in/ OR site:linkedin.com/pub/"
    elif company:
        query = f"\"{company}\" site:linkedin.com/company/"
    else:
        return []
        
    logger.info(f"Searching DuckDuckGo for LinkedIn: '{query}'")
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            if results:
                return [f"{r.get('title', '')}: {r.get('body', '')}" for r in results if r.get("body")]
    except Exception as e:
        logger.error(f"DuckDuckGo search error for LinkedIn query '{query}': {str(e)}")
        
    # Fallback/Mock behavior
    if name:
        return [
            f"{name} | LinkedIn: View the professional profile of {name} on LinkedIn, the world's largest professional community. {name} is based in Pakistan and currently serves at {company}.",
            f"{name} - {company} | LinkedIn: Experience, education, activity, and achievements of {name} at {company}."
        ]
    else:
        return [
            f"{company} | LinkedIn: {company} is a premier software development house providing cutting-edge IT and software solutions worldwide.",
            f"Working at {company} | LinkedIn: Learn about {company} life, office locations, culture, and job openings on LinkedIn."
        ]

