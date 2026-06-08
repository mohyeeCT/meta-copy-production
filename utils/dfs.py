def _post_json(url: str, payload: list, dfs_login: str, dfs_password: str):
    import requests
    from requests.auth import HTTPBasicAuth

    return requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(dfs_login, dfs_password)
    )


def get_keyword_overview(dfs_login: str, dfs_password: str, keywords: list, location_code: int = 2840, language_code: str = "en") -> dict:
    """
    Returns keyword data for a list of keywords.
    location_code 2840 = United States. Adjust per client.
    Returns dict keyed by keyword: { volume, difficulty }
    """
    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"

    payload = [
        {
            "keywords": keywords,
            "location_code": location_code,
            "language_code": language_code
        }
    ]

    try:
        response = _post_json(url, payload, dfs_login, dfs_password)
        response.raise_for_status()
        data = response.json()

        results = {}
        tasks = data.get("tasks", [])
        for task in tasks:
            for item in task.get("result", []) or []:
                kw = item.get("keyword", "").lower()
                results[kw] = {
                    "volume": item.get("search_volume") or 0,
                }
        return results

    except Exception as e:
        raise RuntimeError(f"DataForSEO keyword volume failed: {e}") from e



