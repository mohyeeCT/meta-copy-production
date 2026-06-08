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


def get_keyword_difficulty(dfs_login: str, dfs_password: str, keywords: list, location_code: int = 2840, language_code: str = "en") -> dict:
    """
    Fetches keyword difficulty scores from DataForSEO Labs.
    Returns dict keyed by keyword: { difficulty }
    """
    url = "https://api.dataforseo.com/v3/dataforseo_labs/google/bulk_keyword_difficulty/live"

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
                for kw_item in item.get("items", []) or []:
                    kw = kw_item.get("keyword", "").lower()
                    results[kw] = {
                        "difficulty": kw_item.get("keyword_difficulty") or 50
                    }
        return results

    except Exception as e:
        raise RuntimeError(f"DataForSEO keyword difficulty failed: {e}") from e
