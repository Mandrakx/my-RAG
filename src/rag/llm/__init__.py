"""
LLM adapters for my-RAG
Supports multiple backends: HuggingFace, Ollama, LM Studio
"""

from .ollama_adapter import OllamaLLM, OllamaConfig, OllamaRAGChain

__all__ = [
    'OllamaLLM',
    'OllamaConfig',
    'OllamaRAGChain'
]
