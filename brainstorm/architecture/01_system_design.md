# Agentic Thai Document Generation System - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Web UI    │  │   CLI       │  │   API       │  │   Chat      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                        ORCHESTRATOR AGENT                                │
│                         (Claude / LangGraph)                             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  - Parse user intent                                              │  │
│  │  - Select document type                                           │  │
│  │  - Manage workflow state                                          │  │
│  │  - Coordinate sub-agents                                          │  │
│  │  - Handle errors and retries                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────────────┐
        │                        │                                │
        ▼                        ▼                                ▼
┌───────────────┐      ┌───────────────┐              ┌───────────────┐
│   TEMPLATE    │      │   CONTENT     │              │  VALIDATION   │
│   AGENT       │      │   AGENT       │              │  AGENT        │
│               │      │               │              │               │
│ - Load        │      │ - Generate    │              │ - Format      │
│   templates   │      │   Thai text   │              │   check       │
│ - Select      │      │ - Typhoon 2   │              │ - Grammar     │
│   document    │      │ - Style       │              │ - Completeness│
│   type        │      │   adherence   │              │ - Compliance  │
└───────┬───────┘      └───────┬───────┘              └───────┬───────┘
        │                      │                              │
        └──────────────────────┼──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                        DOCUMENT FORMATTER                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  - Apply TH Sarabun PSK font                                      │  │
│  │  - Place ตราครุฑ correctly                                         │  │
│  │  - Set margins and spacing                                        │  │
│  │  - Generate DOCX/PDF output                                       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                         OUTPUT                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   DOCX      │  │   PDF       │  │   Preview   │  │   Print     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Definitions

### 1. Orchestrator Agent

**Role**: Central coordinator managing the entire workflow

**Framework**: LangGraph or Claude Agent SDK

**Responsibilities**:
- Parse user input and determine intent
- Select appropriate document type
- Manage state across workflow steps
- Handle errors, retries, and edge cases
- Provide user feedback

**State Schema**:
```python
from typing import TypedDict, List, Optional
from enum import Enum

class DocumentType(Enum):
    EXTERNAL = "หนังสือภายนอก"
    INTERNAL = "หนังสือภายใน"
    STAMPED = "หนังสือประทับตรา"
    ORDER = "หนังสือสั่งการ"
    ANNOUNCEMENT = "หนังสือประชาสัมพันธ์"
    RECORD = "หนังสือรับรอง"

class WorkflowState(TypedDict):
    # Input
    user_request: str
    document_type: Optional[DocumentType]

    # Extracted info
    sender: Optional[str]
    recipient: Optional[str]
    subject: Optional[str]
    purpose: Optional[str]
    details: Optional[str]

    # Generated content
    template: Optional[str]
    draft_content: Optional[str]

    # Validation
    format_valid: bool
    grammar_valid: bool
    compliance_valid: bool
    validation_errors: List[str]

    # Output
    final_document: Optional[bytes]
    output_format: str  # "docx" or "pdf"

    # Workflow
    current_step: str
    retry_count: int
    error_message: Optional[str]
```

---

### 2. Template Agent

**Role**: Select and prepare document templates

**Responsibilities**:
- Classify document type from user intent
- Load appropriate template structure
- Prepare template with ตราครุฑ placement

**Template Selection Logic**:
```python
def select_template(user_request: str) -> DocumentType:
    """
    Keywords mapping:
    - "ติดต่อหน่วยงานอื่น", "ส่งถึงกระทรวง" -> EXTERNAL
    - "บันทึกข้อความ", "ภายในหน่วยงาน" -> INTERNAL
    - "ประกาศ", "แจ้งให้ทราบ" -> ANNOUNCEMENT
    - "คำสั่ง", "ให้ดำเนินการ" -> ORDER
    - "รับรอง", "ยืนยัน" -> RECORD
    """
    pass
```

---

### 3. Content Generation Agent

**Role**: Generate Thai formal content

**Primary Model**: Typhoon 2 (70B for quality, 8B for speed)

**Fallback**: Claude with Thai-specific prompting

**Key Tasks**:
- Generate formal Thai prose
- Maintain consistent formal register
- Apply appropriate คำขึ้นต้น and คำลงท้าย
- Structure content logically

