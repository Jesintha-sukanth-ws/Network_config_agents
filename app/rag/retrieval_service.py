"""
retrieval_service.py

Resolves the correct ChromaDB collection from device metadata
and performs semantic retrieval. Version is a metadata filter,
never part of the collection name.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.rag.config import (
    RETRIEVAL_TOP_K,
    RAG_DISTANCE_THRESHOLD,
    CHROMA_COLLECTIONS,
)

from app.rag.chroma_manager import ChromaManager
from app.rag.embedding_service import EmbeddingService


logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    content: str
    metadata: Dict
    distance: float
    rank: int


class RetrievalService:

    def __init__(
        self,
        chroma_manager: ChromaManager,
        embedding_service: EmbeddingService,
        top_k: int = RETRIEVAL_TOP_K,
        distance_threshold: float = RAG_DISTANCE_THRESHOLD,
    ):

        self._chroma = chroma_manager
        self._embedder = embedding_service
        self._top_k = top_k
        self._distance_threshold = distance_threshold


    @staticmethod
    def _resolve_collection_name(vendor: str, os_name: str) -> str:
        

        vendor_norm = (vendor or "").strip().lower()
        os_norm = (os_name or "").strip().lower()

        for name, meta in CHROMA_COLLECTIONS.items():
            if (
                meta["vendor"].lower() == vendor_norm
                and meta["os"].lower() == os_norm
            ):
                return name

        raise ValueError(
            f"No Chroma collection registered for "
            f"vendor='{vendor}' os='{os_name}'"
        )

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def retrieve(
        self,
        intent_type: str,
        vendor: str,
        os_name: str,
        version: str,
        query_text: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:

        collection_name = self._resolve_collection_name(vendor, os_name)

        query = (
            query_text
            or f"{vendor} {os_name} {intent_type}"
        )

        query_embedding = self._embedder.embed_query(query)

        # Build metadata filters
        where = {}
        if version:
            # Handle both VERSION and version fields for compatibility
            where["$or"] = [
                {"VERSION": version},
                {"version": version}
            ]
        
        # Add intent filtering if available
        if intent_type:
            # Try to match intent in multiple fields
            intent_filter = {
                "$or": [
                    {"intent": intent_type},
                    {"INTENT": intent_type},
                    {"feature": intent_type},
                    {"FEATURE": intent_type},
                    {"topic": intent_type},
                    {"TOPIC": intent_type}
                ]
            }
            
            if where:
                where = {"$and": [where, intent_filter]}
            else:
                where = intent_filter

        logger.info(
            "Retrieving from collection=%s, intent=%s, filters=%s",
            collection_name, intent_type, where
        )

        results = self._chroma.query(
            collection_name=collection_name,
            query_embeddings=[query_embedding],
            n_results=top_k or self._top_k,
            where=where,
        )

        chunks = self._parse_results(results)
        
        # Log individual retrieved chunks for debugging
        logger.info("Retrieved %d chunks for intent=%s:", len(chunks), intent_type)
        for i, chunk in enumerate(chunks, 1):
            logger.info(
                "  Chunk %d (distance=%.3f): %s... [metadata: %s]",
                i, chunk.distance, chunk.content[:100], 
                {k: v for k, v in chunk.metadata.items() if k in ['intent', 'feature', 'topic', 'document']}
            )

        return chunks

    def retrieve_raw_context(
        self,
        intent_type: str,
        vendor: str,
        os_name: str,
        version: str,
        query_text: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> str:

        chunks = self.retrieve(
            intent_type=intent_type,
            vendor=vendor,
            os_name=os_name,
            version=version,
            query_text=query_text,
            top_k=top_k,
        )

        return "\n\n---\n\n".join(chunk.content for chunk in chunks)

    # ------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------

    def _parse_results(self, raw: Dict) -> List[RetrievedChunk]:

        chunks = []

        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        for rank, (doc, meta, dist) in enumerate(
            zip(documents, metadatas, distances),
            start=1,
        ):
            if dist is not None and dist > self._distance_threshold:
                continue

            chunks.append(
                RetrievedChunk(
                    content=doc,
                    metadata=meta or {},
                    distance=dist,
                    rank=rank,
                )
            )

        return chunks
