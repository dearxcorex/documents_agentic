# Context Engineering & RAG Research for Thai Document Generation

> Research Date: 2026-01-03
> Updated: Replaced LlamaIndex with LightRAG

## Executive Summary

This research explores context engineering and RAG (Retrieval Augmented Generation) techniques to improve accuracy for Thai government document generation.

**Key Decision**: Use **LightRAG** (graph-based RAG) instead of LlamaIndex for better entity-relationship extraction and Thai document structure understanding.

---

## 1. Why LightRAG over LlamaIndex?

| Feature | LightRAG | LlamaIndex |
|---------|----------|------------|
| **Architecture** | Graph-based with entity extraction | Vector-based |
| **Thai Benefit** | Extracts formal phrases, honorifics, departments as entities | Simple chunk retrieval |
| **Query Modes** | 6 modes (local, global, hybrid, mix) | Query engines |
| **Performance** | 67.6% vs 32.4% over NaiveRAG | Standard vector RAG |
| **Storage** | Graph + Vector + KV (3-tier) | Primarily vector |

### LightRAG Advantages for Thai Government Documents

1. **Entity Extraction**: Automatically extracts หน่วยงาน, ตำแหน่ง, คำราชาศัพท์ as entities
2. **Relationship Mapping**: Links departments → positions → document types
3. **Mix Mode**: Combines knowledge graph + vector for best retrieval
4. **Reranker Support**: Better ranking for formal Thai terminology

---

## 2. LightRAG Architecture

### Graph-Based RAG Pipeline

```
Thai Documents → Chunking → Entity/Relation Extraction → Knowledge Graph
                                                              ↓
                                                     Vector Embeddings
                                                              ↓
Query → Dual Retrieval (Graph + Vector) → Rerank → Context → LLM
```

### Three-Tier Storage

| Storage | Options | Recommended |
|---------|---------|-------------|
| **Graph** | NetworkX, Neo4J, PostgreSQL AGE | NetworkX (dev) → PostgreSQL (prod) |
| **Vector** | Chroma, Qdrant, Milvus, pgvector | Chroma (dev) → pgvector (prod) |
| **KV** | JSON, PostgreSQL, Redis | JSON (dev) → PostgreSQL (prod) |

### Six Query Modes

```python
# Best for Thai documents: mix mode with reranker
QueryParam(
    mode="mix",           # Graph + Vector retrieval
    enable_rerank=True,   # Better ranking
    top_k=60,
    chunk_top_k=20
)
```

| Mode | Use Case |
|------|----------|
| `local` | Entity-focused (specific department, person) |
| `global` | Relationship-focused (document flows, hierarchy) |
| `hybrid` | Local + Global combined |
| `naive` | Basic vector search |
| `mix` | **Best**: Knowledge graph + vector + reranker |
| `bypass` | Direct LLM (no retrieval) |

---

## 3. Installation & Setup

```bash
# Install LightRAG
uv pip install lightrag-hku

# With API server
uv pip install "lightrag-hku[api]"

# Required dependencies
uv pip install chromadb pythainlp
```

### Basic Setup

```python
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed

WORKING_DIR = "./thai_rag_storage"

async def setup_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
        chunk_token_size=1200,
        chunk_overlap_token_size=100,
        addon_params={
            "language": "Thai",
            "entity_types": ["organization", "person", "position", "document_type"]
        }
    )
    await rag.initialize_storages()
    return rag
```

---

## 4. Thai Document Indexing

### Index Templates and Examples

```python
async def index_thai_documents(rag):
    """Index Thai government document templates and examples"""

    # Read template files
    templates = [
        open("templates/01_external_letter.md").read(),
        open("templates/02_internal_memo.md").read(),
    ]

    # Read example documents
    examples = [
        open("examples/travel_approval.txt").read(),
        open("examples/budget_request.txt").read(),
    ]

    # Index all documents
    all_docs = templates + examples
    await rag.ainsert(all_docs)

    print(f"Indexed {len(all_docs)} documents")
```

### Entity Extraction for Thai Documents

LightRAG will extract:

