import logging
import requests

logger = logging.getLogger(__name__)

def get_company_summary(company_name: str) -> str:
    """
    Search Wikipedia for a company summary.
    Returns a brief paragraph or empty string if not found.
    """
    logger.info(f"Searching Wikipedia for company: '{company_name}'")
    try:
        # Step 1: Search Wikipedia to find the best page title match
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": company_name,
            "format": "json",
            "utf8": 1
        }
        headers = {"User-Agent": "OutreachNodeColdEmailer/1.0 (contact: admin@outreachnode.io)"}
        
        search_res = requests.get(search_url, params=search_params, headers=headers, timeout=5)
        search_res.raise_for_status()
        search_data = search_res.json()
        
        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            logger.info(f"No Wikipedia pages found matching '{company_name}'.")
            return ""
            
        best_match_title = search_results[0]["title"]
        
        # Step 2: Fetch the summary for the best matched title
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(best_match_title)}"
        summary_res = requests.get(summary_url, headers=headers, timeout=5)
        summary_res.raise_for_status()
        summary_data = summary_res.json()
        
        extract = summary_data.get("extract", "")
        if extract:
            logger.info(f"Found Wikipedia summary for '{best_match_title}'.")
            return extract
            
    except Exception as e:
        logger.error(f"Error fetching Wikipedia summary for '{company_name}': {str(e)}")
        
    return ""
