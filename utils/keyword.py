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
    h1: str = "",
    restricted_industry: bool = False,
) -> dict:
    """
    Scores and selects the best target keyword from GSC queries + DFS data.

    gsc_queries: list of { query, impressions, clicks, ctr, position }
    dfs_data: dict keyed by keyword (lowercase): { volume, difficulty }
    branded_terms: list of brand name strings to filter out
    position_cutoff: ONLY filters position 1.0 or better (default).
    min_volume: skip keywords below this monthly search volume (ignored in restricted mode)
    h1: current page H1, used as topical relevance signal
    restricted_industry: when True, ignore volume/difficulty and score on GSC engagement
        signals only. Use for industries where DFS suppresses volume data
        (CBD, firearms, dispensaries, adult content).

    Standard scoring formula:
        score = (volume / difficulty) * log1p(impressions) * (1 + ctr)
                * position_score * relevance_score

    Restricted scoring formula (no DFS dependency):
        score = log1p(impressions) * max(log1p(clicks), 1.0) * (1 + ctr)
                * position_score * relevance_score
    """
    branded_terms = [t.lower() for t in (branded_terms or [])]
    scored = []

    for row in gsc_queries:
        query    = row.get("query", "").lower().strip()
        position = row.get("position", 99)

        # Filter: branded
        if any(term in query for term in branded_terms):
            continue

        # Filter: only exclude genuine position 1
        if position <= position_cutoff:
            continue

        impressions = row.get("impressions", 1)
        clicks      = row.get("clicks", 0)
        ctr         = min(row.get("ctr", 0), 0.15)  # cap CTR at 15% to prevent outlier domination

        # Match to DFS data
        dfs        = dfs_data.get(query)
        volume     = dfs.get("volume", 0) if dfs else 0
        kd = dfs.get("difficulty") if dfs else None
        difficulty = max(kd if kd is not None else 50, 1)

        if restricted_industry:
            # Ignore volume/difficulty — score purely on GSC engagement signals
            # so industries where DFS suppresses data still get a useful keyword
            clicks_boost   = max(math.log1p(clicks), 1.0)
            position_score = 1 / (1 + max(0, position - 20) * 0.1)
            ctr_boost      = 1 + ctr
            relevance      = _relevance_score(query, h1)
            score = math.log1p(impressions) * clicks_boost * ctr_boost * position_score * relevance
        else:
            # Standard mode: require DFS data and minimum volume
            if not dfs:
                continue
            if volume < min_volume:
                continue

            position_score = 1 / (1 + max(0, position - 20) * 0.1)
            ctr_boost      = 1 + ctr
            relevance      = _relevance_score(query, h1)
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
