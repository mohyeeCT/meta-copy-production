import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def scrape_h1(url: str, timeout: int = 8) -> dict:
    """
    Scrapes the H1 from a URL.
    Returns:
    {
        h1: str or None,
        all_h1s: list,       # all H1s found on page
        source: "scraped" | "failed",
        error: str or None
    }
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        h1_tags = soup.find_all("h1")
        all_h1s = [tag.get_text(strip=True) for tag in h1_tags if tag.get_text(strip=True)]

        primary_h1 = all_h1s[0] if all_h1s else None

        return {
            "h1": primary_h1,
            "all_h1s": all_h1s,
            "source": "scraped" if primary_h1 else "failed",
            "error": None if primary_h1 else "No H1 found on page"
        }

    except requests.exceptions.Timeout:
        return {"h1": None, "all_h1s": [], "source": "failed", "error": "Timeout"}
    except requests.exceptions.HTTPError as e:
        return {"h1": None, "all_h1s": [], "source": "failed", "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"h1": None, "all_h1s": [], "source": "failed", "error": str(e)[:100]}
