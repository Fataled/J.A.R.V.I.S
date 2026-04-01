from ddgs import DDGS
import webbrowser

def aquire_links(query: str) -> str:
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

def search_web(url: str) -> str:
    """
    Search the web for current information.
    Args:
        url: The website we are searching
    Returns:
        Confirmation of success or failure at opening web page
    """
    try:
        webbrowser.open_new_tab(url)
        return "Success"
    except Exception as e:
        return f"Failure due to {e}"