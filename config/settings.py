import os
import logging
from pathlib import Path

from dotenv import load_dotenv



BASE_DIR = (Path(__file__).resolve().parent.parent)

load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)


def get_env(key: str,default=None,cast=str,required=False):
    value = os.getenv(key,default)
    if required and (value is None or value == ""):
        raise RuntimeError(
            f"Missing required "
            f"environment variable: {key}")
    try:
        return cast(value)
    except (ValueError,TypeError):
        logger.warning("Invalid value for %s. ""Using default=%s",key,default)
        return default

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
CHROMA_PERSIST_DIR = (DATA_DIR / "chroma")

for path in [DATA_DIR,LOGS_DIR,CHROMA_PERSIST_DIR]:
    path.mkdir(parents=True,exist_ok=True)

SERVICENOW_INSTANCE = get_env("SERVICENOW_INSTANCE",required=True)
SERVICENOW_USERNAME = get_env("SERVICENOW_USERNAME",required=True)
SERVICENOW_PASSWORD = get_env("SERVICENOW_PASSWORD",required=True)

NETWORK_GROUP_ID = get_env("NETWORK_GROUP_ID","")

CMDB_TABLE = get_env("CMDB_TABLE","cmdb_ci_comm")

SERVICENOW_TIMEOUT = get_env("SERVICENOW_TIMEOUT",30,int)
SERVICENOW_SSL_VERIFY = (get_env("SERVICENOW_SSL_VERIFY","0") == "1")


DEVICE_TIMEOUT = get_env("DEVICE_TIMEOUT",30,int)
DEVICE_CREDENTIALS = {

    "Cisco": {
        "username":get_env("CISCO_USERNAME",""),
        "password":get_env("CISCO_PASSWORD","")
    }
}


def parse_boolean(value: str) -> bool:
    """Parse boolean values from environment variables.
    
    Supports: true, false, 1, 0, yes, no (case-insensitive)
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.lower().strip()
        if value in ("true", "1", "yes"):
            return True
        elif value in ("false", "0", "no"):
            return False
    return False


SSL_VERIFY = parse_boolean(get_env("SSL_VERIFY", "false"))


OLLAMA_BASE_URL = get_env(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

OLLAMA_TIMEOUT = get_env("OLLAMA_TIMEOUT",180,int)

INTENT_MODEL = get_env("INTENT_MODEL","gpt-oss:120b-cloud")

PAYLOAD_MODEL = get_env("PAYLOAD_MODEL","qwen2.5:7b")

SERVICENOW_FIELDS_MODEL = get_env("SERVICENOW_FIELDS_MODEL","nemotron-3-ultra:cloud")

LLM_TEMPERATURE = get_env("LLM_TEMPERATURE",0.1,float)

LLM_MAX_TOKENS = get_env("LLM_MAX_TOKENS",1024,int)


EMBEDDING_MODEL = get_env("EMBEDDING_MODEL","sentence-transformers/all-MiniLM-L6-v2")

EMBEDDING_DEVICE = get_env("EMBEDDING_DEVICE","cpu")

CHUNK_SIZE = get_env("CHUNK_SIZE",1000,int)

CHUNK_OVERLAP = get_env("CHUNK_OVERLAP",200,int)

RETRIEVAL_TOP_K = get_env("RETRIEVAL_TOP_K",5,int)

CHROMA_COLLECTIONS = (get_env("CHROMA_COLLECTIONS","network_docs").split(","))


LOG_LEVEL = get_env("LOG_LEVEL","INFO")

DEVICE_DEBUG = (get_env("DEVICE_DEBUG","0") == "1")


POLL_INTERVAL = get_env("POLL_INTERVAL",30,int)



MAX_CONTEXT_CHARS = get_env("MAX_CONTEXT_CHARS",4000,int)

INGEST_BATCH_SIZE = get_env("INGEST_BATCH_SIZE",32,int)

RAG_DISTANCE_THRESHOLD = get_env("RAG_DISTANCE_THRESHOLD",1.5,float)



