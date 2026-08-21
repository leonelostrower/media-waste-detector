"""Semantic retrieval and audience similarity helpers."""

from __future__ import annotations

import os
import re
from typing import Iterable

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

REQUEST_TIMEOUT = 20


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    """Split text into overlapping, paragraph-aware chunks."""
    clean = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not clean:
        return []
    paragraphs = [part.strip() for part in clean.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        prefix = current[-overlap:] if current else ""
        current = f"{prefix}\n\n{paragraph}".strip()
        while len(current) > chunk_size:
            chunks.append(current[:chunk_size])
            current = current[chunk_size - overlap :]
    if current:
        chunks.append(current)
    return chunks


def _gemini_embeddings(texts: list[str], task_type: str) -> np.ndarray | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
        response = genai.embed_content(
            model=model,
            content=texts,
            task_type=task_type,
            request_options={"timeout": REQUEST_TIMEOUT, "retry": None},
        )
        return np.asarray(response["embedding"], dtype=float)
    except Exception:
        return None


def embed_texts(texts: Iterable[str], task_type: str = "semantic_similarity") -> np.ndarray:
    """Embed with Gemini when configured, otherwise use a local TF-IDF representation."""
    items = [str(text).strip() for text in texts]
    if not items:
        return np.empty((0, 0))
    gemini = _gemini_embeddings(items, task_type)
    if gemini is not None:
        return gemini
    normalized = [
        text.lower()
        .replace("sneakerheads", "athletic shoes sneakers footwear")
        .replace("sneaker", "athletic shoe")
        for text in items
    ]
    return TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform(
        normalized
    ).toarray()


def similarity_matrix(left: Iterable[str], right: Iterable[str]) -> np.ndarray:
    """Return cosine similarities for two collections in one embedding space."""
    left_items = list(left)
    right_items = list(right)
    if not left_items or not right_items:
        return np.empty((len(left_items), len(right_items)))
    vectors = embed_texts(left_items + right_items)
    split = len(left_items)
    return cosine_similarity(vectors[:split], vectors[split:])


def retrieve_context(query: str, media_plan: str, top_k: int = 3) -> list[str]:
    """Return the most relevant media-plan chunks for a query."""
    chunks = chunk_text(media_plan)
    if not chunks:
        return []
    vectors = embed_texts([query, *chunks], task_type="retrieval_document")
    scores = cosine_similarity(vectors[:1], vectors[1:]).ravel()
    indexes = np.argsort(scores)[::-1][:top_k]
    return [chunks[index] for index in indexes]
