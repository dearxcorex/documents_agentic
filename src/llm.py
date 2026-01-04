"""DeepSeek LLM integration for LightRAG"""

import asyncio
import logging
from typing import Any

import numpy as np
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import wrap_embedding_func_with_attrs
from sentence_transformers import SentenceTransformer

from .config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    MAX_TOKEN_SIZE,
    LLM_MAX_RETRIES,
    LLM_RETRY_DELAY,
    LLM_TIMEOUT,
)

logger = logging.getLogger(__name__)

# Initialize embedding model (lazy loading)
_embedding_model = None


def get_embedding_model():
    """Lazy load embedding model"""
    global _embedding_model
    if _embedding_model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


class LLMError(Exception):
    """Custom exception for LLM-related errors"""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out"""
    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limited by API"""
    pass


async def deepseek_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict[str, Any]] | None = None,
    keyword_extraction: bool = False,
    max_retries: int | None = None,
    **kwargs,
) -> str:
    """
    DeepSeek completion function for LightRAG with retry logic.

    Uses OpenAI-compatible API with DeepSeek's endpoint.
    Includes exponential backoff retry for transient errors.

    Args:
        prompt: The prompt to send to the LLM
        system_prompt: Optional system prompt
        history_messages: Optional conversation history
        keyword_extraction: Whether to extract keywords (disabled for DeepSeek)
        max_retries: Override default max retries
        **kwargs: Additional arguments passed to the API

    Returns:
        The LLM response text

    Raises:
        LLMTimeoutError: If request times out after all retries
        LLMRateLimitError: If rate limited after all retries
        LLMError: For other LLM-related errors
    """
    if history_messages is None:
        history_messages = []

    retries = max_retries if max_retries is not None else LLM_MAX_RETRIES
    last_error = None

    for attempt in range(retries + 1):
        try:
            logger.debug(f"LLM request attempt {attempt + 1}/{retries + 1}")

            result = await asyncio.wait_for(
                openai_complete_if_cache(
                    model=DEEPSEEK_MODEL,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    keyword_extraction=False,  # DeepSeek doesn't support response_format
                    base_url=DEEPSEEK_BASE_URL,
                    api_key=DEEPSEEK_API_KEY,
                    **kwargs,
                ),
                timeout=LLM_TIMEOUT,
            )

            logger.debug(f"LLM request successful on attempt {attempt + 1}")
            return result

        except asyncio.TimeoutError as e:
            last_error = e
            logger.warning(f"LLM request timeout (attempt {attempt + 1}/{retries + 1})")
            if attempt < retries:
                delay = LLM_RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

        except Exception as e:
            error_str = str(e).lower()

            # Check for rate limiting
            if "rate" in error_str and "limit" in error_str:
                last_error = e
                logger.warning(f"Rate limited (attempt {attempt + 1}/{retries + 1}): {e}")
                if attempt < retries:
                    delay = LLM_RETRY_DELAY * (2 ** attempt) * 2  # Longer delay for rate limits
                    logger.info(f"Rate limited, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                continue

            # Check for transient network errors
            if any(x in error_str for x in ["connection", "network", "timeout", "502", "503", "504"]):
                last_error = e
                logger.warning(f"Transient error (attempt {attempt + 1}/{retries + 1}): {e}")
                if attempt < retries:
                    delay = LLM_RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                continue

            # Non-retryable error
            logger.error(f"LLM error (non-retryable): {e}")
            raise LLMError(f"LLM request failed: {e}") from e

    # All retries exhausted
    if isinstance(last_error, asyncio.TimeoutError):
        raise LLMTimeoutError(f"LLM request timed out after {retries + 1} attempts")
    elif last_error and "rate" in str(last_error).lower():
        raise LLMRateLimitError(f"Rate limited after {retries + 1} attempts")
    else:
        raise LLMError(f"LLM request failed after {retries + 1} attempts: {last_error}")


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
