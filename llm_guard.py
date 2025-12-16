import os
import base64
from typing import List, Literal
from pydantic import BaseModel
from openai import OpenAI
import re


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))



def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\[\.\]|\(dot\)", ".", text, flags=re.IGNORECASE)
    text = re.sub(r"hxxps?", "https", text, flags=re.IGNORECASE)
    return text


SYSTEM_TEXT = """Je bent een strikte veiligheids- en misbruikdetectie-classificator voor een publieke website in het Nederlands en Engels.
Je moet gebruikersinhoud beoordelen op:
- nsfw (seksuele inhoud)
- wapens
- alcohol
- drugs
- gore (bloederig / extreem geweld)
- aanstootgevende symbolen (incl. extremistische/haat-symbolen) en haatdragende inhoud
- scheldwoorden / grof taalgebruik (Nederlands + Engels)
- spam (algemeen)
- spam-email / phishing-patronen
- kwaadaardige of verdachte URL’s

Harde regels:
- Als ERGENS scheldwoorden/grof taalgebruik voorkomt, MOET action = "block" en severity = "high" zijn.
- Als ERGENS een kwaadaardige of verdachte URL voorkomt, MOET action minimaal "review" zijn (of "block").
- Bij twijfel kies altijd action="review" (nooit "allow").

Belangrijk:
- "malicious_url" moet worden bepaald op basis van tekstuele heuristiek
  (URL-shorteners, vreemde TLD’s, obfuscatie, phishing-taal, credential-diefstal).
Geef het resultaat terug als gestructureerde data die exact aan het schema voldoet.
"""


SYSTEM_IMAGE = """Je bent een strikte veiligheids- en misbruikdetectie-classificator voor een publieke website.
Je moet een geüploade afbeelding beoordelen op:
- nsfw (seksuele inhoud)
- gore (bloederig / extreem geweld)
- aanstootgevende symbolen (incl. extremistische/haat-symbolen)

Harde regels:
- Als ERGENS aanstootgevende symbolen voorkomen, MOET action = "block" en severity = "high" zijn.
- Bij twijfel kies altijd action="review" (nooit "allow").

Geef het resultaat terug als gestructureerde data die exact aan het schema voldoet.
"""


class Categories(BaseModel):
    nsfw: bool
    weapons: bool
    alcohol: bool
    drugs: bool
    gore: bool
    offensive_symbols: bool
    profanity: bool
    spam: bool
    spam_email: bool
    malicious_url: bool


class Found(BaseModel):
    profanity_terms: List[str]
    suspicious_phrases: List[str]
    urls: List[str]
    suspicious_urls: List[str]
    notes: List[str]


class GuardResult(BaseModel):
    action: Literal["allow", "warn", "review", "block"]
    severity: Literal["low", "medium", "high"]
    categories: Categories
    found: Found
    reasons: List[str]

# Guard text content
def guard_text(*, title: str = "", body: str = "", context: str = "generic") -> dict:
    title = (title or "")[:4000]
    body = (body or "")[:20000]

    title = normalize_text(title)
    body = normalize_text(body)

    resp = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM_TEXT},
            {
                "role": "user",
                "content": f"Context: {context}\n\nTITEL:\n{title}\n\nINHOUD:\n{body}",
            },
        ],
        text_format=GuardResult,
    )

    result = resp.output_parsed

    if result.categories.profanity or (
        result.found.profanity_terms and len(result.found.profanity_terms) > 0
    ):
        result.action = "block"
        result.severity = "high"
        if "Scheldwoorden/grof taalgebruik gedetecteerd" not in result.reasons:
            result.reasons.insert(0, "Scheldwoorden/grof taalgebruik gedetecteerd")

    if result.categories.malicious_url or (
        result.found.suspicious_urls and len(result.found.suspicious_urls) > 0
    ):
        if result.action == "allow":
            result.action = "review"
        if result.severity == "low":
            result.severity = "medium"
        if "Verdachte of kwaadaardige URL gedetecteerd" not in result.reasons:
            result.reasons.insert(0, "Verdachte of kwaadaardige URL gedetecteerd")

    return result.model_dump()

# Helper to convert file to data URL
def _file_to_data_url(path: str) -> str:
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext in ("jpg", "jpeg"):
        mime = "image/jpeg"
    elif ext == "png":
        mime = "image/png"
    elif ext == "webp":
        mime = "image/webp"
    else:
        mime = "application/octet-stream"

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime};base64,{b64}"


# Guard image content
def guard_image(path: str, context: str = "image_upload") -> dict:
    data_url = _file_to_data_url(path)

    resp = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": SYSTEM_IMAGE},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Context: {context}. Classificeer deze afbeelding.",
                    },
                    {"type": "input_image", "image_url": data_url},
                ],
            },
        ],
        text_format=GuardResult,
    )

    result = resp.output_parsed

    if result.categories.offensive_symbols:
        result.action = "block"
        result.severity = "high"
        if "Aanstootgevende symbolen gedetecteerd" not in result.reasons:
            result.reasons.insert(0, "Aanstootgevende symbolen gedetecteerd")

    if result.categories.nsfw or result.categories.gore:
        if result.action == "allow":
            result.action = "review"
        if result.severity == "low":
            result.severity = "medium"

    return result.model_dump()
