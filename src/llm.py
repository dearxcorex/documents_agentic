"""DeepSeek LLM integration for LightRAG"""

from typing import Any
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import wrap_embedding_func_with_attrs
from sentence_transformers import SentenceTransformer
import numpy as np

from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    MAX_TOKEN_SIZE,
)

# Initialize embedding model (lazy loading)
_embedding_model = None


def get_embedding_model():
    """Lazy load embedding model"""
    global _embedding_model
    if _embedding_model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


async def deepseek_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, Any]] | None = None,
    keyword_extraction: bool = False,
    **kwargs,
) -> str:
    """
    DeepSeek completion function for LightRAG.

    Uses OpenAI-compatible API with DeepSeek's endpoint.
    Note: DeepSeek doesn't support response_format, so we disable keyword_extraction.
    """
    if history_messages is None:
        history_messages = []

    # DeepSeek doesn't support response_format for structured output
    # So we always set keyword_extraction to False
    return await openai_complete_if_cache(
        model=DEEPSEEK_MODEL,
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        keyword_extraction=False,  # DeepSeek doesn't support response_format
        base_url=DEEPSEEK_BASE_URL,
        api_key=DEEPSEEK_API_KEY,
        **kwargs,
    )


@wrap_embedding_func_with_attrs(
    embedding_dim=EMBEDDING_DIM,
    max_token_size=MAX_TOKEN_SIZE,
    model_name=EMBEDDING_MODEL,
)
async def bge_m3_embed(texts: list[str]) -> np.ndarray:
    """
    BGE-M3 embedding function for Thai text.

    Uses sentence-transformers for local embedding generation.
    """
    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.array(embeddings, dtype=np.float32)
