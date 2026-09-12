import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .providers import groq_text, parse_json

RAG_MODEL = os.getenv("GROQ_RAG_MODEL", "llama-3.1-8b-instant")
BASE_DIR = Path(__file__).resolve().parents[1]
KB_PATH = BASE_DIR / "data" / "departments.txt"


@lru_cache(maxsize=1)
def _get_vector_store() -> FAISS:
    docs = TextLoader(str(KB_PATH), encoding="utf-8").load()
    chunks = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=80).split_documents(docs)
    return FAISS.from_documents(chunks, HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"))


def route_issue(classification: dict[str, Any], user_description: str = "", language: str = "English") -> dict[str, Any]:
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
