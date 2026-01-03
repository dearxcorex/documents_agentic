"""Configuration for Thai Document RAG System"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# DeepSeek API Configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable is required. Set it in .env file.")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # or "deepseek-reasoner" for reasoning

# LightRAG Configuration
RAG_WORKING_DIR = "./rag_storage"
CHUNK_TOKEN_SIZE = 1200
CHUNK_OVERLAP_TOKEN_SIZE = 100

# Embedding Configuration
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024
MAX_TOKEN_SIZE = 8192

# Thai Document Settings
ADDON_PARAMS = {
    "language": "Thai",
    "entity_types": ["organization", "person", "position", "document_type", "location"]
}

# Query Settings
# Note: "naive" mode doesn't require keyword extraction (response_format)
# which DeepSeek doesn't support. Use "mix" only with OpenAI-compatible LLMs.
DEFAULT_QUERY_MODE = "naive"  # Changed from "mix" for DeepSeek compatibility
ENABLE_RERANK = False  # Disabled - requires keyword extraction
TOP_K = 60
CHUNK_TOP_K = 20
