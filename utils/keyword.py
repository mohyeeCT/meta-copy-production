import math


def select_keyword(
    gsc_queries: list,
    dfs_data: dict,
    branded_terms: list = None,
    position_cutoff: float = 3.0,
    min_volume: int = 10
) -> dict:
    """
    Scores and selects the best target keyword from GSC queries + DFS data.

    gsc_queries: list of { query, impressions, clicks, ctr, position }
    dfs_data: dict keyed by keyword (lowercase): { volume, difficulty }
    branded_terms: list of brand name strings to filter out
    position_cutoff: skip queries already ranking at or above this position (default 3)
    min_volume: skip keywords below this monthly search volume

    Scoring formula:
        score = (volume / difficulty) * log1p(impressions) * (1 + ctr) * position_score

    position_score peaks at position 10 (prime opportunity window):
        - Positions 1-3: already ranking well, deprioritised
        - Positions 4-15: sweet spot, highest scores
        - Positions 16+: weak relevance signal, diminishing score

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

        # Filter: already ranking in top N (default 3 - title tag already working)
        if row.get("position", 99) <= position_cutoff:
            continue

        # Match to DFS data
        dfs = dfs_data.get(query)
        if not dfs:
            continue

        volume     = dfs.get("volume", 0)
        difficulty = dfs.get("difficulty", 50) or 50

        # Filter: low volume
        if volume < min_volume:
            continue

        impressions = row.get("impressions", 1)
        clicks      = row.get("clicks", 0)
        ctr         = row.get("ctr", 0)
        position    = row.get("position", 50)

        # Position score: peaks at position 10, drops off either side
        # Uses a bell curve centred on position 10
        # Position 10 = 1.0, position 4 = ~0.73, position 20 = ~0.50
        position_score = 1 / (1 + abs(position - 10) * 0.15)

        # CTR boost: rewards queries where users actually click through
        # Zero clicks = multiplier of 1.0 (no penalty, no bonus)
        # 5% CTR = multiplier of 1.05, 20% CTR = 1.20
        ctr_boost = 1 + ctr

        # Final score
        score = (volume / difficulty) * math.log1p(impressions) * ctr_boost * position_score

        scored.append({
            "keyword":        row.get("query"),
            "volume":         volume,
            "difficulty":     difficulty,
            "impressions":    impressions,
            "clicks":         clicks,
            "ctr":            round(ctr * 100, 2),   # stored as % for readability
            "position":       position,
            "position_score": round(position_score, 3),
            "ctr_boost":      round(ctr_boost, 3),
            "score":          round(score, 2)
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    winner    = scored[0] if scored else None
    runner_up = scored[1] if len(scored) > 1 else None

    return {
        "selected_keyword":      winner["keyword"] if winner else None,
        "selected_keyword_data": winner,
        "runner_up":             runner_up,
        "all_scored":            scored,
        "fallback_triggered":    winner is None
    }
