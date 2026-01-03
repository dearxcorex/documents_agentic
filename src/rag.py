"""LightRAG setup for Thai Document Generation"""

import asyncio
from pathlib import Path
from lightrag import LightRAG, QueryParam

from .config import (
    RAG_WORKING_DIR,
    CHUNK_TOKEN_SIZE,
    CHUNK_OVERLAP_TOKEN_SIZE,
    ADDON_PARAMS,
    DEFAULT_QUERY_MODE,
    ENABLE_RERANK,
    TOP_K,
    CHUNK_TOP_K,
)
from .llm import deepseek_complete, bge_m3_embed

# Global RAG instance
_rag_instance = None


async def get_rag() -> LightRAG:
    """Get or create LightRAG instance (singleton pattern)"""
    global _rag_instance

    if _rag_instance is None:
        # Ensure working directory exists
        Path(RAG_WORKING_DIR).mkdir(parents=True, exist_ok=True)

        _rag_instance = LightRAG(
            working_dir=RAG_WORKING_DIR,
            llm_model_func=deepseek_complete,
            embedding_func=bge_m3_embed,
            chunk_token_size=CHUNK_TOKEN_SIZE,
            chunk_overlap_token_size=CHUNK_OVERLAP_TOKEN_SIZE,
            addon_params=ADDON_PARAMS,
        )

        await _rag_instance.initialize_storages()
        print(f"LightRAG initialized at: {RAG_WORKING_DIR}")

    return _rag_instance


async def close_rag():
    """Close RAG instance and cleanup resources"""
    global _rag_instance

    if _rag_instance is not None:
        await _rag_instance.finalize_storages()
        _rag_instance = None
        print("LightRAG closed")


async def index_documents(documents: list[str]) -> None:
    """Index documents into LightRAG"""
    rag = await get_rag()
    await rag.ainsert(documents)
    print(f"Indexed {len(documents)} documents")


async def index_file(file_path: str) -> None:
    """Index a single file into LightRAG"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    await index_documents([content])
    print(f"Indexed file: {file_path}")


async def index_directory(directory: str, pattern: str = "*.md") -> None:
    """Index all matching files in a directory"""
    path = Path(directory)
    files = list(path.glob(pattern))

    documents = []
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Add metadata header
            content = f"# Source: {file_path.name}\n\n{content}"
            documents.append(content)

    if documents:
        await index_documents(documents)
        print(f"Indexed {len(documents)} files from {directory}")
    else:
        print(f"No files matching {pattern} found in {directory}")


async def query(
    question: str,
    mode: str = DEFAULT_QUERY_MODE,
    only_context: bool = False,
) -> dict | str:
    """
    Query the RAG system.

    Args:
        question: The question to ask
        mode: Query mode (local, global, hybrid, naive, mix, bypass)
        only_context: If True, return only retrieved context without LLM generation

    Returns:
        If only_context=True: dict with entities, relations, chunks
        If only_context=False: str with generated answer
    """
    rag = await get_rag()

    param = QueryParam(
        mode=mode,
        only_need_context=only_context,
        enable_rerank=ENABLE_RERANK,
        top_k=TOP_K,
        chunk_top_k=CHUNK_TOP_K,
    )

    if only_context:
        result = await rag.aquery_data(question, param=param)
        return result.get("context", {})
    else:
        result = await rag.aquery(question, param=param)
        return result


async def get_entities_and_relations(question: str) -> tuple[list, list]:
    """
    Get entities and relations relevant to a question.

    Returns:
        Tuple of (entities, relations)
    """
    context = await query(question, only_context=True)

    entities = context.get("entities", [])
    relations = context.get("relations", [])

    return entities, relations


# CLI interface for testing
if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("Usage:")
            print("  python -m src.rag index <directory>")
            print("  python -m src.rag query <question>")
            return

        command = sys.argv[1]

        if command == "index":
            directory = sys.argv[2] if len(sys.argv) > 2 else "./corpus"
            await index_directory(directory)

        elif command == "query":
            question = " ".join(sys.argv[2:])
            result = await query(question)
            print("\n--- Answer ---")
            print(result)

        await close_rag()

    asyncio.run(main())
