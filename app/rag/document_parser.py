import hashlib
import logging
import re
from pathlib import Path
from typing import List, Dict, Any

import fitz

from app.utils.version_utils import normalize_version


logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Robust PDF parser for RAG ingestion.

    Responsibilities:
    - Read PDF
    - Extract metadata
    - Clean text
    - Remove duplicate content
    - Return structured blocks
    """

    SUPPORTED_METADATA = [
        "VENDOR",
        "VERSION",
        "OS",
        "TOPIC",
        "FEATURE",
        "INTENT"
    ]

    METADATA_PATTERN = re.compile(
        rf"^(?P<key>{'|'.join(SUPPORTED_METADATA)}):\s*(?P<value>.*)$",
        re.IGNORECASE
    )


    def parse(
        self,
        pdf_path: Path
    ) -> List[Dict[str, Any]]:

        pdf_path = Path(pdf_path)

        if not pdf_path.exists():

            raise FileNotFoundError(
                f"{pdf_path} not found"
            )


        blocks = []
        seen_hashes = set()
        global_metadata = {}

        try:

            document = fitz.open(
                str(pdf_path)
            )

            for page_number, page in enumerate(
                document,
                start=1
            ):

                page_blocks = page.get_text(
                    "blocks",
                    sort=True
                )

                for block in page_blocks:

                    raw_text = block[4] if len(block) > 4 else ""

                    # First, try to extract metadata from raw text (before cleaning)
                    # This preserves newlines for multi-line metadata blocks
                    metadata_extracted = self._extract_metadata_from_block(
                        raw_text,
                        global_metadata
                    )

                    # If the entire block was metadata, skip to next block
                    if metadata_extracted:
                        continue

                    text = self._clean(
                        raw_text
                    )

                    if not text:
                        continue

                    # Single-line metadata check (fallback)
                    match = self.METADATA_PATTERN.match(
                        text
                    )

                    if match:
                        key = match.group("key").upper()
                        value = match.group("value").strip()
                        
                        # Normalize VERSION metadata using shared utility
                        if key == "VERSION":
                            value = normalize_version(value)
                        
                        global_metadata[key] = value

                        continue


                    if len(text) < 10:
                        continue


                    content_hash = self._hash(
                        text
                    )

                    if content_hash in seen_hashes:
                        continue


                    seen_hashes.add(
                        content_hash
                    )


                    blocks.append({

                        "content":
                        text,

                        "metadata": {

                            **global_metadata,

                            "page":
                            page_number,

                            "source":
                            pdf_path.name
                        },

                        "hash":
                        content_hash
                    })


            logger.info(
                f"Extracted "
                f"{len(blocks)} blocks "
                f"from {pdf_path.name}"
            )

            return blocks


        except Exception as e:

            logger.exception(
                f"PDF parse failed: {e}"
            )

            raise


        finally:

            if "document" in locals():

                document.close()


    def _clean(
        self,
        text: str
    ) -> str:

        text = re.sub(
            r"[\x00-\x1f\x7f]",
            "",
            text
        )

        return re.sub(
            r"\s+",
            " ",
            text
        ).strip()


    def _extract_metadata_from_block(
        self,
        raw_text: str,
        global_metadata: Dict[str, str]
    ) -> bool:
        """
        Extract metadata from a raw text block that may contain
        multiple metadata lines separated by newlines.
        
        Returns True if the entire block was metadata (should be skipped),
        False otherwise.
        """
        if not raw_text:
            return False
        
        lines = raw_text.strip().split('\n')
        metadata_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            match = self.METADATA_PATTERN.match(line)
            if match:
                key = match.group("key").upper()
                value = match.group("value").strip()
                
                # Normalize VERSION metadata using shared utility
                if key == "VERSION":
                    value = normalize_version(value)
                
                global_metadata[key] = value
                metadata_count += 1
        
        # If all non-empty lines were metadata, consider the block as metadata-only
        non_empty_lines = [l for l in lines if l.strip()]
        return metadata_count > 0 and metadata_count == len(non_empty_lines)


    def _hash(
        self,
        text: str
    ) -> str:

        return hashlib.sha256(
            text.encode(
                "utf-8"
            )
        ).hexdigest()