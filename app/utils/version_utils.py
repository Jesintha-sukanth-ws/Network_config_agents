"""
Version normalization utility.

Provides a single source of truth for version string normalization
across the RAG pipeline (device state collection, PDF ingestion, retrieval).
"""


def normalize_version(version: str) -> str:
    """
    Normalize version string to major.minor format.
    
    Extracts the first two components (major.minor) from a version string,
    ensuring consistent version matching across device-reported versions
    and PDF metadata stored in ChromaDB.
    
    Examples:
        normalize_version("17.15.01") -> "17.15"
        normalize_version("17.15")    -> "17.15"
        normalize_version("9.3.12")   -> "9.3"
        normalize_version("17")       -> "17"
        normalize_version(None)       -> None
        normalize_version("")         -> ""
    
    Args:
        version: Version string to normalize (e.g., "17.15.01", "9.3.12")
        
    Returns:
        Normalized version string (major.minor) or original value if:
        - version is None or empty
        - version has fewer than 2 components
    """
    if not version:
        return version
    
    parts = version.strip().split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else version
