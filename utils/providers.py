import json
import os
from typing import Any


def key(name: str) -> str:
    return os.getenv(name, "").strip()


def parse_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.replace("```json", "", 1).replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Model response did not contain JSON.")
    return json.loads(text[start:end + 1])


def groq_text(prompt: str, model: str) -> str:
    from groq import Groq
    token = key("GROQ_API_KEY")
    if not token:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    response = Groq(api_key=token).chat.completions.create(model=model, temperature=0, max_tokens=500, messages=[{"role": "user", "content": prompt}])
    return response.choices[0].message.content or ""


def groq_vision(prompt: str, image_parts: list[dict], model: str) -> str:
    from groq import Groq
    token = key("GROQ_API_KEY")
    if not token:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    response = Groq(api_key=token).chat.completions.create(model=model, temperature=0, max_tokens=500, messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, *image_parts]}])
    return response.choices[0].message.content or ""
