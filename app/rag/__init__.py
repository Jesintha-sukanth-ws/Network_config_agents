"""
RAG Module - Retrieval Augmented Generation

Main Components:
- ChromaManager: Vector database operations
- EmbeddingService: Text embedding generation
- IngestionService: Document processing pipeline
- RetrievalService: Semantic search and retrieval
- ChunkingService: Intelligent text chunking
- DocumentParser: Multi-format document parsing
"""

from .chroma_manager import ChromaManager
from .embedding_service import EmbeddingService
from .ingestion_service import IngestionService
from .retrieval_service import RetrievalService
from .chunking_service import ChunkingService
from .document_parser import DocumentParser

__all__ = [
    "ChromaManager",
    "EmbeddingService",
    "IngestionService",
    "RetrievalService",
    "ChunkingService",
    "DocumentParser",
]

__version__ = "1.0.0"
