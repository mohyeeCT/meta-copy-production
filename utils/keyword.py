import math


def select_keyword(
    gsc_queries: list,
    dfs_data: dict,
    branded_terms: list = None,
    position_cutoff: float = 1.0,
    min_volume: int = 100
) -> dict:
    """
    Scores and selects the best target keyword from GSC queries + DFS data.

    gsc_queries: list of { query, impressions, position }
    dfs_data: dict keyed by keyword (lowercase): { volume, difficulty }
    branded_terms: list of brand name strings to filter out
    position_cutoff: skip queries already ranking at or above this position
    min_volume: skip keywords below this monthly search volume

    Returns:
    {
        selected_keyword: str or None,
        selected_keyword_data: dict or None,
        runner_up: dict or None,
        all_scored: list,
        fallback_triggered: bool
    }
    """
    branded_terms = [t.lower() for t in (branded_terms or [])]
    scored = []

    for row in gsc_queries:
        query = row.get("query", "").lower().strip()

        # Filter: branded
        if any(term in query for term in branded_terms):
            continue

        # Filter: already at position 1
        if row.get("position", 99) <= position_cutoff:
            continue

        # Match to DFS data
        dfs = dfs_data.get(query)
        if not dfs:
            continue

        volume = dfs.get("volume", 0)
        difficulty = dfs.get("difficulty", 50) or 50

        # Filter: low volume
        if volume < min_volume:
            continue

        # Score: volume / difficulty * log(impressions + 1)
        impressions = row.get("impressions", 1)
        score = (volume / difficulty) * math.log1p(impressions)

        scored.append({
            "keyword": row.get("query"),
            "volume": volume,
            "difficulty": difficulty,
            "impressions": impressions,
            "position": row.get("position"),
            "score": round(score, 2)
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    winner = scored[0] if scored else None
    runner_up = scored[1] if len(scored) > 1 else None

    return {
        "selected_keyword": winner["keyword"] if winner else None,
        "selected_keyword_data": winner,
        "runner_up": runner_up,
        "all_scored": scored,
        "fallback_triggered": winner is None
    }
