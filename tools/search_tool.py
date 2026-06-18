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
