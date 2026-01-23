# CLAUDE.md - Thai Document RAG System

## Project Overview

This is a **Thai Government Document Generation System** that uses RAG (Retrieval-Augmented Generation) with LightRAG and DeepSeek LLM to automatically generate formal Thai government documents. The system combines knowledge graph-based retrieval with intelligent document generation using LangGraph workflows.

**Primary Use Case**: Generate Thai bureaucratic documents (internal memos, external letters, meeting minutes) with proper formatting and structure according to Thai government standards.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     LangGraph Workflow                       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │ Classify │ → │ Retrieve │ → │ Generate │ → │ Validate │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│                      ↑                             │        │
│                      └─────────────────────────────┘        │
│                              (retry loop)                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   LightRAG    │   │   DeepSeek LLM  │   │   BGE-M3        │
│ (Knowledge    │   │ (Text Gen)      │   │ (Embeddings)    │
│  Graph RAG)   │   │                 │   │                 │
└───────────────┘   └─────────────────┘   └─────────────────┘
```

## Project Structure

```
/home/user/documents_agentic/
├── src/                        # Main source code
│   ├── __init__.py            # Module exports
│   ├── config.py              # Central configuration (env, constants)
│   ├── categories.py          # Document category definitions (Pydantic)
│   ├── llm.py                 # DeepSeek LLM + BGE-M3 embeddings
│   ├── rag.py                 # LightRAG setup and operations
│   ├── templates.py           # 13 Thai document templates
│   └── workflow.py            # LangGraph orchestration (main entry)
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── .gitignore                 # Git exclusions
└── CLAUDE.md                  # This file
```

## Key Files

| File | Purpose | Entry Point |
|------|---------|-------------|
| `src/workflow.py` | Main document generation workflow | `python -m src.workflow` |
| `src/rag.py` | RAG indexing and querying | `python -m src.rag` |
| `src/config.py` | All configuration constants | N/A (imported) |
| `src/categories.py` | 3 document categories with validation | N/A (imported) |
| `src/templates.py` | Document templates with placeholders | N/A (imported) |
| `src/llm.py` | LLM/embedding functions | N/A (imported) |

## Setup

1. **Clone and create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your DEEPSEEK_API_KEY
   ```

## Running the System

### Interactive Document Generation
```bash
python -m src.workflow
```

### Command Line Document Generation
```bash
# Auto-classify category
python -m src.workflow "ขออนุมัติเดินทางไปราชการจังหวัดเชียงใหม่"

# Specify category (1=ภายใน, 2=ภายนอก, 3=ประชุม)
python -m src.workflow -c 1 "รายงานผลการตรวจสอบคลื่นความถี่"
```

### RAG Operations
```bash
# Index documents
python -m src.rag index ./corpus

# Query RAG
python -m src.rag query "ตัวอย่างบันทึกข้อความขออนุมัติ"
```

## Document Categories

| Category | Thai Name | Description |
|----------|-----------|-------------|
| `หนังสือภายใน` | Internal Memo | บันทึกข้อความ - approvals, reports, invitations |
| `หนังสือภายนอก` | External Letter | Correspondence with external organizations |
| `รายงานการประชุม` | Meeting Minutes | Committee/working group meeting records |

## Code Conventions

### Python Style
- **Type hints**: Use throughout (`TypedDict`, `Literal`, `Optional`)
- **Async/await**: All LLM and RAG operations are async
- **Pydantic**: Use for data validation (`BaseModel`, `Field`, `field_validator`)
- **Logging**: Use `logging` module, not print() for debugging
- **Docstrings**: Required for public functions

### Error Handling
- Custom exceptions in `llm.py`: `LLMError`, `LLMTimeoutError`, `LLMRateLimitError`
- Exponential backoff retry for LLM calls (configured in `config.py`)
- Graceful fallbacks when RAG context is insufficient

### Thai Language Handling
- Use Thai numerals for document numbering: ๑. ๒. ๓. (not 1. 2. 3.)
- Use Buddhist Era year (พ.ศ.): ๒๕๖๘ (not 2025)
- Official language: formal, polite (ราชการ)
- UTF-8 encoding for all Thai text

### Configuration
All magic numbers and settings are centralized in `config.py`:
```python
# LLM Settings
LLM_MAX_RETRIES = 3
LLM_RETRY_DELAY = 1.0
LLM_TIMEOUT = 60.0

# RAG Settings
CHUNK_TOKEN_SIZE = 1200
DEFAULT_QUERY_MODE = "naive"  # DeepSeek compatible

# Document Generation
MAX_VALIDATION_RETRIES = 3
MIN_DOCUMENT_LENGTH = 200
```

### Template Placeholders
Templates use `[PLACEHOLDER_NAME]` format:
- `[SUBJECT]` - Document subject
- `[RECIPIENT]` - Addressee
- `[BODY]` - Main content
- `[DATE]` - Date in Thai format
- `[DOC_NUMBER]` - Official document number

The LLM must replace ALL placeholders - validation fails if any `[...]` remain.

## Workflow State

The `DocumentState` TypedDict tracks:
```python
class DocumentState(TypedDict):
    user_request: str              # Input from user
    category: Optional[CategoryType]  # Document type
    rag_context: str               # Retrieved context
    rag_examples: list[str]        # Example documents
    draft: str                     # Generated document
    validation_errors: list[str]   # Validation issues
    retry_count: int               # Retry attempts
    is_valid: bool                 # Validation passed
    final_document: str            # Output
```

## Validation Rules

Documents are validated for:
1. No unreplaced `[PLACEHOLDER]` tokens
2. All required sections present (per category)
3. User-provided data incorporated (location, doc number, etc.)
4. Minimum document length (200 chars)
5. Content pattern matching (e.g., must have "เรื่องเพื่อพิจารณา" OR "ข้อเท็จจริง")

## Dependencies

| Package | Purpose |
|---------|---------|
| `lightrag-hku>=1.4.0` | Knowledge graph RAG engine |
| `openai>=2.0.0` | OpenAI-compatible API client |
| `sentence-transformers>=5.0.0` | BGE-M3 Thai embeddings |
| `langgraph>=0.2.0` | Workflow orchestration |
| `pydantic>=2.0.0` | Data validation |
| `python-dotenv>=1.0.0` | Environment variables |

## Important Notes for AI Assistants

### Do
- Always use async/await for LLM and RAG operations
- Validate with Pydantic models when adding new data structures
- Add appropriate logging for debugging
- Follow the existing state machine pattern for workflow changes
- Use Thai language in prompts to LLM for better results
- Keep configuration in `config.py`

### Don't
- Don't use `response_format` parameter with DeepSeek (not supported)
- Don't use "mix" query mode - use "naive" for DeepSeek compatibility
- Don't hardcode API keys - always use environment variables
- Don't skip validation step when modifying document generation
- Don't create files in `rag_storage/` manually (auto-generated)

### Testing Changes
1. Run interactive mode: `python -m src.workflow`
2. Test with different categories
3. Verify generated documents have no `[PLACEHOLDER]` tokens
4. Check logs for any errors or warnings

## Git Workflow

- Branch naming: `feat/feature-name`, `fix/bug-description`
- Commit messages: `feat:`, `fix:`, `docs:`, `refactor:` prefixes
- PRs merged to main branch

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | Yes | DeepSeek API key for LLM |

## Common Issues

1. **Empty document generated**: Check LLM API connectivity and rate limits
2. **Validation fails repeatedly**: Check if user data extraction regex matches input format
3. **RAG returns no context**: Ensure documents are indexed first
4. **Thai encoding issues**: Verify UTF-8 encoding in all file operations