**Prompt Engineering**:
```python
CONTENT_SYSTEM_PROMPT = """
คุณเป็นผู้เชี่ยวชาญในการเขียนหนังสือราชการไทย
ตามระเบียบสำนักนายกรัฐมนตรีว่าด้วยงานสารบรรณ พ.ศ. 2526

หลักการเขียน:
1. ใช้ภาษาราชการที่เป็นทางการ
2. ใช้คำราชาศัพท์เมื่อเหมาะสม
3. เนื้อความกระชับ ชัดเจน ตรงประเด็น
4. ใช้ลำดับความคิดที่เป็นเหตุเป็นผล
5. หลีกเลี่ยงภาษาพูด คำแสลง หรือคำต่างประเทศที่ไม่จำเป็น

รูปแบบคำขึ้นต้น-คำลงท้าย ตามตำแหน่งผู้รับ:
- นายกรัฐมนตรี: กราบเรียน / ด้วยความเคารพอย่างสูง
- รัฐมนตรี: เรียน / ขอแสดงความนับถืออย่างยิ่ง
- ผู้อำนวยการ/หัวหน้าส่วนราชการ: เรียน / ขอแสดงความนับถือ
- บุคคลทั่วไป: เรียน / ขอแสดงความนับถือ
"""
```

---

### 4. Validation Agent

**Role**: Quality assurance and compliance checking

**Checks**:

| Check Type | Details |
|------------|---------|
| Format | Font, margins, spacing, alignment |
| Structure | Required sections present |
| Grammar | Thai grammar and spelling |
| Compliance | ระเบียบสำนักนายกรัฐมนตรี adherence |
| Completeness | All required fields filled |

**Implementation**:
```python
class ValidationResult(TypedDict):
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]

def validate_document(content: str, doc_type: DocumentType) -> ValidationResult:
    errors = []
    warnings = []

    # Check required sections
    required = get_required_sections(doc_type)
    for section in required:
        if section not in content:
            errors.append(f"Missing required section: {section}")

    # Check formal language
    informal_words = detect_informal_language(content)
    if informal_words:
        warnings.append(f"Informal words detected: {informal_words}")

    # Check salutation matches recipient
    # Check closing matches recipient
    # etc.

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        suggestions=[]
    )
```

---

### 5. Document Formatter

**Role**: Generate final DOCX/PDF with correct formatting

**Technology**: python-docx + reportlab (or weasyprint)

**Key Formatting**:
```python
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

def format_document(content: dict, doc_type: str) -> bytes:
    doc = Document()

    # Page setup
    section = doc.sections[0]
    section.page_width = Cm(21)    # A4
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(2)

    # Add ตราครุฑ
    add_garuda_emblem(doc)

    # Set font
    style = doc.styles['Normal']
    style.font.name = 'TH Sarabun PSK'
    style.font.size = Pt(16)

    # Add content sections
    # ...

    return doc_to_bytes(doc)
```

---

## Workflow Diagram (LangGraph)

```python
from langgraph.graph import StateGraph, END

# Define nodes
workflow = StateGraph(WorkflowState)

workflow.add_node("parse_input", parse_user_input)
workflow.add_node("select_template", select_document_template)
workflow.add_node("generate_content", generate_thai_content)
workflow.add_node("validate", validate_document)
workflow.add_node("format", format_final_document)
workflow.add_node("handle_error", handle_validation_error)

# Define edges
workflow.set_entry_point("parse_input")

workflow.add_edge("parse_input", "select_template")
workflow.add_edge("select_template", "generate_content")
workflow.add_edge("generate_content", "validate")

# Conditional edge after validation
workflow.add_conditional_edges(
    "validate",
    lambda state: "format" if state["format_valid"] else "handle_error",
    {
        "format": "format",
        "handle_error": "handle_error"
    }
)

workflow.add_edge("format", END)
workflow.add_conditional_edges(
    "handle_error",
    lambda state: "generate_content" if state["retry_count"] < 3 else END,
    {
        "generate_content": "generate_content",
        END: END
    }
)

app = workflow.compile()
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Orchestration | LangGraph / Claude Agent SDK | Workflow management |
| Thai LLM | Typhoon 2 API | Content generation |
| Fallback LLM | Claude API | Complex reasoning |
| Document Gen | python-docx | DOCX output |
| PDF Gen | reportlab / weasyprint | PDF output |
| API | FastAPI | REST endpoints |
| Frontend | Streamlit / React | Web UI |
| Storage | SQLite / PostgreSQL | Templates, history |

---

## MCP Integration

Since you have MCP servers available, we can integrate:

```python
# MCP Tools for the agent
mcp_tools = [
    "mcp__exa__web_search_exa",       # Research official formats
    "mcp__exa__get_code_context_exa",  # Code examples
    "mcp__context7__query-docs",       # Library documentation
]

# Custom MCP server for Thai documents
class ThaiDocumentMCP:
    """
    Custom MCP server providing:
    - get_template(doc_type) -> template structure
    - validate_thai_format(content) -> validation result
    - get_formal_phrases(context) -> appropriate phrases
    """
    pass
```

---

## Next Steps

1. [ ] Set up project structure
2. [ ] Implement Template Agent
3. [ ] Integrate Typhoon 2 API
4. [ ] Build Content Generation Agent
5. [ ] Create Validation Agent
6. [ ] Implement Document Formatter
7. [ ] Wire up LangGraph workflow
8. [ ] Build simple UI
9. [ ] Test with real document examples
