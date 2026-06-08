import json
import re


def _sanitise(text: str, brand_name: str = "") -> str:
    """Apply hard formatting cleanup to model output."""
    if not text:
        return ""
    text = str(text)
    text = text.replace("\u2014", ", ").replace("\u2013", " | ")
    text = re.sub(r"\s*--\s*", ", ", text)
    text = text.strip().strip('"').strip("'").strip()
    if brand_name and brand_name.strip():
        text = re.sub(
            re.escape(brand_name.strip()),
            brand_name.strip(),
            text,
            flags=re.IGNORECASE,
        )
    return text.strip()


BUSINESS_TYPE_CONTEXT = {
    "b2b": {
        "buyer": "procurement managers, R&D teams, and business buyers",
        "intent": "evaluating suppliers, sourcing products, or requesting quotes",
        "tone": "professional, specific, and credibility-focused",
        "cta_examples": "Request a sample, Get specifications, Contact our team, Request a quote",
        "avoid": "consumer-facing CTAs like Shop Now or Buy Today",
        "title_pattern": "lead with the product/service capability, end with brand",
        "desc_pattern": "lead with what you supply or manufacture, include a B2B-specific CTA",
    },
    "b2c": {
        "buyer": "individual consumers",
        "intent": "researching, comparing, or ready to purchase",
        "tone": "direct, benefit-driven, and engaging",
        "cta_examples": "Shop now, Explore the range, Find yours, Order today",
        "avoid": "jargon, overly technical language",
        "title_pattern": "lead with the product benefit or keyword, end with brand",
        "desc_pattern": "highlight the key benefit, create interest, end with CTA",
    },
    "ecommerce": {
        "buyer": "online shoppers",
        "intent": "browsing products, comparing options, ready to buy",
        "tone": "punchy, benefit-focused, conversion-oriented",
        "cta_examples": "Shop now, Browse the collection, Order today, View options",
        "avoid": "vague descriptions with no product specifics",
        "title_pattern": "product name or category first, include a differentiator if space allows, end with brand",
        "desc_pattern": "lead with the product, include a key benefit, end with action-oriented CTA",
    },
    "service": {
        "buyer": "people looking for professional help or a solution to a problem",
        "intent": "evaluating providers, understanding what a service includes, or ready to contact",
        "tone": "confident, outcome-focused, and trustworthy",
        "cta_examples": "Get a quote, Book a consultation, Talk to an expert, Get started",
        "avoid": "vague fluff like world-class or industry-leading",
        "title_pattern": "lead with the service outcome or what you do, include location if local, end with brand",
        "desc_pattern": "state what you do and who you help, include a benefit, end with a direct CTA",
    },
    "local": {
        "buyer": "local searchers with high purchase or visit intent",
        "intent": "finding a nearby provider, checking hours or location, ready to call or visit",
        "tone": "direct, local, and action-oriented",
        "cta_examples": "Call us today, Visit our showroom, Get directions, Book an appointment",
        "avoid": "national/generic copy with no local relevance",
        "title_pattern": "service + location + brand",
        "desc_pattern": "mention the city or area, include what you offer, end with a local-specific CTA",
    },
    "general": {
        "buyer": "general web visitors",
        "intent": "informational or navigational",
        "tone": "clear and informative",
        "cta_examples": "Learn more, Explore, Find out more",
        "avoid": "overly salesy language for informational pages",
        "title_pattern": "topic first, brand last",
        "desc_pattern": "summarize what the page covers clearly, include a soft CTA",
    },
}


UNSUPPORTED_CLAIM_GUARDRAIL = """UNSUPPORTED CLAIM RULES:
- Do not state return, shipping, delivery, warranty, guarantee, refund, exchange, eligibility, availability, stock, pricing, discount, certification, compliance, safety, legal, medical, or performance claims unless explicitly present in supplied context, page details, or brand guidelines.
- Treat business type, niche, keyword, H1, and CTA examples as strategy signals, not proof of this business's actual policies, inventory, prices, warranties, guarantees, or shipping terms.
- If a risky policy or eligibility detail is not confirmed, avoid the claim or use neutral wording that asks readers to check the relevant policy page only when that fits naturally.
- If an unsupported risky claim would be needed to write the strongest copy, keep the copy general and flag it for review in review_notes."""


COPY_PROMPT = """You are a senior SEO copywriter with deep knowledge of how different business types require different copy strategies.

Write one title tag, one meta description, and one optimised H1 for the following page.

Hard rules:
- Title should aim for about 50 to 80 characters.
- Meta description should aim for about 140 to 180 characters.
- Prioritise strong, natural copy over mechanically forcing the old 60/155-character limits.
- H1 has no hard character limit but should aim for under 70 characters.
- Include the target keyword naturally, ideally near the start where it fits.
- No all-caps, excessive punctuation, or clickbait.
- No padding or filler words.
- Never use em dashes anywhere in the output.
- If brand name is provided, append it to the title after a pipe character.
- Use the brand name EXACTLY as provided, preserving capitalisation and full name.
- Do not duplicate the title tag, meta description, and H1.
- Return ONLY a raw JSON object with keys: title, description, h1_optimised, review_notes.

{unsupported_claim_guardrail}

Business context:
- Business type: {business_type}
- Target buyer: {buyer}
- Buyer intent: {intent}
- Recommended tone: {tone}
- Good CTA examples for this type: {cta_examples}
- Recommended title pattern: {title_pattern}
- Recommended description pattern: {desc_pattern}
- Avoid: {avoid}

Page details:
- URL: {url}
- Page type: {page_type}
- Target keyword: {keyword}
- Brand name: {brand_name}
- Current H1: {h1}
- Forbidden phrases: {forbidden_phrases}
- Additional context: {context}

Review notes:
- If output avoids or softens a risky unsupported claim, explain that briefly in review_notes.
- If output is clean, use an empty string for review_notes.
"""


