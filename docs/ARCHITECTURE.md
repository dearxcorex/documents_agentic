# หลักการทำงานของระบบสร้างเอกสารราชการไทย

## สารบัญ

1. [ภาพรวมระบบ](#1-ภาพรวมระบบ)
2. [สถาปัตยกรรมระบบ](#2-สถาปัตยกรรมระบบ)
3. [องค์ประกอบหลัก](#3-องค์ประกอบหลัก)
4. [ขั้นตอนการทำงานโดยละเอียด](#4-ขั้นตอนการทำงานโดยละเอียด)
5. [เทคนิคและ Design Patterns](#5-เทคนิคและ-design-patterns)
6. [Data Flow](#6-data-flow)
7. [สรุป Flow Diagram](#7-สรุป-flow-diagram)

---

## 1. ภาพรวมระบบ

### 1.1 วัตถุประสงค์
ระบบนี้ออกแบบมาเพื่อ **สร้างเอกสารราชการไทยอัตโนมัติ** โดยใช้เทคโนโลยี AI ประกอบด้วย:
- **RAG (Retrieval-Augmented Generation)**: ค้นหาเอกสารตัวอย่างที่เกี่ยวข้อง
- **LLM (Large Language Model)**: สร้างเนื้อหาเอกสาร
- **Knowledge Graph**: เก็บความสัมพันธ์ระหว่างข้อมูล

### 1.2 ประเภทเอกสารที่รองรับ

| ประเภท | ชื่อภาษาอังกฤษ | ตัวอย่างการใช้งาน |
|--------|---------------|------------------|
| หนังสือภายใน | Internal Memo | ขออนุมัติ, รายงานผล, เชิญประชุม |
| หนังสือภายนอก | External Letter | เชิญตรวจร่วม, ขอรื้อถอน, ขอขยายสัญญาณ |
| รายงานการประชุม | Meeting Minutes | บันทึกการประชุมคณะกรรมการ |

### 1.3 Technology Stack

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  LangGraph  │  │   Pydantic  │  │  Python 3.10+   │ │
│  │  Workflow   │  │  Validation │  │  Async/Await    │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                      AI/ML Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  LightRAG   │  │  DeepSeek   │  │    BGE-M3       │ │
│  │  (KG-RAG)   │  │  (LLM API)  │  │  (Embeddings)   │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                     Storage Layer                        │
│  ┌─────────────────────────────────────────────────────┐│
│  │              rag_storage/ (Local Files)              ││
│  │    - Knowledge Graph    - Vector Store    - Cache   ││
│  └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

---

## 2. สถาปัตยกรรมระบบ

### 2.1 High-Level Architecture

```
                           ┌─────────────────┐
                           │   User Input    │
                           │  (คำขอภาษาไทย)  │
                           └────────┬────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                        LangGraph Workflow                          │
│                                                                    │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│   │ CLASSIFY │───▶│ RETRIEVE │───▶│ GENERATE │───▶│ VALIDATE │   │
│   │          │    │          │    │          │    │          │   │
│   │ จำแนก    │    │ ค้นหา    │    │ สร้าง    │    │ ตรวจสอบ  │   │
│   │ ประเภท   │    │ ตัวอย่าง │    │ เอกสาร   │    │ ความถูก  │   │
│   └──────────┘    └──────────┘    └──────────┘    └─────┬────┘   │
│                                         ▲                │        │
│                                         │    ┌───────────┴───┐    │
│                                         │    │  should_retry │    │
│                                         │    └───────┬───────┘    │
│                                         │            │            │
│                                         │     ┌──────┴──────┐     │
│                                    retry│     │             │     │
│                                         │   ไม่ผ่าน       ผ่าน    │
│                                         │  (< 3 ครั้ง)     │     │
│                                         └─────┘            │      │
│                                                            ▼      │
│                                                    ┌───────────┐  │
│                                                    │    END    │  │
│                                                    └───────────┘  │
└───────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                           ┌─────────────────┐
                           │  Final Document │
                           │  (เอกสารสำเร็จ)  │
                           └─────────────────┘
```

### 2.2 Module Dependencies

```
workflow.py (Main Orchestrator)
     │
     ├──────────────┬──────────────┬──────────────┐
     │              │              │              │
     ▼              ▼              ▼              ▼
 rag.py        llm.py      categories.py   templates.py
     │              │              │              │
     │              │              │              │
     ▼              ▼              ▼              ▼
config.py ◄────────┴──────────────┴──────────────┘
     │
     ▼
  .env (Environment Variables)
```

---

## 3. องค์ประกอบหลัก

### 3.1 Config Module (`config.py`)

**หน้าที่**: ศูนย์กลางการตั้งค่าทั้งหมด

```python
# LLM Configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # API Key จาก .env
DEEPSEEK_BASE_URL = "https://api.deepseek.com"    # Endpoint
DEEPSEEK_MODEL = "deepseek-chat"                   # Model name

# Retry Configuration
LLM_MAX_RETRIES = 3      # จำนวนครั้งที่ retry
LLM_RETRY_DELAY = 1.0    # delay เริ่มต้น (วินาที)
LLM_TIMEOUT = 60.0       # timeout ต่อ request

# RAG Configuration
RAG_WORKING_DIR = "./rag_storage"    # ที่เก็บ Knowledge Graph
CHUNK_TOKEN_SIZE = 1200              # ขนาด chunk
CHUNK_OVERLAP_TOKEN_SIZE = 100       # overlap ระหว่าง chunk

# Embedding Configuration
EMBEDDING_MODEL = "BAAI/bge-m3"      # Model สำหรับภาษาไทย
EMBEDDING_DIM = 1024                  # มิติของ vector

# Document Generation
MAX_VALIDATION_RETRIES = 3           # retry validation สูงสุด
MIN_DOCUMENT_LENGTH = 200            # ความยาวขั้นต่ำ (ตัวอักษร)
```

**Design Pattern**: **Centralized Configuration** - รวมค่า config ไว้ที่เดียว ง่ายต่อการปรับแต่ง

---

### 3.2 Categories Module (`categories.py`)

**หน้าที่**: กำหนดประเภทเอกสารและกฎการตรวจสอบ

```python
# Type Definition ด้วย Literal
CategoryType = Literal[
    "หนังสือภายใน",      # Internal memo
    "หนังสือภายนอก",     # External letter
    "รายงานการประชุม",   # Meeting minutes
]

# Pydantic Model สำหรับ Validation
class CategoryInfo(BaseModel):
    name: str = Field(..., min_length=1)
    name_en: str = Field(..., min_length=1)
    description: str
    keywords: list[str]           # คำสำคัญสำหรับจำแนก
    required_sections: list[str]  # ส่วนที่ต้องมี
    optional_sections: list[str]  # ส่วนเสริม
```

**ตัวอย่างข้อมูล Category**:

```python
"หนังสือภายใน": {
    "name": "หนังสือภายใน",
    "name_en": "Internal Memo",
    "keywords": ["บันทึกข้อความ", "ขออนุมัติ", "รายงาน", ...],
    "required_sections": [
        "บันทึกข้อความ",  # Header
        "ส่วนราชการ",     # หน่วยงาน
        "ที่",            # เลขที่หนังสือ
        "วันที่",         # วันที่
        "เรื่อง",         # หัวเรื่อง
        "เรียน",          # ผู้รับ
        "เรื่องเดิม",     # ความเป็นมา
    ],
}
```

---

### 3.3 LLM Module (`llm.py`)

**หน้าที่**: จัดการการเรียกใช้ LLM และ Embedding

#### 3.3.1 DeepSeek Complete Function

```python
async def deepseek_complete(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list[dict] | None = None,
    max_retries: int | None = None,
) -> str:
```

**กระบวนการทำงาน**:

```
┌─────────────────────────────────────────────────────────────┐
│                    deepseek_complete()                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   attempt = 0                                                │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────────┐                                       │
│   │  Send Request   │◄──────────────────────┐               │
│   │  to DeepSeek    │                       │               │
│   └────────┬────────┘                       │               │
│            │                                │               │
│            ▼                                │               │
│   ┌─────────────────┐                       │               │
│   │    Success?     │                       │               │
│   └────────┬────────┘                       │               │
│            │                                │               │
│      ┌─────┴─────┐                          │               │
│      │           │                          │               │
│     Yes          No                         │               │
│      │           │                          │               │
│      ▼           ▼                          │               │
│  ┌───────┐  ┌─────────────────┐             │               │
│  │Return │  │  Error Type?    │             │               │
│  │Result │  └────────┬────────┘             │               │
│  └───────┘           │                      │               │
│                ┌─────┴─────┬─────────┐      │               │
│                │           │         │      │               │
│             Timeout    Rate Limit  Network  │               │
│                │           │         │      │               │
│                └─────┬─────┴─────────┘      │               │
│                      │                      │               │
│                      ▼                      │               │
│              ┌───────────────┐              │               │
│              │ attempt < 3?  │              │               │
│              └───────┬───────┘              │               │
│                      │                      │               │
│                ┌─────┴─────┐                │               │
│               Yes          No               │               │
│                │           │                │               │
│                ▼           ▼                │               │
│         ┌──────────┐  ┌─────────┐           │               │
│         │  Sleep   │  │  Raise  │           │               │
│         │ 2^n sec  │──┘LLMError │           │               │
│         └────┬─────┘  └─────────┘           │               │
│              │                              │               │
│              └──────────────────────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Exponential Backoff**:
- ครั้งที่ 1: รอ 1 วินาที
- ครั้งที่ 2: รอ 2 วินาที
- ครั้งที่ 3: รอ 4 วินาที
- Rate Limit: รอ x2 (2, 4, 8 วินาที)

#### 3.3.2 BGE-M3 Embedding Function

```python
@wrap_embedding_func_with_attrs(
    embedding_dim=1024,
    max_token_size=8192,
    model_name="BAAI/bge-m3",
)
async def bge_m3_embed(texts: list[str]) -> np.ndarray:
    model = get_embedding_model()  # Lazy loading
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.array(embeddings, dtype=np.float32)
```

**ทำไมใช้ BGE-M3?**
- รองรับภาษาไทยได้ดี (Multilingual)
- มิติ 1024 ให้ความแม่นยำสูง
- รองรับ token สูงสุด 8192

---

### 3.4 RAG Module (`rag.py`)

**หน้าที่**: จัดการ Knowledge Graph และการค้นหา

#### 3.4.1 LightRAG Initialization

```python
async def get_rag() -> LightRAG:
    global _rag_instance

    if _rag_instance is None:
        _rag_instance = LightRAG(
            working_dir="./rag_storage",
            llm_model_func=deepseek_complete,  # ใช้ LLM สกัด entities
            embedding_func=bge_m3_embed,       # ใช้ embedding ค้นหา
            chunk_token_size=1200,
            addon_params={
                "language": "Thai",
                "entity_types": ["organization", "person", "position",
                                "document_type", "location"]
            },
        )
        await _rag_instance.initialize_storages()

    return _rag_instance
```

#### 3.4.2 Knowledge Graph vs Traditional RAG

```
┌─────────────────────────────────────────────────────────────────┐
│                     Traditional RAG                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Document → Chunking → Embedding → Vector Store                 │
│                                                                  │
│   Query → Embedding → Similarity Search → Top-K Chunks           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    LightRAG (Knowledge Graph)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Document → Chunking → LLM Extract → Entities + Relations       │
│                    │                         │                   │
│                    ▼                         ▼                   │
│             Embedding Store          Knowledge Graph             │
│                    │                         │                   │
│                    └──────────┬──────────────┘                   │
│                               ▼                                  │
│   Query → Multi-hop Reasoning → Context with Relationships       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**ข้อดีของ Knowledge Graph RAG**:
1. เข้าใจความสัมพันธ์ระหว่างข้อมูล
2. ตอบคำถามแบบ multi-hop ได้
3. ให้ context ที่มีความหมายมากกว่า

#### 3.4.3 Query Modes

| Mode | คำอธิบาย | เหมาะกับ |
|------|---------|---------|
| `naive` | ค้นหาแบบตรงไปตรงมา | DeepSeek (ใช้เป็น default) |
| `local` | ค้นหาจาก entities ใกล้เคียง | คำถามเฉพาะเจาะจง |
| `global` | ค้นหาจาก community summaries | คำถามกว้าง |
| `hybrid` | ผสม local + global | คำถามทั่วไป |

---

### 3.5 Templates Module (`templates.py`)

**หน้าที่**: เก็บ template เอกสารและ placeholder

#### 3.5.1 Template Structure

```python
DRAFT_INTERNAL_REQUEST = """บันทึกข้อความ

ส่วนราชการ  [AGENCY]
ที่         [DOC_NUMBER]                    วันที่ [DATE]
เรื่อง      [SUBJECT]

เรียน  [RECIPIENT]

        เรื่องเดิม
                [BACKGROUND]

        เรื่องเพื่อพิจารณา
                [CONSIDERATION_ITEMS]

        จึงเรียนมาเพื่อโปรดพิจารณา[APPROVAL_REQUEST]

                                        [SIGNATURE_BLOCK]
"""
```

#### 3.5.2 Placeholder System

```python
PLACEHOLDERS = {
    "AGENCY": {
        "description": "ชื่อส่วนราชการ/หน่วยงาน",
        "example": "สำนักงาน กสทช.",
        "required": True,
    },
    "DOC_NUMBER": {
        "description": "เลขที่หนังสือ",
        "example": "สทช ๑๒๓๔/๒๕๖๘",
        "required": True,
    },
    "DATE": {
        "description": "วันที่ในรูปแบบไทย",
        "example": "๑๕ มกราคม ๒๕๖๘",
        "required": True,
    },
    # ... more placeholders
}
```

**การทำงาน**:
1. เลือก template ตามประเภทเอกสาร
2. LLM อ่าน placeholder descriptions
3. LLM แทนที่ `[PLACEHOLDER]` ด้วยเนื้อหาจริง
4. Validation ตรวจว่าไม่มี `[...]` เหลือ

---

### 3.6 Workflow Module (`workflow.py`)

**หน้าที่**: ควบคุม flow การสร้างเอกสารทั้งหมด

#### 3.6.1 Document State

```python
class DocumentState(TypedDict):
    # Input
    user_request: str                    # คำขอจากผู้ใช้
    category: Optional[CategoryType]     # ประเภทที่เลือก (ถ้ามี)

    # Classification
    auto_category: Optional[CategoryType]  # ประเภทที่ AI จำแนก
    classification_confidence: float       # ความมั่นใจ (0.0-1.0)

    # RAG Retrieved
    rag_context: str                     # context จาก RAG
    rag_examples: list[str]              # ตัวอย่างเอกสาร
    entities: list                       # entities ที่พบ
    relations: list                      # ความสัมพันธ์

    # Generation
    draft: str                           # เอกสารที่สร้าง

    # Validation
    validation_errors: list[str]         # ข้อผิดพลาด
    retry_count: int                     # จำนวนครั้งที่ retry
    is_valid: bool                       # ผ่าน/ไม่ผ่าน

    # Output
    final_document: str                  # เอกสารสุดท้าย
```

---

## 4. ขั้นตอนการทำงานโดยละเอียด

### 4.1 Node 1: Classify Category

**ไฟล์**: `workflow.py` บรรทัด 65-113

**หน้าที่**: จำแนกประเภทเอกสารจากคำขอผู้ใช้

```
┌─────────────────────────────────────────────────────────────┐
│                    classify_category()                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Input: user_request = "ขออนุมัติเดินทางไปราชการ..."        │
│                                                              │
│                       │                                      │
│                       ▼                                      │
│              ┌────────────────┐                              │
│              │ มี category    │                              │
│              │ ที่เลือกแล้ว?   │                              │
│              └───────┬────────┘                              │
│                      │                                       │
│               ┌──────┴──────┐                                │
│              Yes            No                               │
│               │             │                                │
│               ▼             ▼                                │
│         ┌─────────┐   ┌─────────────────┐                   │
│         │ ใช้ค่า   │   │ ส่ง prompt ไป   │                   │
│         │ ที่เลือก │   │ LLM เพื่อจำแนก  │                   │
│         └─────────┘   └────────┬────────┘                   │
│                                │                             │
│                                ▼                             │
│                    ┌─────────────────────┐                   │
│                    │ Parse LLM Response  │                   │
│                    │ หา category name    │                   │
│                    └────────┬────────────┘                   │
│                             │                                │
│                             ▼                                │
│                    ┌─────────────────────┐                   │
│                    │  พบ category?       │                   │
│                    └────────┬────────────┘                   │
│                             │                                │
│                      ┌──────┴──────┐                         │
│                     Yes            No                        │
│                      │             │                         │
│                      ▼             ▼                         │
│              confidence=0.8   confidence=0.5                 │
│                      │        default="หนังสือภายใน"         │
│                      │             │                         │
│                      └──────┬──────┘                         │
│                             │                                │
│                             ▼                                │
│   Output: category, auto_category, classification_confidence │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Prompt ที่ใช้**:
```
คุณเป็นผู้เชี่ยวชาญในการจำแนกประเภทหนังสือราชการไทย

จากคำขอของผู้ใช้ด้านล่าง ให้จำแนกว่าเป็นหนังสือประเภทใด:

1. หนังสือภายใน - บันทึกข้อความภายในหน่วยงาน
2. หนังสือภายนอก - หนังสือติดต่อภายนอกหน่วยงาน
3. รายงานการประชุม - บันทึกรายงานการประชุม

คำขอ: {user_request}

ตอบเฉพาะชื่อประเภท:
```

---

### 4.2 Node 2: Retrieve Context

**ไฟล์**: `workflow.py` บรรทัด 116-172

**หน้าที่**: ค้นหาเอกสารตัวอย่างและข้อมูลที่เกี่ยวข้อง

```
┌─────────────────────────────────────────────────────────────┐
│                    retrieve_context()                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Input: user_request, category                              │
│                                                              │
│                       │                                      │
│                       ▼                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │           Build Search Query                         │   │
│   │                                                      │   │
│   │   1. สกัด action keywords จากคำขอ:                   │   │
│   │      - "ขออนุมัติ" → เพิ่ม "ขออนุมัติ"                │   │
│   │      - "เดินทาง" → เพิ่ม "เดินทาง ปฏิบัติงาน"         │   │
│   │      - "รายงาน" → เพิ่ม "รายงานผล"                   │   │
│   │                                                      │   │
│   │   2. รวมเป็น query:                                  │   │
│   │      "บันทึกข้อความ {keywords} {user_request[:100]}" │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│           ┌───────────┴───────────┐                         │
│           │                       │                         │
│           ▼                       ▼                         │
│   ┌───────────────┐       ┌───────────────┐                 │
│   │ get_entities_ │       │    query()    │                 │
│   │ and_relations │       │ (RAG search)  │                 │
│   └───────┬───────┘       └───────┬───────┘                 │
│           │                       │                         │
│           ▼                       ▼                         │
│     entities: []           rag_context: str                 │
│     relations: []                 │                         │
│           │                       │                         │
│           │                       ▼                         │
│           │               ┌───────────────┐                 │
│           │               │ context เพียง │                 │
│           │               │ พอไหม?        │                 │
│           │               │ (> 200 chars) │                 │
│           │               └───────┬───────┘                 │
│           │                       │                         │
│           │                ┌──────┴──────┐                  │
│           │               Yes            No                 │
│           │                │             │                  │
│           │                │             ▼                  │
│           │                │    ┌────────────────┐          │
│           │                │    │ ใช้ template   │          │
│           │                │    │ example แทน   │          │
│           │                │    └────────┬───────┘          │
│           │                │             │                  │
│           │                └──────┬──────┘                  │
│           │                       │                         │
│           └───────────────────────┼─────────────────────────│
│                                   │                         │
│                                   ▼                         │
│   Output: rag_context, rag_examples, entities, relations    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.3 Node 3: Generate Draft

**ไฟล์**: `workflow.py` บรรทัด 175-340

**หน้าที่**: สร้างเอกสารโดยการกรอก template

```
┌─────────────────────────────────────────────────────────────┐
│                      generate_draft()                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Step 1: Extract User Data (Regex)                   │   │
│   │                                                      │   │
│   │  user_request = "ขออนุมัติเดินทางจังหวัดเชียงใหม่     │   │
│   │                  สทช 1234/2568 วันที่ 15-20 ม.ค."    │   │
│   │                                                      │   │
│   │  ผลลัพธ์:                                            │   │
│   │  - location: "เชียงใหม่"                             │   │
│   │  - doc_number: "สทช 1234"                           │   │
│   │  - year: "2568"                                      │   │
│   │  - date_range: "15-20 ม.ค."                         │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Step 2: Detect Document Subtype                     │   │
│   │                                                      │   │
│   │  มี "ขออนุมัติ"?  ──Yes──▶ REQUEST template          │   │
│   │       │                    (เรื่องเพื่อพิจารณา)       │   │
│   │       No                                             │   │
│   │       │                                              │   │
│   │       ▼                                              │   │
│   │  มี "รายงานผล"?  ──Yes──▶ REPORT template            │   │
│   │       │                    (ข้อเท็จจริง)              │   │
│   │       No                                             │   │
│   │       │                                              │   │
│   │       ▼                                              │   │
│   │  default ──────────────▶ REQUEST template            │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Step 3: Build LLM Prompt                            │   │
│   │                                                      │   │
│   │  <role>                                              │   │
│   │  คุณเป็นเจ้าหน้าที่ธุรการผู้เชี่ยวชาญ...              │   │
│   │  </role>                                             │   │
│   │                                                      │   │
│   │  <task>                                              │   │
│   │  กรอกแบบฟอร์มโดยแทนที่ [PLACEHOLDER] ทุกตัว          │   │
│   │  </task>                                             │   │
│   │                                                      │   │
│   │  <previous_errors> (ถ้า retry)                       │   │
│   │  เอกสารก่อนหน้ามีข้อผิดพลาด:                          │   │
│   │  - Missing section: เรื่องเดิม                       │   │
│   │  </previous_errors>                                  │   │
│   │                                                      │   │
│   │  <input>                                             │   │
│   │  คำขอ: {user_request}                               │   │
│   │  ประเภท: หนังสือภายใน                                │   │
│   │  - เลขที่: สทช 1234                                  │   │
│   │  - สถานที่: เชียงใหม่                                │   │
│   │  </input>                                            │   │
│   │                                                      │   │
│   │  <template>                                          │   │
│   │  บันทึกข้อความ                                       │   │
│   │  ส่วนราชการ [AGENCY]                                 │   │
│   │  ...                                                 │   │
│   │  </template>                                         │   │
│   │                                                      │   │
│   │  <placeholders>                                      │   │
│   │  - [AGENCY]: ชื่อส่วนราชการ (จำเป็น)                  │   │
│   │    ตัวอย่าง: สำนักงาน กสทช.                          │   │
│   │  ...                                                 │   │
│   │  </placeholders>                                     │   │
│   │                                                      │   │
│   │  <rules>                                             │   │
│   │  1. แทนที่ [PLACEHOLDER] ทุกตัว                      │   │
│   │  2. ห้ามมี [ หรือ ] เหลือ                            │   │
│   │  3. ใช้เลขไทย ๑. ๒. ๓.                              │   │
│   │  4. ใช้ปี พ.ศ.                                       │   │
│   │  </rules>                                            │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│              ┌────────────────┐                              │
│              │ deepseek_      │                              │
│              │ complete()     │                              │
│              └────────┬───────┘                              │
│                       │                                      │
│                       ▼                                      │
│   Output: draft (เอกสารที่ LLM สร้าง)                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.4 Node 4: Validate Document

**ไฟล์**: `workflow.py` บรรทัด 343-412

**หน้าที่**: ตรวจสอบเอกสารที่สร้างว่าถูกต้องหรือไม่

```
┌─────────────────────────────────────────────────────────────┐
│                   validate_document()                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Input: draft, category, user_request                       │
│                                                              │
│   errors = []                                                │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Check 1: Empty Draft                                │   │
│   │                                                      │   │
│   │  if not draft:                                       │   │
│   │      errors.append("Empty draft")                    │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Check 2: Unreplaced Placeholders                    │   │
│   │                                                      │   │
│   │  regex: \[([A-Z_]+)\]                               │   │
│   │                                                      │   │
│   │  พบ [SUBJECT] → error!                              │   │
│   │  พบ [DATE] → error!                                 │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Check 3: Required Sections                          │   │
│   │                                                      │   │
│   │  สำหรับ "หนังสือภายใน" ต้องมี:                        │   │
│   │  ✓ บันทึกข้อความ                                     │   │
│   │  ✓ ส่วนราชการ                                       │   │
│   │  ✓ ที่                                              │   │
│   │  ✓ วันที่                                           │   │
│   │  ✓ เรื่อง                                           │   │
│   │  ✓ เรียน                                            │   │
│   │  ✓ เรื่องเดิม                                       │   │
│   │                                                      │   │
│   │  ถ้าไม่พบ → errors.append("Missing: {section}")      │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Check 4: Content Pattern                            │   │
│   │                                                      │   │
│   │  สำหรับ "หนังสือภายใน" ต้องมี:                        │   │
│   │  - "เรื่องเพื่อพิจารณา" (สำหรับขออนุมัติ)              │   │
│   │       หรือ                                           │   │
│   │  - "ข้อเท็จจริง" (สำหรับรายงาน)                       │   │
│   │                                                      │   │
│   │  ถ้าไม่มีทั้งคู่ → error!                             │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Check 5: User Data Incorporated                     │   │
│   │                                                      │   │
│   │  ผู้ใช้ระบุ doc_number = "สทช 1234"                  │   │
│   │  → ต้องมี "สทช1234" ในเอกสาร (ไม่รวม space)          │   │
│   │                                                      │   │
│   │  ผู้ใช้ระบุ location = "เชียงใหม่"                    │   │
│   │  → ต้องมี "เชียงใหม่" ในเอกสาร                       │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  Check 6: Minimum Length                             │   │
│   │                                                      │   │
│   │  if len(draft) < 200:                               │   │
│   │      errors.append("Too short")                      │   │
│   └─────────────────────────────────────────────────────┘   │
│                       │                                      │
│                       ▼                                      │
│              ┌────────────────┐                              │
│              │ errors empty?  │                              │
│              └───────┬────────┘                              │
│                      │                                       │
│               ┌──────┴──────┐                                │
│              Yes            No                               │
│               │             │                                │
│               ▼             ▼                                │
│          is_valid=True  is_valid=False                       │
│          final_doc=draft  retry_count++                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 4.5 Conditional Edge: Should Retry

**ไฟล์**: `workflow.py` บรรทัด 415-430

```python
def should_retry(state: DocumentState) -> Literal["generate", "end"]:
    # ถ้าผ่าน validation แล้ว → จบ
    if state.get('is_valid', False):
        return "end"

    # ถ้ายัง retry ได้ (< 3 ครั้ง) → กลับไป generate
    if state.get('retry_count', 0) < MAX_VALIDATION_RETRIES:
        return "generate"

    # retry หมดแล้ว → จบ
    return "end"
```

**Retry Flow**:
```
ครั้งที่ 1: generate → validate → ไม่ผ่าน (errors: ["Missing: เรื่องเดิม"])
ครั้งที่ 2: generate (+ error feedback) → validate → ไม่ผ่าน
ครั้งที่ 3: generate (+ error feedback) → validate → ผ่าน ✓

หรือ

ครั้งที่ 3: generate → validate → ยังไม่ผ่าน → หยุด (max retry)
```

---

## 5. เทคนิคและ Design Patterns

### 5.1 State Machine Pattern (LangGraph)

```python
workflow = StateGraph(DocumentState)

# เพิ่ม nodes
workflow.add_node("classify", classify_category)
workflow.add_node("retrieve", retrieve_context)
workflow.add_node("generate", generate_draft)
workflow.add_node("validate", validate_document)

# กำหนด edges
workflow.set_entry_point("classify")
workflow.add_edge("classify", "retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "validate")

# Conditional edge
workflow.add_conditional_edges("validate", should_retry, {
    "generate": "generate",
    "end": END,
})

app = workflow.compile()
```

**ข้อดี**:
- แยก logic ออกเป็น node ชัดเจน
- Control flow ผ่าน edges
- รองรับ conditional branching และ loops
- State ถูก track ตลอดการทำงาน

---

### 5.2 Singleton Pattern

```python
_rag_instance = None

async def get_rag() -> LightRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = LightRAG(...)
        await _rag_instance.initialize_storages()
    return _rag_instance
```

**ข้อดี**:
- สร้าง instance เดียว ใช้ทั้งโปรแกรม
- ประหยัด memory
- ไม่ต้อง initialize ซ้ำ

---

### 5.3 Lazy Loading Pattern

```python
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print(f"Loading model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model
```

**ข้อดี**:
- โหลด model เมื่อต้องใช้เท่านั้น
- ลด startup time
- ประหยัด memory ถ้าไม่ได้ใช้

---

### 5.4 Retry with Exponential Backoff

```python
for attempt in range(retries + 1):
    try:
        result = await asyncio.wait_for(api_call(), timeout=60)
        return result
    except Exception:
        if attempt < retries:
            delay = base_delay * (2 ** attempt)  # 1, 2, 4, 8, ...
            await asyncio.sleep(delay)
```

**ข้อดี**:
- ไม่ flood API เมื่อเกิด error
- รอนานขึ้นเรื่อยๆ ให้ระบบฟื้นตัว
- มี limit จำนวน retry

---

### 5.5 Pydantic Validation

```python
class CategoryInfo(BaseModel):
    name: str = Field(..., min_length=1)
    keywords: list[str] = Field(default_factory=list)

    @field_validator('keywords')
    @classmethod
    def validate_non_empty_strings(cls, v):
        return [s.strip() for s in v if s and s.strip()]
```

**ข้อดี**:
- Type checking at runtime
- Automatic validation
- Clear error messages
- Self-documenting

---

### 5.6 TypedDict for State

```python
class DocumentState(TypedDict):
    user_request: str
    category: Optional[CategoryType]
    draft: str
    is_valid: bool
```

**ข้อดี**:
- Type hints สำหรับ dictionary
- IDE support (autocomplete)
- ไม่มี overhead ตอน runtime

---

## 6. Data Flow

### 6.1 Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER INPUT                                 │
│  "ขออนุมัติเดินทางไปราชการจังหวัดเชียงใหม่ สทช 1234/2568"             │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CLASSIFY NODE                                 │
│─────────────────────────────────────────────────────────────────────│
│  Input:  user_request                                                │
│                                                                      │
│  Process:                                                            │
│  1. ส่ง prompt ไป LLM                                                │
│  2. LLM วิเคราะห์คำขอ                                                │
│  3. Return: "หนังสือภายใน"                                           │
│                                                                      │
│  Output: category="หนังสือภายใน", confidence=0.8                     │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        RETRIEVE NODE                                 │
│─────────────────────────────────────────────────────────────────────│
│  Input:  user_request, category                                      │
│                                                                      │
│  Process:                                                            │
│  1. สร้าง search query:                                              │
│     "บันทึกข้อความ ขออนุมัติ เดินทาง ขออนุมัติเดินทางไปราชการ..."    │
│                                                                      │
│  2. Query Knowledge Graph:                                           │
│     ┌─────────────────────────────────────────────┐                 │
│     │  LightRAG                                   │                 │
│     │  ├─ Entities: [กสทช, เชียงใหม่, สทช]        │                 │
│     │  ├─ Relations: [ตั้งอยู่ที่, สังกัด]         │                 │
│     │  └─ Context: "ตัวอย่างบันทึกขออนุมัติ..."   │                 │
│     └─────────────────────────────────────────────┘                 │
│                                                                      │
│  3. Fallback ถ้า context น้อย:                                       │
│     → ใช้ template example แทน                                       │
│                                                                      │
│  Output: rag_context, rag_examples, entities, relations              │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        GENERATE NODE                                 │
│─────────────────────────────────────────────────────────────────────│
│  Input:  user_request, category, rag_examples, validation_errors     │
│                                                                      │
│  Process:                                                            │
│                                                                      │
│  1. Extract User Data (Regex):                                       │
│     ┌─────────────────────────────────────────────┐                 │
│     │  location: "เชียงใหม่"                      │                 │
│     │  doc_number: "สทช 1234"                    │                 │
│     │  year: "2568"                              │                 │
│     └─────────────────────────────────────────────┘                 │
│                                                                      │
│  2. Select Template:                                                 │
│     "ขออนุมัติ" → DRAFT_INTERNAL_REQUEST                            │
│                                                                      │
│  3. Build Prompt with:                                               │
│     - Role: เจ้าหน้าที่ธุรการ                                        │
│     - Task: กรอก placeholder                                        │
│     - Template: บันทึกข้อความ...                                     │
│     - User data: location, doc_number                               │
│     - Examples: rag_examples                                        │
│     - Previous errors (if retry)                                    │
│                                                                      │
│  4. Send to LLM → Generate document                                  │
│                                                                      │
│  Output: draft                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  บันทึกข้อความ                                                 │  │
│  │                                                                │  │
│  │  ส่วนราชการ  สำนักงาน กสทช. เขต ๑๔ (เชียงใหม่)                  │  │
│  │  ที่         สทช ๑๒๓๔/๒๕๖๘           วันที่ ๑๕ มกราคม ๒๕๖๘    │  │
│  │  เรื่อง      ขออนุมัติเดินทางไปราชการ                           │  │
│  │                                                                │  │
│  │  เรียน  ผู้อำนวยการสำนักงาน กสทช. เขต ๑๔                       │  │
│  │                                                                │  │
│  │          เรื่องเดิม                                            │  │
│  │                  ตามที่สำนักงาน กสทช. ...                       │  │
│  │                                                                │  │
│  │          เรื่องเพื่อพิจารณา                                     │  │
│  │                  ๑. ขออนุมัติเดินทางไปราชการ...                 │  │
│  │                                                                │  │
│  │          จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติ                       │  │
│  │                                                                │  │
│  │                                      (ลงชื่อ)                   │  │
│  │                                    พนักงานเจ้าหน้าที่            │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        VALIDATE NODE                                 │
│─────────────────────────────────────────────────────────────────────│
│  Input:  draft, category, user_request                               │
│                                                                      │
│  Validation Checks:                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  Check                          │  Result                       ││
│  │─────────────────────────────────┼───────────────────────────────││
│  │  1. Empty draft                 │  ✓ Pass (มีเนื้อหา)           ││
│  │  2. Unreplaced [PLACEHOLDER]    │  ✓ Pass (ไม่มี [...])         ││
│  │  3. Required sections           │  ✓ Pass (มีครบ 7 sections)    ││
│  │  4. Content pattern             │  ✓ Pass (มี "เรื่องเพื่อพิจารณา")││
│  │  5. User data incorporated      │  ✓ Pass (มี "เชียงใหม่")       ││
│  │  6. Minimum length              │  ✓ Pass (> 200 chars)         ││
│  └─────────────────────────────────┴───────────────────────────────┘│
│                                                                      │
│  Output: is_valid=True, final_document=draft                         │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
                        ┌─────────────────┐
                        │  should_retry   │
                        │  is_valid=True  │
                        │  → return "end" │
                        └────────┬────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          FINAL OUTPUT                                │
│─────────────────────────────────────────────────────────────────────│
│                                                                      │
│  บันทึกข้อความ                                                       │
│                                                                      │
│  ส่วนราชการ  สำนักงาน กสทช. เขต ๑๔ (เชียงใหม่)                        │
│  ที่         สทช ๑๒๓๔/๒๕๖๘                    วันที่ ๑๕ มกราคม ๒๕๖๘ │
│  เรื่อง      ขออนุมัติเดินทางไปราชการจังหวัดเชียงใหม่                  │
│                                                                      │
│  เรียน  ผู้อำนวยการสำนักงาน กสทช. เขต ๑๔                             │
│                                                                      │
│          เรื่องเดิม                                                  │
│                  ตามที่สำนักงาน กสทช. เขต ๑๔ มีภารกิจในการตรวจสอบ    │
│          คลื่นความถี่ในพื้นที่จังหวัดเชียงใหม่...                      │
│                                                                      │
│          เรื่องเพื่อพิจารณา                                           │
│                  ๑. ขออนุมัติเดินทางไปราชการจังหวัดเชียงใหม่           │
│                  ๒. กำหนดวันเดินทาง วันที่ ๑๕-๒๐ มกราคม ๒๕๖๘         │
│                  ๓. ขออนุมัติค่าใช้จ่ายในการเดินทาง                   │
│                                                                      │
│          จึงเรียนมาเพื่อโปรดพิจารณาอนุมัติ                             │
│                                                                      │
│                                            (ลงชื่อ)                   │
│                                          นายสมชาย ใจดี               │
│                                        พนักงานตรวจสอบคลื่นความถี่      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. สรุป Flow Diagram

### 7.1 Simple Flow (Happy Path)

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│   INPUT   │────▶│  CLASSIFY │────▶│  RETRIEVE │────▶│  GENERATE │────▶│  VALIDATE │
│           │     │           │     │           │     │           │     │   ✓ Pass  │
└───────────┘     └───────────┘     └───────────┘     └───────────┘     └─────┬─────┘
                                                                              │
                                                                              ▼
                                                                        ┌───────────┐
                                                                        │  OUTPUT   │
                                                                        │  Document │
                                                                        └───────────┘
```

### 7.2 Flow with Retry

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│   INPUT   │────▶│  CLASSIFY │────▶│  RETRIEVE │────▶│  GENERATE │────▶│  VALIDATE │
│           │     │           │     │           │     │    (1)    │     │   ✗ Fail  │
└───────────┘     └───────────┘     └───────────┘     └───────────┘     └─────┬─────┘
                                                            ▲                 │
                                                            │     ┌───────────┴───────────┐
                                                            │     │ retry_count < 3?      │
                                                            │     │ errors: [Missing...]  │
                                                            │     └───────────┬───────────┘
                                                            │                 │ Yes
                                                            │                 ▼
                                                      ┌───────────┐     ┌───────────┐
                                                      │  GENERATE │◀────│  Add error│
                                                      │    (2)    │     │  feedback │
                                                      └─────┬─────┘     └───────────┘
                                                            │
                                                            ▼
                                                      ┌───────────┐
                                                      │  VALIDATE │
                                                      │   ✓ Pass  │
                                                      └─────┬─────┘
                                                            │
                                                            ▼
                                                      ┌───────────┐
                                                      │  OUTPUT   │
                                                      └───────────┘
```

### 7.3 Complete System Flow

```
                              ┌─────────────────────────────────────┐
                              │           User Request              │
                              │   "ขออนุมัติเดินทางจังหวัดเชียงใหม่"  │
                              └─────────────────┬───────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │                           ▼                           │
                    │                  ┌─────────────────┐                  │
                    │                  │    CLASSIFY     │                  │
                    │                  │                 │                  │
                    │                  │  ┌───────────┐  │                  │
                    │                  │  │  DeepSeek │  │                  │
                    │                  │  │    LLM    │  │                  │
                    │                  │  └───────────┘  │                  │
                    │                  │        │        │                  │
                    │                  │        ▼        │                  │
                    │                  │  "หนังสือภายใน" │                  │
                    │                  └────────┬────────┘                  │
                    │                           │                           │
                    │                           ▼                           │
                    │                  ┌─────────────────┐                  │
                    │                  │    RETRIEVE     │                  │
                    │                  │                 │                  │
                    │                  │  ┌───────────┐  │                  │
                    │                  │  │ LightRAG  │  │                  │
                    │                  │  │    KG     │  │                  │
                    │                  │  └───────────┘  │                  │
                    │                  │        │        │                  │
                    │                  │        ▼        │                  │
                    │                  │  entities,      │                  │
                    │                  │  relations,     │                  │
                    │                  │  examples       │                  │
                    │                  └────────┬────────┘                  │
                    │                           │                           │
                    │  ┌────────────────────────┼────────────────────────┐  │
                    │  │                        ▼                        │  │
                    │  │               ┌─────────────────┐               │  │
                    │  │               │    GENERATE     │               │  │
                    │  │               │                 │               │  │
                    │  │               │  ┌───────────┐  │               │  │
                    │  │               │  │  DeepSeek │  │               │  │
                    │  │               │  │    LLM    │  │               │  │
                    │  │               │  └───────────┘  │               │  │
                    │  │               │        │        │               │  │
                    │  │               │        ▼        │               │  │
                    │  │               │  draft document │               │  │
                    │  │               └────────┬────────┘               │  │
                    │  │                        │                        │  │
                    │  │                        ▼                        │  │
                    │  │               ┌─────────────────┐               │  │
                    │  │               │    VALIDATE     │               │  │
                    │  │               │                 │               │  │
                    │  │               │  6 checks:      │               │  │
                    │  │               │  □ Empty        │               │  │
                    │  │               │  □ Placeholders │               │  │
                    │  │               │  □ Sections     │               │  │
                    │  │               │  □ Pattern      │               │  │
                    │  │               │  □ User data    │               │  │
                    │  │               │  □ Length       │               │  │
                    │  │               └────────┬────────┘               │  │
                    │  │                        │                        │  │
                    │  │               ┌────────┴────────┐               │  │
                    │  │               │                 │               │  │
                    │  │            ✓ Pass           ✗ Fail              │  │
                    │  │               │                 │               │  │
                    │  │               │       ┌─────────┴─────────┐     │  │
                    │  │               │       │  retry < 3?       │     │  │
                    │  │               │       └────────┬──────────┘     │  │
                    │  │               │                │                │  │
                    │  │               │         ┌──────┴──────┐         │  │
                    │  │               │        Yes            No        │  │
                    │  │               │         │             │         │  │
                    │  │               │         │             ▼         │  │
                    │  │               │         │        ┌────────┐     │  │
                    │  │               │         │        │  END   │     │  │
                    │  │               │         │        │ (fail) │     │  │
                    │  │               │         │        └────────┘     │  │
                    │  │               │         │                       │  │
                    │  │               │    ┌────┴─────┐                 │  │
                    │  │               │    │  RETRY   │                 │  │
                    │  │               │    │ + errors │                 │  │
                    │  │               │    └────┬─────┘                 │  │
                    │  │               │         │                       │  │
                    │  └───────────────│─────────┘───────────────────────┘  │
                    │                  │  (loop back to GENERATE)           │
                    │                  │                                    │
                    │                  ▼                                    │
                    │         ┌─────────────────┐                           │
                    │         │      END        │                           │
                    │         │   (success)     │                           │
                    │         └────────┬────────┘                           │
                    │                  │                                    │
                    └──────────────────┼────────────────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────────────────────────┐
                              │           Final Document            │
                              │                                     │
                              │   บันทึกข้อความ                      │
                              │   ส่วนราชการ สำนักงาน กสทช. ...       │
                              │   ...                               │
                              └─────────────────────────────────────┘
```

---

## สรุป

ระบบนี้ใช้หลักการ **Agentic AI** โดยมี:

1. **State Machine** (LangGraph) - ควบคุม flow การทำงาน
2. **Knowledge Graph RAG** (LightRAG) - ค้นหาข้อมูลอัจฉริยะ
3. **LLM** (DeepSeek) - สร้างเนื้อหาเอกสาร
4. **Validation Loop** - ตรวจสอบและ retry อัตโนมัติ
5. **Template System** - โครงสร้างเอกสารมาตรฐาน

การออกแบบนี้ทำให้ระบบ:
- **Reliable** - มี retry และ fallback
- **Maintainable** - แยก module ชัดเจน
- **Extensible** - เพิ่มประเภทเอกสารได้ง่าย
- **Observable** - มี logging และ state tracking
