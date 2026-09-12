import base64
from io import BytesIO
import os
from typing import Any

import streamlit as st
from PIL import Image

from .providers import groq_vision, parse_json

REQUESTED_GROQ_VISION_MODEL = "qwen/qwen3.6-27b"
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", REQUESTED_GROQ_VISION_MODEL)


LOCAL_LABELS = {
    "a pothole or damaged road surface": "pothole",
    "a broken streetlight": "streetlight",
    "a garbage dump or littered street": "garbage",
    "a water leak, flooded area, or blocked drain": "water_sewer",
    "a damaged park or public space": "park_public_space",
    "a traffic or road safety problem": "traffic_safety",
    "another civic issue": "other",
}


@st.cache_resource(show_spinner=False)
def _load_local_vision_model():
    from transformers import pipeline
    return pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")


def _local_classification(image_bytes: bytes, user_description: str, language: str) -> dict[str, Any]:
    """Analyse the uploaded image locally with CLIP, without an API key."""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        results = _load_local_vision_model()(image, candidate_labels=list(LOCAL_LABELS))
        top = results[0]
        category = LOCAL_LABELS[top["label"]]
        scores = {LOCAL_LABELS[item["label"]]: float(item["score"]) for item in results}
        text = (user_description or "").lower()
        severity = "high" if any(word in text for word in ("danger", "hazard", "accident", "خطرناک")) else "medium"
        return _normalise({
            "category": category,
            "severity": severity,
            "confidence": float(top["score"]),
            "description": user_description.strip() or "Issue identified from the uploaded image.",
            "evidence": "Local CLIP image classification.",
            "immediate_risk": "Review the evidence before dispatch.",
            "citizen_summary": user_description.strip() or "The uploaded image was classified for municipal review.",
            "all_scores": scores,
            "provider": "Local CLIP · openai/clip-vit-base-patch32",
        }, language)
    except Exception:
        return _local_text_classification(user_description, language)


def _local_text_classification(user_description: str, language: str) -> dict[str, Any]:
    """Transparent final fallback if the local model cannot load."""
    text = (user_description or "").lower()
    keyword_groups = {
        "pothole": ("pothole", "road damage", "broken road", "گڑھا", "سڑک"),
        "streetlight": ("streetlight", "street light", "lamp", "light is off", "اسٹریٹ لائٹ"),
        "garbage": ("garbage", "trash", "waste", "rubbish", "کچرا", "صفائی"),
        "water_sewer": ("sewer", "drain", "water leak", "flood", "سیوریج", "پانی"),
        "park_public_space": ("park", "playground", "bench", "پارک"),
        "traffic_safety": ("traffic", "signal", "crossing", "accident", "ٹریفک"),
    }
    category = "other"
    for candidate, keywords in keyword_groups.items():
        if any(keyword in text for keyword in keywords):
            category = candidate
            break
    severity = "high" if any(word in text for word in ("danger", "hazard", "accident", "خطرناک")) else "medium"
    description = user_description.strip() or "Issue submitted for municipal review."
    return _normalise({
        "category": category,
        "severity": severity,
        "confidence": 0.45,
        "description": description,
        "evidence": "Local text mode: the image model was unavailable; review is required.",
        "immediate_risk": "Please review the evidence before dispatch.",
        "citizen_summary": description,
        "provider": "Local text mode",
    }, language)


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
    if not os.getenv("GROQ_API_KEY", "").strip():
        return _local_classification(image_bytes, user_description, language)
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
