import re
import requests


JINA_BASE = "https://r.jina.ai"

_REMOVE_SELECTOR = ", ".join([
    "nav", "header", "footer", "aside",
    "#cart", ".cart", "[class*='cart']",
    "#header", "#footer", "#nav", "#sidebar",
    "[class*='sidebar']", "[class*='navigation']",
    "[class*='breadcrumb']", "[class*='cookie']",
    "[class*='popup']", "[class*='modal']",
    "[class*='newsletter']", "[class*='subscribe']",
    "[class*='related']", "[class*='recommended']",
    "[class*='upsell']", "[class*='cross-sell']",
    "form", "script", "style", "noscript", "iframe",
])

_NOISE_LINE_PATTERNS = re.compile(
    r"^\s*("
    r"\$[\d,.]+|"
    r"Add to cart|Sold out|Sale price|Regular price|Unit price|"
    r"Quantity must be|Adding product|"
    r"Please allow \d|"
    r"Pickup available|Usually ready|"
    r"Check availability|Service Center|"
    r"Skip to content|Log in|Sign in|"
    r"Search$|Menu$|Close$|"
    r"\+?1?[\s\-.]?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}"
    r")\s*$",
    re.IGNORECASE,
)


def _extract_title(text: str) -> str:
    title_match = re.search(r"^Title:\s*(.+)$", text or "", re.MULTILINE)
    return title_match.group(1).strip() if title_match else ""


def _score_paragraph(para: str) -> float:
    words = para.split()
    if len(words) < 8:
        return 0.0
    link_count = len(re.findall(r"\[.+?\]\(https?://", para))
    if link_count > 2:
        return 0.0
    alpha_ratio = sum(c.isalpha() for c in para) / max(len(para), 1)
    if alpha_ratio < 0.5:
        return 0.0
    return len(words) * alpha_ratio


def _clean_reader_text(text: str, max_chars: int = 5000) -> tuple:
    title = _extract_title(text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text or "")
    text = re.sub(r"^\s*\*\s+\[.+?\]\(https?://.+?\)\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^#{1,4}\s+\[.+?\]\(https?://.+?\)\s*$", "", text, flags=re.MULTILINE)

    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _NOISE_LINE_PATTERNS.match(line):
            continue
        if line.startswith("Title:"):
            continue
        lines.append(line)

    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    paragraphs = re.split(r"\n{2,}", text)

    result_paras = []
    chars_used = 0
    for para in paragraphs:
        if chars_used >= max_chars:
            break
        is_heading = para.strip().startswith("#")
        if _score_paragraph(para) > 0 or is_heading:
            result_paras.append(para)
            chars_used += len(para)

    content = "\n\n".join(result_paras).strip()
    if len(content) > max_chars:
        truncated = content[:max_chars]
        last_period = truncated.rfind(".")
        content = truncated[: last_period + 1].strip() if last_period > max_chars * 0.5 else truncated.strip()

    return content, title


def scrape_page_context(api_key: str, url: str, max_chars: int = 5000) -> dict:
    if not url:
        return {"content": "", "title": "", "success": False, "error": "No URL provided"}

    headers = {
        "Accept": "text/plain",
        "X-Return-Format": "markdown",
        "X-With-Links-Summary": "false",
        "X-With-Images-Summary": "false",
        "X-Remove-Selector": _REMOVE_SELECTOR,
        "X-Timeout": "30",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(f"{JINA_BASE}/{url}", headers=headers, timeout=35)
        if resp.status_code in (400, 422):
            headers.pop("X-Remove-Selector", None)
            resp = requests.get(f"{JINA_BASE}/{url}", headers=headers, timeout=35)
        resp.raise_for_status()

        content, title = _clean_reader_text(resp.text.strip(), max_chars=max_chars)
        if not content:
            return {"content": "", "title": title, "success": False, "error": "No substantive content found"}
        return {"content": content, "title": title, "success": True, "error": ""}
    except requests.exceptions.Timeout:
        return {"content": "", "title": "", "success": False, "error": "Request timed out"}
    except requests.exceptions.HTTPError as e:
        return {"content": "", "title": "", "success": False, "error": f"HTTP {e.response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"content": "", "title": "", "success": False, "error": str(e)}
    except Exception as e:
        return {"content": "", "title": "", "success": False, "error": str(e)}