```
Entities:
- สำนักงาน กสทช.เขต 23 (organization)
- ผภภ. 23 (position)
- บันทึกข้อความ (document_type)
- นายสมชาย ใจดี (person)

Relations:
- สำนักงาน กสทช.เขต 23 → has_position → ผภภ. 23
- บันทึกข้อความ → sent_to → ผภภ. 23
- นายสมชาย → works_at → สำนักงาน กสทช.เขต 23
```

---

## 5. LangGraph Integration

### LightRAG as Retrieval Node

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
from lightrag import LightRAG, QueryParam

class DocumentState(TypedDict):
    user_request: str
    doc_type: Literal["หนังสือภายนอก", "บันทึกข้อความ"]
    retrieved_context: dict
    entities: list
    relations: list
    draft: str
    validation_errors: list

# Global RAG instance
rag = None

async def init_rag(state: DocumentState) -> DocumentState:
    """Initialize LightRAG once"""
    global rag
    if rag is None:
        rag = LightRAG(
            working_dir="./thai_rag_storage",
            embedding_func=openai_embed,
            llm_model_func=gpt_4o_mini_complete,
        )
        await rag.initialize_storages()
    return state

async def retrieve_context(state: DocumentState) -> DocumentState:
    """LightRAG retrieval with graph + vector"""

    # Get structured data (entities, relations, chunks)
    data = await rag.aquery_data(
        state["user_request"],
        param=QueryParam(
            mode="mix",
            only_need_context=True,  # Just retrieval, no generation
            enable_rerank=True,
            top_k=60
        )
    )

    context = data.get("context", {})

    return {
        **state,
        "retrieved_context": context,
        "entities": context.get("entities", []),
        "relations": context.get("relations", []),
    }

async def generate_draft(state: DocumentState) -> DocumentState:
    """Generate document using Typhoon 2 with retrieved context"""

    prompt = f"""คุณเป็นผู้เชี่ยวชาญในการเขียนหนังสือราชการไทย

บริบทจากเอกสารอ้างอิง:
{state['retrieved_context']}

หน่วยงานที่เกี่ยวข้อง:
{state['entities']}

คำขอ:
{state['user_request']}

สร้างเอกสารตามรูปแบบ {state['doc_type']}:"""

    # Call Typhoon 2 or your LLM
    draft = await typhoon_generate(prompt)

    return {**state, "draft": draft}

# Build workflow
workflow = StateGraph(DocumentState)

workflow.add_node("init", init_rag)
workflow.add_node("retrieve", retrieve_context)
workflow.add_node("generate", generate_draft)
workflow.add_node("validate", validate_document)

