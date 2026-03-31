import math
import re


def _stem(word: str) -> str:
    """
    Minimal stemmer: strips common suffixes so plurals and
    verb forms match their root. No external libs needed.
    flavors → flavor, beverages → beverage, extracts → extract
    """
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("es") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and len(word) > 3 and not word.endswith("ss"):
        return word[:-1]
    if word.endswith("ing") and len(word) > 5:
        return word[:-3]
    if word.endswith("ed") and len(word) > 4:
        return word[:-2]
    return word


def _relevance_score(query: str, h1: str) -> float:
    """
    Measures topical overlap between a query and the page H1.
    Returns a multiplier between 0.5 and 1.5.

    Uses basic stemming so plurals match roots:
    - H1: "Flavors and Extracts for Beverages"
      → stems: {flavor, extract, beverage}
    - query: "flavor concentrates for beverages"
      → stems: {flavor, concentrate, beverage}
      → overlap: {flavor, beverage} → ratio 2/3 → score 1.167
    - query: "natural flavor concentrates"
      → stems: {natural, flavor, concentrate}
      → overlap: {flavor} → ratio 1/3 → score 0.833
    - query: "water treatment chemicals"
      → no overlap → score 0.5 (penalty)
    """
    STOP_WORDS = {
        "a","an","the","and","or","for","of","in","on","at","to","with",
        "by","from","as","is","are","was","were","be","been","being",
        "it","its","this","that","these","those","we","our","your","their"
    }

    def tokenise(text):
        words = re.findall(r'[a-z]+', text.lower())
        return set(_stem(w) for w in words if w not in STOP_WORDS and len(w) > 2)

    if not h1:
        return 1.0

    h1_words    = tokenise(h1)
    query_words = tokenise(query)

    if not h1_words:
        return 1.0

    overlap = len(h1_words & query_words)
    ratio   = overlap / len(h1_words)

    # Scale: 0 overlap = 0.5 (penalty), full overlap = 1.5 (bonus)
    return round(0.5 + ratio, 3)


def select_keyword(
    gsc_queries: list,
    dfs_data: dict,
    branded_terms: list = None,
    position_cutoff: float = 1.0,
    min_volume: int = 10,
    h1: str = ""
) -> dict:
    """
    Scores and selects the best target keyword from GSC queries + DFS data.

    gsc_queries: list of { query, impressions, clicks, ctr, position }
    dfs_data: dict keyed by keyword (lowercase): { volume, difficulty }
    branded_terms: list of brand name strings to filter out
    position_cutoff: ONLY filters position 1.0 or better (default).
                     Position is otherwise a scoring signal, not a hard filter.
                     We do NOT exclude good-ranking keywords — if the page ranks
                     well for a keyword, that proves relevance and it's a valid target.
    min_volume: skip keywords below this monthly search volume
    h1: current page H1, used as topical relevance signal

    Scoring formula:
        score = (volume / difficulty)
                * log1p(impressions)
                * (1 + ctr)
                * position_score
                * relevance_score

    position_score:
        - Does NOT penalise positions 1-3. Ranking well = keyword is proven relevant.
        - Rewards positions 4-20 as opportunity window.
        - Penalises positions 20+ (weak relevance signal).
        - Formula: 1 / (1 + max(0, position - 20) * 0.1)
          → positions 1-20 all score 1.0, position 30 scores 0.5

    relevance_score:
        - Word overlap between query and H1
        - 0.5 (no overlap) to 1.5 (full overlap)

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
        query    = row.get("query", "").lower().strip()
        position = row.get("position", 99)

        # Filter: branded
        if any(term in query for term in branded_terms):
            continue

        # Filter: only exclude genuine position 1 with strong CTR
        # (title tag is already perfect for this keyword)
        if position <= position_cutoff:
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

        # Position score: positions 1-20 are all valid targets (score 1.0)
        # Beyond 20, score drops to reflect weak relevance signal
        position_score = 1 / (1 + max(0, position - 20) * 0.1)

        # CTR boost: rewards queries users actually click on
        ctr_boost = 1 + ctr

        # H1 relevance: rewards topical alignment with page content
        relevance = _relevance_score(query, h1)

        # Final score
        score = (volume / difficulty) * math.log1p(impressions) * ctr_boost * position_score * relevance

        scored.append({
            "keyword":         row.get("query"),
            "volume":          volume,
            "difficulty":      difficulty,
            "impressions":     impressions,
            "clicks":          clicks,
            "ctr":             round(ctr * 100, 2),
            "position":        position,
            "position_score":  round(position_score, 3),
            "ctr_boost":       round(ctr_boost, 3),
            "relevance_score": relevance,
            "score":           round(score, 2)
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
