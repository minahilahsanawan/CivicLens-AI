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
        departments = {
            "pothole": ("Public Works and Roads", "Road damage category selected from the submitted note.", "Inspect and repair the damaged road surface."),
            "streetlight": ("Street Lighting and Electrical Services", "Street lighting category selected from the submitted note.", "Inspect the fixture, power supply, and replace the lamp if required."),
            "garbage": ("Waste Management and Sanitation", "Waste category selected from the submitted note.", "Arrange collection and inspect the site for recurring dumping."),
            "water_sewer": ("Water Supply and Sewerage", "Water or drainage category selected from the submitted note.", "Inspect the drain or water line and address the leak or blockage."),
            "park_public_space": ("Parks and Public Spaces", "Public-space category selected from the submitted note.", "Inspect and schedule maintenance for the affected public space."),
            "traffic_safety": ("Traffic and Road Safety", "Traffic-safety category selected from the submitted note.", "Inspect the site and apply the appropriate road-safety response."),
        }
        department, reason, action = departments.get(classification.get("category"), ("Public Works and Roads", "The issue requires municipal review.", "Assign a coordinator for manual inspection."))
        return {"department": department, "reason": reason, "recommended_action": action, "escalation": "Manual review required before dispatch.", "provider": "Local routing mode"}
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
