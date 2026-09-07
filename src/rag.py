"""Grounded question answering and feedback persistence for HealthSentinel.

The module deliberately keeps the LLM optional. Without MongoDB and an LLM,
the UI can still explain that grounded answering is not configured instead of
inventing an answer.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any


def _mongo_client():
    from pymongo import MongoClient

    uri = os.environ.get("MONGO_URI", "").strip()
    if not uri:
        return None
    return MongoClient(uri, serverSelectionTimeoutMS=5000)


def retrieve_context(question: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Retrieve grounded chunks through Atlas Vector Search.

    Embeddings are supplied by ``EMBEDDING_VECTOR`` as a comma-separated
    vector, or by a configured ``sentence-transformers`` model. The latter is
    optional so importing the app never downloads a model.
    """
    client = _mongo_client()
    if client is None:
        return []
    try:
        vector = _embed(question)
        if not vector:
            return []
        db = client[os.environ.get("MONGO_DB", "healthsentinel")]
        return list(db.rag_chunks.aggregate([
            {"$vectorSearch": {
                "index": os.environ.get("ATLAS_VECTOR_INDEX", "rag_chunks_vector"),
                "path": "embedding",
                "queryVector": vector,
                "numCandidates": max(top_k * 10, 50),
                "limit": top_k,
            }},
            {"$project": {"_id": 0, "text": 1, "metadata": 1,
                           "score": {"$meta": "vectorSearchScore"}}},
        ]))
    finally:
        client.close()


def _embed(text: str) -> list[float]:
    raw = os.environ.get("EMBEDDING_VECTOR", "").strip()
    if raw:
        return [float(value) for value in raw.split(",")]
    model_name = os.environ.get("EMBEDDING_MODEL", "").strip()
    if not model_name:
        return []
    import importlib

    SentenceTransformer = importlib.import_module("sentence_transformers").SentenceTransformer
    model = SentenceTransformer(model_name)
    return model.encode(text, normalize_embeddings=True).tolist()


def answer_question(question: str, top_k: int = 5) -> dict[str, Any]:
    """Answer only from retrieved context using the configured LLM."""
    sources = retrieve_context(question, top_k)
    if not sources:
        return {"answer": "I cannot answer this from the configured HealthSentinel sources.",
                "sources": [], "grounded": False}

    context = "\n\n".join(
        f"[{index}] {item.get('text', '')}" for index, item in enumerate(sources, 1)
    )
    answer = _generate(question, context)
    return {"answer": answer, "sources": sources, "grounded": True}


def _generate(question: str, context: str) -> str:
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    if provider != "gemini" or not os.environ.get("GEMINI_API_KEY"):
        return "Grounded context was found, but no supported LLM provider is configured."
    import json
    from urllib.request import Request, urlopen

    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent?key=" + os.environ["GEMINI_API_KEY"]
    )
    prompt = ("Answer only from the context below. If it does not contain the answer, "
              "say that the data is insufficient. Cite sources as [1], [2], etc.\n\n"
              f"Question: {question}\n\nContext:\n{context}")
    request = Request(endpoint, data=json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode(),
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=20) as response:  # nosec B310: fixed HTTPS endpoint
        payload = json.load(response)
    return payload["candidates"][0]["content"]["parts"][0]["text"]


def save_feedback(question: str, answer: str, sources: list[dict[str, Any]],
                  rating: str, comment: str = "", user: str = "anonymous") -> None:
    """Persist answer feedback when Atlas is configured."""
    client = _mongo_client()
    if client is None:
        return
    try:
        db = client[os.environ.get("MONGO_DB", "healthsentinel")]
        db.feedback.insert_one({
            "question": question,
            "answer": answer,
            "sources_used": [{"text": item.get("text"), "metadata": item.get("metadata")}
                              for item in sources],
            "rating": rating,
            "comment": comment,
            "user": user,
            "timestamp": datetime.now(timezone.utc),
        })
    finally:
        client.close()