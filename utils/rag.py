import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from .providers import groq_text, parse_json

RAG_MODEL = os.getenv("GROQ_RAG_MODEL", "llama-3.1-8b-instant")
BASE_DIR = Path(__file__).resolve().parents[1]
KB_PATH = BASE_DIR / "data" / "departments.txt"


@lru_cache(maxsize=1)
def _get_vector_store():
    from langchain_community.document_loaders import TextLoader
    from langchain_community.vectorstores import FAISS
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    docs = TextLoader(str(KB_PATH), encoding="utf-8").load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=80).split_documents(docs)
    return FAISS.from_documents(chunks, HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"))


def route_issue(classification: dict[str, Any], user_description: str = "", language: str = "English") -> dict[str, Any]:
    if not os.getenv("GROQ_API_KEY", "").strip():
        urdu = language == "Urdu"
        departments = {
            "pothole": ("Public Works and Roads", "سڑک کے نقصان کی قسم شہری کی درج کردہ تفصیل کی بنیاد پر منتخب کی گئی ہے۔" if urdu else "Road damage category selected from the submitted note.", "متاثرہ سڑک کا معائنہ کرکے مرمت کی جائے۔" if urdu else "Inspect and repair the damaged road surface."),
            "streetlight": ("Street Lighting and Electrical Services", "سٹریٹ لائٹ کی قسم درج کردہ تفصیل کی بنیاد پر منتخب کی گئی ہے۔" if urdu else "Street lighting category selected from the submitted note.", "لائٹ اور بجلی کی فراہمی کا معائنہ کیا جائے۔" if urdu else "Inspect the fixture, power supply, and replace the lamp if required."),
            "garbage": ("Waste Management and Sanitation", "کچرے کی قسم درج کردہ تفصیل کی بنیاد پر منتخب کی گئی ہے۔" if urdu else "Waste category selected from the submitted note.", "کچرا اٹھانے کا انتظام کیا جائے اور مقام کا معائنہ کیا جائے۔" if urdu else "Arrange collection and inspect the site for recurring dumping."),
            "water_sewer": ("Water Supply and Sewerage", "پانی یا نکاسیٔ آب کی قسم درج کردہ تفصیل کی بنیاد پر منتخب کی گئی ہے۔" if urdu else "Water or drainage category selected from the submitted note.", "نالی یا پانی کی لائن کا معائنہ کرکے رساؤ یا رکاوٹ دور کی جائے۔" if urdu else "Inspect the drain or water line and address the leak or blockage."),
            "park_public_space": ("Parks and Public Spaces", "عوامی مقام کی قسم درج کردہ تفصیل کی بنیاد پر منتخب کی گئی ہے۔" if urdu else "Public-space category selected from the submitted note.", "متاثرہ عوامی مقام کا معائنہ کرکے دیکھ بھال کا کام مقرر کیا جائے۔" if urdu else "Inspect and schedule maintenance for the affected public space."),
            "traffic_safety": ("Traffic and Road Safety", "ٹریفک کی حفاظت کی قسم درج کردہ تفصیل کی بنیاد پر منتخب کی گئی ہے۔" if urdu else "Traffic-safety category selected from the submitted note.", "مقام کا معائنہ کرکے مناسب حفاظتی کارروائی کی جائے۔" if urdu else "Inspect the site and apply the appropriate road-safety response."),
        }
        default = ("Public Works and Roads", "مسئلے کے لیے بلدیاتی معائنہ ضروری ہے۔" if urdu else "The issue requires municipal review.", "معائنے کے لیے ایک رابطہ افسر مقرر کیا جائے۔" if urdu else "Assign a coordinator for manual inspection.")
        department, reason, action = departments.get(classification.get("category"), default)
        return {"department": department, "reason": reason, "recommended_action": action, "escalation": "بھیجنے سے پہلے انسانی جائزہ ضروری ہے۔" if urdu else "Manual review required before dispatch.", "provider": "مقامی روٹنگ" if urdu else "Local routing mode"}
    query = f"Category: {classification.get('category')} Severity: {classification.get('severity')} Evidence: {classification.get('evidence')} Description: {classification.get('description')} Citizen note: {user_description}"
    try:
        context = "\n\n".join(doc.page_content for doc in _get_vector_store().similarity_search(query, k=3))
        prompt = f"""Route this civic complaint using only the department knowledge below.
Return only JSON with keys department, reason, recommended_action, escalation. Write reason, recommended_action, and escalation in {language}.
The reason must cite the responsibility or keyword match in plain language.
Knowledge base:\n{context}\nComplaint:\n{query}"""
        data = parse_json(groq_text(prompt, RAG_MODEL)); data["provider"] = f"Groq RAG · {RAG_MODEL}"; return data
    except Exception as exc:
        raise RuntimeError(f"RAG routing failed. Check GROQ_API_KEY, model access, and the knowledge base. Details: {exc}") from exc
