from ddgs import DDGS
from anthropic import beta_tool

@beta_tool
def search_web(query: str) -> str:
    """Search the web for current information.

    Args:
        query: The search query
    Returns:
        Search results as text
    """
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))
        if not results:
            return "No results found."

        output = ""
        for r in results:
            output += f"Title: {r['title']}\nURL: {r['href']}\nSummary: {r['body']}\n\n"
        return output
