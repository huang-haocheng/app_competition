from tavily import TavilyClient
api = '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'
client = TavilyClient(api)

def web_search(query):
    response = client.search(
        query=query,
        search_depth="basic"
    )
    return response