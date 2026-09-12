import base64
import os
from typing import Any

from .providers import groq_vision, parse_json

REQUESTED_GROQ_VISION_MODEL = "llama-3.2-11b-vision-preview"
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", REQUESTED_GROQ_VISION_MODEL)


def _image_part(image_bytes: bytes, mime_type: str) -> dict:
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}}


def _normalise(data: dict[str, Any], language: str) -> dict[str, Any]:
    categories = {"pothole", "streetlight", "garbage", "water_sewer", "park_public_space", "traffic_safety", "other"}
    severities = {"low", "medium", "high", "critical"}
    category = str(data.get("category", "other")).lower().strip().replace(" ", "_")
    severity = str(data.get("severity", "medium")).lower().strip()
    try: confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
    except (TypeError, ValueError): confidence = 0.5
    data.update(category=category if category in categories else "other", severity=severity if severity in severities else "medium", confidence=confidence, needs_review=confidence < 0.65, provider=data.get("provider", "AI"), language=language)
    return data


def classify_image(image_bytes: bytes, mime_type: str, user_description: str = "", language: str = "English") -> dict[str, Any]:
    prompt = f"""You are a civic infrastructure triage expert. Analyze this image and classify the visible issue.
Use exactly one category from: pothole, streetlight, garbage, water_sewer, park_public_space, traffic_safety, other.
Use exactly one severity from: low, medium, high, critical. Severity reflects public safety.
Return only JSON with keys category, severity, confidence, description, evidence, immediate_risk, citizen_summary.
confidence must be a number from 0 to 1. citizen_summary must be in {language}. Be honest if ambiguous.
Citizen note: {user_description or 'None'}"""
    data = parse_json(groq_vision(prompt, [_image_part(image_bytes, mime_type)], GROQ_VISION_MODEL))
    data["provider"] = f"Groq · {GROQ_VISION_MODEL}"
    return _normalise(data, language)


def verify_resolution(before_bytes: bytes, after_bytes: bytes, mime_type: str, language: str = "English") -> dict[str, Any]:
    prompt = f"""Compare the BEFORE and AFTER civic issue images. Determine whether the original issue appears resolved.
Return only JSON with keys resolved, confidence, explanation, citizen_summary. resolved must be true or false,
confidence must be between 0 and 1, and citizen_summary must be in {language}. Do not claim certainty if unclear."""
    data = parse_json(groq_vision(prompt, [{"type": "text", "text": "BEFORE"}, _image_part(before_bytes, mime_type), {"type": "text", "text": "AFTER"}, _image_part(after_bytes, mime_type)], GROQ_VISION_MODEL))
    resolved_value = data.get("resolved", False)
    data["resolved"] = resolved_value if isinstance(resolved_value, bool) else str(resolved_value).lower().strip() in {"true", "yes", "1", "resolved"}
    data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
    return data
