"""
RAG Configuration

Centralized configuration for the
Retrieval-Augmented Generation system.

Single source of truth:
- collection names are static (vendor + os family)
- device version is metadata only, never part of a collection name
- topic keywords come from the intent registry
"""

from pathlib import Path

from config.settings import (
    EMBEDDING_MODEL,
    EMBEDDING_DEVICE,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    MAX_CONTEXT_CHARS,
    RETRIEVAL_TOP_K,
    RAG_DISTANCE_THRESHOLD,
    INGEST_BATCH_SIZE,
)

from app.registry.intent_registry import (
    CANONICAL_INTENT_SCHEMAS,
)


# ----------------------------------------------------
# Supported Intent Types (derived from registry)
# ----------------------------------------------------

SUPPORTED_INTENT_TYPES = list(
    CANONICAL_INTENT_SCHEMAS.keys()
)



BASE_DIR = (
    Path(__file__).resolve().parent.parent.parent
)

DATA_DIR = BASE_DIR / "data"

DOCUMENTS_DIR = DATA_DIR / "documents"

CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"


CHROMA_COLLECTIONS = {

    "cisco_iosxe": {
        "vendor": "Cisco",
        "os": "IOS-XE",
    },

    "cisco_nxos": {
        "vendor": "Cisco",
        "os": "NX-OS",
    },
}



TOPIC_KEYWORDS = {

    intent: schema.get("keywords", [])

    for intent, schema in CANONICAL_INTENT_SCHEMAS.items()
}



SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".md",
    ".txt",
}


__all__ = [
    "EMBEDDING_MODEL",
    "EMBEDDING_DEVICE",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "MAX_CONTEXT_CHARS",
    "RETRIEVAL_TOP_K",
    "RAG_DISTANCE_THRESHOLD",
    "INGEST_BATCH_SIZE",
    "SUPPORTED_INTENT_TYPES",
    "BASE_DIR",
    "DATA_DIR",
    "DOCUMENTS_DIR",
    "CHROMA_PERSIST_DIR",
    "CHROMA_COLLECTIONS",
    "TOPIC_KEYWORDS",
    "SUPPORTED_DOCUMENT_EXTENSIONS",
]