TITLE_PROMPT = COPY_PROMPT
DESCRIPTION_PROMPT = COPY_PROMPT
H1_PROMPT = COPY_PROMPT


def _build_prompt(template: str, url: str, keyword: str, page_type: str,
                  brand_name: str, forbidden_phrases: str, context: str,
                  business_type: str = "general", h1: str = "") -> str:
    btype = (business_type or "general").lower().strip()
    bcontext = BUSINESS_TYPE_CONTEXT.get(btype, BUSINESS_TYPE_CONTEXT["general"])
    return template.format(
        url=url,
        keyword=keyword,
        page_type=page_type,
        brand_name=brand_name or "N/A",
        forbidden_phrases=forbidden_phrases or "None",
        context=context or "None",
        h1=h1 or "Not provided",
        business_type=btype,
        buyer=bcontext["buyer"],
        intent=bcontext["intent"],
        tone=bcontext["tone"],
        cta_examples=bcontext["cta_examples"],
        avoid=bcontext["avoid"],
        title_pattern=bcontext["title_pattern"],
        desc_pattern=bcontext["desc_pattern"],
        unsupported_claim_guardrail=UNSUPPORTED_CLAIM_GUARDRAIL,
    )


def _parse_copy_json(raw: str) -> dict:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```\s*$", "", raw)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object")
    return data


def _fit_to_limit(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    shortened = text[:limit].rstrip()
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0].rstrip()
    return shortened[:limit].rstrip(" ,|")


def _normalise_copy_result(data: dict, brand_name: str = "") -> dict:
    return {
        "title": _fit_to_limit(_sanitise(data.get("title", ""), brand_name), 80),
        "description": _fit_to_limit(_sanitise(data.get("description", ""), brand_name), 180),
        "h1_optimised": _sanitise(data.get("h1_optimised", ""), brand_name),
        "review_notes": _sanitise(data.get("review_notes", ""), brand_name),
    }


def _call_and_normalise(call_fn, url: str, keyword: str, page_type: str,
                        brand_name: str, forbidden_phrases: str, context: str,
                        business_type: str, h1: str) -> dict:
    prompt = _build_prompt(
        COPY_PROMPT,
        url,
        keyword,
        page_type,
        brand_name,
        forbidden_phrases,
        context,
        business_type,
        h1,
    )
    return _normalise_copy_result(_parse_copy_json(call_fn(prompt)), brand_name)


def generate_copy_claude(api_key: str, url: str, keyword: str, page_type: str = "general",
                         brand_name: str = "", forbidden_phrases: str = "", context: str = "",
                         business_type: str = "general", h1: str = "") -> dict:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    def call(prompt):
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    return _call_and_normalise(call, url, keyword, page_type, brand_name, forbidden_phrases, context, business_type, h1)


def generate_copy_openai(api_key: str, url: str, keyword: str, page_type: str = "general",
                         brand_name: str = "", forbidden_phrases: str = "", context: str = "",
                         business_type: str = "general", h1: str = "") -> dict:
    import openai
    client = openai.OpenAI(api_key=api_key)

    def call(prompt):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    return _call_and_normalise(call, url, keyword, page_type, brand_name, forbidden_phrases, context, business_type, h1)


def generate_copy_gemini(api_key: str, url: str, keyword: str, page_type: str = "general",
                         brand_name: str = "", forbidden_phrases: str = "", context: str = "",
                         business_type: str = "general", h1: str = "") -> dict:
    from google import genai as google_genai
    client = google_genai.Client(api_key=api_key)

    def call(prompt):
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return resp.text.strip()

    return _call_and_normalise(call, url, keyword, page_type, brand_name, forbidden_phrases, context, business_type, h1)


def generate_copy_mistral(api_key: str, url: str, keyword: str, page_type: str = "general",
                          brand_name: str = "", forbidden_phrases: str = "", context: str = "",
                          business_type: str = "general", h1: str = "") -> dict:
    from mistralai.client import Mistral
    client = Mistral(api_key=api_key)

    def call(prompt):
        resp = client.chat.complete(
            model="mistral-small-latest",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    return _call_and_normalise(call, url, keyword, page_type, brand_name, forbidden_phrases, context, business_type, h1)


def generate_copy_groq(api_key: str, url: str, keyword: str, page_type: str = "general",
                       brand_name: str = "", forbidden_phrases: str = "", context: str = "",
                       business_type: str = "general", h1: str = "") -> dict:
    from groq import Groq
    client = Groq(api_key=api_key)

    def call(prompt):
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    return _call_and_normalise(call, url, keyword, page_type, brand_name, forbidden_phrases, context, business_type, h1)


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