workflow.set_entry_point("init")
workflow.add_edge("init", "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "validate")
workflow.add_conditional_edges(
    "validate",
    lambda s: "generate" if s["validation_errors"] else END,
    {"generate": "generate", END: END}
)

app = workflow.compile()
```

---

## 6. Embedding Options for Thai

### Recommended: BGE-M3 (Multilingual)

```python
from lightrag.utils import wrap_embedding_func_with_attrs
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")

@wrap_embedding_func_with_attrs(
    embedding_dim=1024,
    max_token_size=8192,
    model_name="BAAI/bge-m3"
)
async def thai_embed_func(texts: list[str]) -> list[list[float]]:
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()

# Use in LightRAG
rag = LightRAG(
    working_dir="./thai_rag_storage",
    embedding_func=thai_embed_func,
    llm_model_func=your_llm_func,
)
```

### Alternative: WangchanBERTa (Thai-specific)

```python
from transformers import AutoTokenizer, AutoModel
import torch

model_name = "airesearch/wangchanberta-base-att-spm-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

@wrap_embedding_func_with_attrs(
    embedding_dim=768,
    max_token_size=512,
    model_name="wangchanberta"
)
async def wangchan_embed(texts: list[str]) -> list[list[float]]:
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state[:, 0, :].numpy()
    return embeddings.tolist()
```

---

## 7. Reranker for Better Thai Retrieval

```python
# Use BGE reranker for multilingual support
rag = LightRAG(
    working_dir="./thai_rag_storage",
    embedding_func=thai_embed_func,
    llm_model_func=your_llm_func,
    # Add reranker
    rerank_model="BAAI/bge-reranker-v2-m3",
)

# Query with reranking enabled
result = await rag.aquery(
    "ขอตัวอย่างบันทึกข้อความขออนุมัติเดินทาง",
    param=QueryParam(
        mode="mix",
        enable_rerank=True,  # Enable reranking
        top_k=60,
        chunk_top_k=20
    )
)
```

---

## 8. Production Setup with PostgreSQL

```python
import os

# Set environment variables
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "thai_documents"
os.environ["POSTGRES_USER"] = "user"
os.environ["POSTGRES_PASSWORD"] = "password"

# Production LightRAG setup
rag = LightRAG(
    working_dir="./thai_production",
    kv_storage="PGKVStorage",
    vector_storage="PGVectorStorage",
    graph_storage="PGGraphStorage",
    embedding_func=thai_embed_func,
    llm_model_func=gpt_4o_complete,
)
```

---

## 9. Complete Architecture

```
+------------------------------------------------------------------+
|                        USER INTERFACE                             |
+------------------------------------------------------------------+
                               ↓
+------------------------------------------------------------------+
|                     LANGGRAPH ORCHESTRATOR                        |
|  Classify → Retrieve (LightRAG) → Generate (Typhoon 2) → Validate|
+------------------------------------------------------------------+
                               ↓
+------------------------------------------------------------------+
|                         LIGHTRAG                                  |
|  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              |
|  │ Knowledge   │  │   Vector    │  │    KV       │              |
|  │ Graph       │  │   Store     │  │   Store     │              |
|  │ (entities,  │  │ (BGE-M3     │  │  (chunks,   │              |
|  │  relations) │  │  embeddings)│  │   metadata) │              |
|  └─────────────┘  └─────────────┘  └─────────────┘              |
+------------------------------------------------------------------+
                               ↓
+------------------------------------------------------------------+
|                      DOCUMENT CORPUS                              |
|  templates/ │ examples/ │ terminology/ │ regulations/            |
+------------------------------------------------------------------+
```

---

## 10. Implementation Phases

### Phase 1: LightRAG Foundation
- [ ] Install lightrag-hku with dependencies
- [ ] Set up BGE-M3 or WangchanBERTa embeddings
- [ ] Initialize LightRAG with JSON storage (dev)
- [ ] Index existing templates

### Phase 2: Document Corpus
- [ ] Collect 10-20 example documents per type
- [ ] Structure corpus with entity metadata
- [ ] Index all documents with entity extraction
- [ ] Verify entity/relation extraction quality

### Phase 3: LangGraph Integration
- [ ] Create retrieval node using LightRAG
- [ ] Implement mix mode with reranker
- [ ] Add entity-aware prompt construction
- [ ] Test end-to-end workflow

### Phase 4: Production
- [ ] Migrate to PostgreSQL storage
- [ ] Add monitoring and metrics
- [ ] Evaluate retrieval quality
- [ ] Fine-tune reranker weights

---

## Key Takeaways

1. **LightRAG > LlamaIndex** for Thai documents due to entity-relationship extraction
2. **Mix Mode + Reranker** provides best retrieval quality
3. **BGE-M3** embedding recommended for Thai multilingual support
4. **Graph Storage** captures formal Thai document structure
5. **Three-Tier Storage** enables flexible production deployment
6. **Entity Extraction** automatically captures หน่วยงาน, ตำแหน่ง, คำราชาศัพท์

---

## Resources

- [LightRAG GitHub](https://github.com/HKUDS/LightRAG)
- [LightRAG Paper (EMNLP 2025)](https://arxiv.org/abs/2410.05779)
- [BGE-M3 Embedding](https://huggingface.co/BAAI/bge-m3)
- [WangchanBERTa](https://airesearch.in.th/releases/wangchanberta-pre-trained-thai-language-model/)
- [PyThaiNLP](https://pythainlp.org/)
