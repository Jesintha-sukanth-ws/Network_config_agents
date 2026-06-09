

"""
ingestion_service.py

Responsibilities:
- Parse documents
- Chunk content
- Generate embeddings
- Store into ChromaDB

Does NOT:
- Resolve collection names
- Perform retrieval
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Any

from app.utils.version_utils import normalize_version
from config.settings import INGEST_BATCH_SIZE


logger = logging.getLogger(__name__)


class IngestionService:


    def __init__(

        self,

        parser,

        chunker,

        embedder,

        chroma_manager
    ):

        self._parser=parser

        self._chunker=chunker

        self._embedder=embedder

        self._chroma=chroma_manager


    def clear_collection(self, collection_name: str) -> Dict:
        """Clear all data from a collection."""
        try:
            self._chroma.clear_collection(collection_name)
            return {
                "collection": collection_name,
                "status": "cleared",
                "message": f"Collection {collection_name} cleared successfully"
            }
        except Exception as e:
            logger.error("Failed to clear collection %s: %s", collection_name, e)
            return {
                "collection": collection_name,
                "status": "error",
                "error": str(e)
            }

    def refresh_collection(self, collection_name: str, documents_dir: Path) -> Dict:
        """Clear collection and re-ingest all matching documents."""
        try:
            # Clear existing data
            clear_result = self.clear_collection(collection_name)
            if clear_result["status"] == "error":
                return clear_result

            # Find and ingest documents
            documents = self._discover_documents_for_collection(collection_name, documents_dir)
            
            if not documents:
                return {
                    "collection": collection_name,
                    "status": "ok",
                    "documents_processed": 0,
                    "total_chunks": 0,
                    "message": "No documents found for collection"
                }

            total_chunks = 0
            processed_docs = []

            for doc_path in documents:
                result = self.ingest_pdf(
                    pdf_path=doc_path,
                    collection_name=collection_name,
                    metadata=self._build_document_metadata(collection_name, doc_path)
                )
                
                if result["status"] == "ok":
                    total_chunks += result["chunks_ingested"]
                    processed_docs.append(result["file"])

            return {
                "collection": collection_name,
                "status": "ok",
                "documents_processed": len(processed_docs),
                "total_chunks": total_chunks,
                "files": processed_docs
            }

        except Exception as e:
            logger.exception("Failed to refresh collection %s", collection_name)
            return {
                "collection": collection_name,
                "status": "error",
                "error": str(e)
            }

    def _discover_documents_for_collection(self, collection_name: str, documents_dir: Path) -> List[Path]:
        """Find documents that belong to a specific collection based on PDF metadata."""
        from app.rag.config import CHROMA_COLLECTIONS, SUPPORTED_DOCUMENT_EXTENSIONS
        
        if collection_name not in CHROMA_COLLECTIONS:
            return []

        documents = []
        if not documents_dir.exists():
            return documents

        collection_config = CHROMA_COLLECTIONS[collection_name]
        target_vendor = collection_config.get("vendor", "").lower()
        target_os = collection_config.get("os", "").lower()

        for file_path in documents_dir.iterdir():
            if file_path.suffix.lower() in SUPPORTED_DOCUMENT_EXTENSIONS:
                try:
                    # Extract metadata from PDF to determine collection mapping
                    pdf_metadata = self._extract_pdf_metadata(file_path)
                    
                    doc_vendor = pdf_metadata.get("VENDOR", "").lower()
                    doc_os = pdf_metadata.get("OS", "").lower()
                    
                    # Primary mapping: Use PDF metadata if available
                    if doc_vendor and doc_os:
                        # Flexible matching for vendor and OS
                        vendor_match = (target_vendor in doc_vendor or doc_vendor in target_vendor or
                                      target_vendor.replace("-", "").replace("_", "") in doc_vendor.replace("-", "").replace("_", "") or
                                      doc_vendor.replace("-", "").replace("_", "") in target_vendor.replace("-", "").replace("_", ""))
                        
                        os_match = (target_os in doc_os or doc_os in target_os or
                                   target_os.replace("-", "").replace("_", "") in doc_os.replace("-", "").replace("_", "") or
                                   doc_os.replace("-", "").replace("_", "") in target_os.replace("-", "").replace("_", ""))
                        
                        if vendor_match and os_match:
                            documents.append(file_path)
                            logger.info(
                                "Mapped %s to %s based on metadata: vendor=%s, os=%s",
                                file_path.name, collection_name, doc_vendor, doc_os
                            )
                            continue
                    
                    # Fallback: Use filename patterns if metadata is missing/unclear
                    filename_lower = file_path.name.lower()
                    if self._matches_collection_by_filename(filename_lower, collection_name):
                        documents.append(file_path)
                        logger.warning(
                            "Mapped %s to %s based on filename (metadata insufficient: vendor=%s, os=%s)",
                            file_path.name, collection_name, doc_vendor or "missing", doc_os or "missing"
                        )
                        
                except Exception as e:
                    logger.error("Failed to process %s: %s", file_path.name, e)
                    continue

        return documents

    def _extract_pdf_metadata(self, pdf_path: Path) -> Dict[str, str]:
        """Extract metadata from PDF without full parsing."""
        try:
            # Parse just the first few pages to extract metadata
            parsed_blocks = self._parser.parse(pdf_path)
            
            # Aggregate metadata from all blocks
            metadata = {}
            for block in parsed_blocks[:10]:  # Check first 10 blocks for metadata
                block_metadata = block.get("metadata", {})
                for key, value in block_metadata.items():
                    if key.upper() in ["VENDOR", "OS", "VERSION", "TOPIC", "FEATURE", "INTENT"] and value:
                        # Handle compound metadata lines like "Cisco OS: IOS-XE VERSION: 17.15.01"
                        if key.upper() == "VENDOR" and ("OS:" in value or "VERSION:" in value):
                            # Parse compound vendor line
                            parts = value.split()
                            vendor_parts = []
                            for i, part in enumerate(parts):
                                if part.upper() in ["OS:", "VERSION:"]:
                                    break
                                vendor_parts.append(part)
                            metadata["VENDOR"] = " ".join(vendor_parts).strip()
                            
                            # Extract OS if present
                            if "OS:" in value:
                                os_match = re.search(r'OS:\s*([^\s]+(?:\s*-\s*[^\s]+)*)', value, re.IGNORECASE)
                                if os_match:
                                    metadata["OS"] = os_match.group(1).strip()
                            
                            # Extract VERSION if present
                            if "VERSION:" in value:
                                version_match = re.search(r'VERSION:\s*([^\s]+)', value, re.IGNORECASE)
                                if version_match:
                                    raw_ver = version_match.group(1).strip()
                                    # Normalize to major.minor using shared utility
                                    norm_ver = normalize_version(raw_ver)
                                    metadata["VERSION"] = norm_ver
                                    metadata["version"] = norm_ver  # Store both for compatibility
                        else:
                            metadata[key.upper()] = value
                        
            return metadata
            
        except Exception as e:
            logger.warning("Failed to extract metadata from %s: %s", pdf_path.name, e)
            return {}

    def _matches_collection_by_filename(self, filename_lower: str, collection_name: str) -> bool:
        """Fallback filename-based collection mapping."""
        if collection_name == "cisco_iosxe":
            return ("iosxe" in filename_lower or "ios-xe" in filename_lower or 
                   ("cisco" in filename_lower and "nxos" not in filename_lower))
        elif collection_name == "cisco_nxos":
            return ("nxos" in filename_lower or "nx-os" in filename_lower)
        return False

    def _build_document_metadata(self, collection_name: str, doc_path: Path) -> Dict[str, Any]:
        """Build metadata for a document based on PDF content and collection."""
        from app.rag.config import CHROMA_COLLECTIONS
        
        collection_metadata = CHROMA_COLLECTIONS.get(collection_name, {})
        
        # Extract metadata from PDF
        pdf_metadata = self._extract_pdf_metadata(doc_path)
        
        # Use PDF metadata if available, fallback to collection defaults
        return {
            "vendor": pdf_metadata.get("VENDOR") or collection_metadata.get("vendor", "Unknown"),
            "os": pdf_metadata.get("OS") or collection_metadata.get("os", "Unknown"),
            "version": pdf_metadata.get("VERSION", ""),
            "topic": pdf_metadata.get("TOPIC", ""),
            "feature": pdf_metadata.get("FEATURE", ""),
            "intent": pdf_metadata.get("INTENT", ""),
            "document": doc_path.name,
            "source": "pdf"
        }

    def ingest_pdf(

        self,

        pdf_path:Path,

        collection_name:str,

        metadata:Dict[str,Any]

    )->Dict:


        try:


            # -----------------------------
            # Parse document
            # -----------------------------

            parsed_blocks=(

                self._parser.parse(
                    pdf_path
                )
            )


            chunks=(

                self._build_chunks(

                    parsed_blocks,

                    metadata
                )
            )


            total_chunks=len(
                chunks
            )


            if total_chunks==0:

                logger.warning(

                    "No chunks extracted "
                    "from %s",

                    pdf_path.name
                )

                return {

                    "file":
                    pdf_path.name,

                    "chunks_ingested":
                    0,

                    "status":
                    "ok"
                }


            # -----------------------------
            # Batch ingestion
            # -----------------------------

            for i in range(

                0,

                total_chunks,

                INGEST_BATCH_SIZE
            ):


                batch=(

                    chunks[
                        i:
                        i+
                        INGEST_BATCH_SIZE
                    ]
                )


                self._ingest_batch(
                    collection_name,
                    batch
                )


            logger.info(

                "Successfully ingested "
                "%d chunks from %s",

                total_chunks,

                pdf_path.name
            )


            return {

                "file":
                pdf_path.name,

                "chunks_ingested":
                total_chunks,

                "status":
                "ok"
            }


        except Exception as e:

            logger.exception(

                "Ingestion failed "
                "for %s",

                pdf_path.name
            )

            return {

                "file":
                str(pdf_path),

                "status":
                "error",

                "error":
                str(e)
            }


    def _build_chunks(

        self,

        parsed_blocks:List[Dict],

        metadata:Dict

    )->List[Dict]:


        chunks=[]


        for block in parsed_blocks:


            split_chunks=(

                self._chunker
                .split_text(

                    block[
                        "content"
                    ]
                )
            )


            for index,text in enumerate(

                split_chunks
            ):


                chunks.append({

                    "content":
                    text,

                    "metadata":{

                        **block[
                            "metadata"
                        ],

                        **metadata
                    },

                    "hash":

                    f"{block['hash']}_{index}"
                })


        return chunks


    def _ingest_batch(

        self,

        collection_name:str,

        batch:List[Dict]

    )->None:


        texts=[]

        ids=[]

        metadatas=[]


        for chunk in batch:

            texts.append(

                chunk[
                    "content"
                ]
            )

            ids.append(

                chunk[
                    "hash"
                ]
            )

            metadatas.append(

                chunk[
                    "metadata"
                ]
            )


        embeddings=(

            self._embedder
            .embed_texts(
                texts
            )
        )


        if len(
            embeddings
        )!=len(texts):

            raise RuntimeError(

                "Embedding count "
                "mismatch"
            )


        self._chroma.upsert_chunks(

            collection_name=
            collection_name,

            ids=ids,

            documents=texts,

            embeddings=
            embeddings,

            metadatas=
            metadatas
        )