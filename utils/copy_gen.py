import anthropic
import openai
import google.generativeai as genai
from mistralai import Mistral
from groq import Groq


TITLE_PROMPT = """You are an SEO copywriter. Write a page title tag for the following page.

Rules:
- Maximum 60 characters (hard limit)
- Include the target keyword naturally, ideally near the start
- Do not use all-caps, excessive punctuation, or clickbait
- Do not pad with filler words
- Include the brand name at the end separated by a pipe if provided
- Return ONLY the title tag text, nothing else

Page URL: {url}
Page Type: {page_type}
Target Keyword: {keyword}
Brand Name: {brand_name}
Forbidden Phrases: {forbidden_phrases}
Additional Context: {context}"""


DESCRIPTION_PROMPT = """You are an SEO copywriter. Write a meta description for the following page.

Rules:
- Maximum 155 characters (hard limit)
- Include the target keyword naturally
- Include a soft call to action
- Do not use all-caps, excessive punctuation, or clickbait
- Do not duplicate the title tag
- Return ONLY the meta description text, nothing else

Page URL: {url}
Page Type: {page_type}
Target Keyword: {keyword}
Brand Name: {brand_name}
Forbidden Phrases: {forbidden_phrases}
Additional Context: {context}"""


def _build_prompt(template: str, url: str, keyword: str, page_type: str,
                  brand_name: str, forbidden_phrases: str, context: str) -> str:
    return template.format(
        url=url,
        keyword=keyword,
        page_type=page_type,
        brand_name=brand_name or "N/A",
        forbidden_phrases=forbidden_phrases or "None",
        context=context or "None"
    )


# ── Claude ────────────────────────────────────────────────────────────────────
def generate_copy_claude(api_key: str, url: str, keyword: str, page_type: str = "general",
                         brand_name: str = "", forbidden_phrases: str = "", context: str = "") -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    def call(template):
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": _build_prompt(template, url, keyword, page_type, brand_name, forbidden_phrases, context)}]
        )
        return msg.content[0].text.strip()

    return {"title": call(TITLE_PROMPT), "description": call(DESCRIPTION_PROMPT)}


# ── OpenAI ────────────────────────────────────────────────────────────────────
def generate_copy_openai(api_key: str, url: str, keyword: str, page_type: str = "general",
                         brand_name: str = "", forbidden_phrases: str = "", context: str = "") -> dict:
    client = openai.OpenAI(api_key=api_key)

    def call(template):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            messages=[{"role": "user", "content": _build_prompt(template, url, keyword, page_type, brand_name, forbidden_phrases, context)}]
        )
        return resp.choices[0].message.content.strip()

    return {"title": call(TITLE_PROMPT), "description": call(DESCRIPTION_PROMPT)}


# ── Gemini ────────────────────────────────────────────────────────────────────
def generate_copy_gemini(api_key: str, url: str, keyword: str, page_type: str = "general",
                         brand_name: str = "", forbidden_phrases: str = "", context: str = "") -> dict:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    def call(template):
        resp = model.generate_content(_build_prompt(template, url, keyword, page_type, brand_name, forbidden_phrases, context))
        return resp.text.strip()

    return {"title": call(TITLE_PROMPT), "description": call(DESCRIPTION_PROMPT)}


# ── Mistral ───────────────────────────────────────────────────────────────────
def generate_copy_mistral(api_key: str, url: str, keyword: str, page_type: str = "general",
                          brand_name: str = "", forbidden_phrases: str = "", context: str = "") -> dict:
    client = Mistral(api_key=api_key)

    def call(template):
        resp = client.chat.complete(
            model="mistral-small-latest",
            max_tokens=256,
            messages=[{"role": "user", "content": _build_prompt(template, url, keyword, page_type, brand_name, forbidden_phrases, context)}]
        )
        return resp.choices[0].message.content.strip()

    return {"title": call(TITLE_PROMPT), "description": call(DESCRIPTION_PROMPT)}


# ── Groq ──────────────────────────────────────────────────────────────────────
def generate_copy_groq(api_key: str, url: str, keyword: str, page_type: str = "general",
                       brand_name: str = "", forbidden_phrases: str = "", context: str = "") -> dict:
    client = Groq(api_key=api_key)

    def call(template):
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=256,
            messages=[{"role": "user", "content": _build_prompt(template, url, keyword, page_type, brand_name, forbidden_phrases, context)}]
        )
        return resp.choices[0].message.content.strip()

    return {"title": call(TITLE_PROMPT), "description": call(DESCRIPTION_PROMPT)}


# ── Router ────────────────────────────────────────────────────────────────────
PROVIDERS = {
    "Claude": generate_copy_claude,
    "OpenAI": generate_copy_openai,
    "Gemini (free)": generate_copy_gemini,
    "Mistral (free tier)": generate_copy_mistral,
    "Groq (free tier)": generate_copy_groq,
}

def generate_copy(provider: str, api_key: str, **kwargs) -> dict:
    fn = PROVIDERS.get(provider)
    if not fn:
        raise ValueError(f"Unknown provider: {provider}")
    return fn(api_key, **kwargs)
