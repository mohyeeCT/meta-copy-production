import anthropic
import openai


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


def generate_copy_claude(api_key: str, url: str, keyword: str, page_type: str = "general",
                         brand_name: str = "", forbidden_phrases: str = "", context: str = "") -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    def call(prompt_template):
        prompt = prompt_template.format(
            url=url,
            keyword=keyword,
            page_type=page_type,
            brand_name=brand_name or "N/A",
            forbidden_phrases=forbidden_phrases or "None",
            context=context or "None"
        )
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.strip()

    title = call(TITLE_PROMPT)
    description = call(DESCRIPTION_PROMPT)
    return {"title": title, "description": description}


def generate_copy_openai(api_key: str, url: str, keyword: str, page_type: str = "general",
                         brand_name: str = "", forbidden_phrases: str = "", context: str = "") -> dict:
    client = openai.OpenAI(api_key=api_key)

    def call(prompt_template):
        prompt = prompt_template.format(
            url=url,
            keyword=keyword,
            page_type=page_type,
            brand_name=brand_name or "N/A",
            forbidden_phrases=forbidden_phrases or "None",
            context=context or "None"
        )
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content.strip()

    title = call(TITLE_PROMPT)
    description = call(DESCRIPTION_PROMPT)
    return {"title": title, "description": description}


def generate_copy(provider: str, api_key: str, **kwargs) -> dict:
    if provider == "Claude":
        return generate_copy_claude(api_key, **kwargs)
    elif provider == "OpenAI":
        return generate_copy_openai(api_key, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
