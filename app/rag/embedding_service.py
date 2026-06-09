"""
embedding_service.py

Encapsulates sentence-transformer embedding generation.

Responsibilities:
- Lazy-load the embedding model
- Embed individual queries
- Embed batches of texts
"""

from __future__ import annotations

import logging
from typing import List

from sentence_transformers import SentenceTransformer

from config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_DEVICE,
)


logger = logging.getLogger(__name__)


class EmbeddingService:

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        device: str = EMBEDDING_DEVICE,
    ) -> None:

        logger.info(
            "Loading embedding model %s on %s",
            model_name,
            device,
        )

        self._model = SentenceTransformer(
            model_name,
            device=device,
        )

    def embed_query(self, text: str) -> List[float]:

        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        vector = self._model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return vector.tolist()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:

        if not texts:
            return []

        vectors = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return [v.tolist() for v in vectors]
