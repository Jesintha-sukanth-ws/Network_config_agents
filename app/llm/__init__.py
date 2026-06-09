"""
LLM Module - Large Language Model Integration

Main Components:
- OllamaClient: Ollama interface
- prompt_template: Prompt construction helpers
- PayloadGenerationService: Structured JSON output generation
"""

from .ollama_client import OllamaClient
from .prompt_template import build_payload_prompt, SYSTEM_PROMPT
from .payload_generation_service import PayloadGenerationService

__all__ = [
    "OllamaClient",
    "build_payload_prompt",
    "SYSTEM_PROMPT",
    "PayloadGenerationService",
]

__version__ = "1.0.0"
