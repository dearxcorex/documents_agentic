"""Thai Document RAG System with LightRAG"""

from .config import *
from .llm import deepseek_complete, bge_m3_embed
from .rag import (
    get_rag,
    close_rag,
    index_documents,
    index_file,
    index_directory,
    query,
    get_entities_and_relations,
)

__all__ = [
    "deepseek_complete",
    "bge_m3_embed",
    "get_rag",
    "close_rag",
    "index_documents",
    "index_file",
    "index_directory",
    "query",
    "get_entities_and_relations",
]
