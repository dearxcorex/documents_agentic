# Agentic AI Frameworks Comparison

## Overview

| Framework | Best For | Complexity | Thai Support |
|-----------|----------|------------|--------------|
| **LangGraph** | Complex workflows | Medium | Via LLM |
| **Claude Agent SDK** | Tool-heavy agents | Low-Medium | Native |
| **LlamaIndex ADW** | Document-centric | Medium | Via LLM |
| **CrewAI** | Multi-agent teams | Medium | Via LLM |
| **AutoGen** | Research/code | High | Via LLM |

---

## Option 1: LangGraph (Recommended)

### Why Choose
- Graph-based workflow design
- State management built-in
- Easy conditional branching
- Good for document pipelines

### Architecture Pattern
```
┌─────────────────────────────────────────────┐
│              LangGraph Workflow              │
│                                             │
│  ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐ │
│  │Parse├───►│Type ├───►│Gen  ├───►│Valid│ │
│  │Input│    │Select    │Content   │ate  │ │
│  └─────┘    └─────┘    └──┬──┘    └──┬──┘ │
│                           │          │     │
│                           │    ┌─────▼───┐ │
│                           │    │Retry?   │ │
│                           │    └────┬────┘ │
│                           │         │      │
│                           └─────────┘      │
│                                     │      │
│                              ┌──────▼────┐ │
│                              │  Format   │ │
│                              │  Output   │ │
│                              └───────────┘ │
└─────────────────────────────────────────────┘
```

### Installation
```bash
pip install langgraph langchain-core langchain-anthropic
```

### Example Code
```python
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from typing import TypedDict, Annotated
import operator

class DocumentState(TypedDict):
    messages: Annotated[list, operator.add]
    document_type: str
    content: str
    is_valid: bool

def parse_input(state: DocumentState) -> DocumentState:
    """Extract document requirements from user input"""
    llm = ChatAnthropic(model="claude-sonnet-4-20250514")
    # Parse logic
    return state

def generate_content(state: DocumentState) -> DocumentState:
    """Generate Thai formal content using Typhoon"""
    # Call Typhoon API
    return state

def validate(state: DocumentState) -> DocumentState:
    """Validate against Thai document standards"""
    # Validation logic
    return state

# Build graph
graph = StateGraph(DocumentState)
graph.add_node("parse", parse_input)
graph.add_node("generate", generate_content)
graph.add_node("validate", validate)

graph.set_entry_point("parse")
graph.add_edge("parse", "generate")
graph.add_edge("generate", "validate")
graph.add_conditional_edges(
    "validate",
    lambda s: END if s["is_valid"] else "generate"
)

app = graph.compile()
```

---

## Option 2: Claude Agent SDK

### Why Choose
- Native Claude integration
- Built-in tool system
- MCP server support
- Production-ready

### Architecture Pattern
```python
from claude_code_sdk import ClaudeSDKClient, Tool

# Define custom tools
@Tool
def get_document_template(doc_type: str) -> str:
    """Get Thai official document template"""
    templates = {
        "external": "...",
        "internal": "...",
    }
    return templates.get(doc_type, "")

@Tool
def validate_thai_format(content: str) -> dict:
    """Validate Thai document formatting"""
    # Validation logic
    return {"valid": True, "errors": []}

@Tool
def generate_docx(content: dict) -> bytes:
    """Generate DOCX file from content"""
    # python-docx logic
    return b"..."

# Create client
client = ClaudeSDKClient(
    tools=[
        get_document_template,
        validate_thai_format,
        generate_docx
    ]
)

# Run agent
result = await client.query(
    """
    สร้างหนังสือภายนอก เรื่อง ขอความอนุเคราะห์
    จาก: กรมการปกครอง
    ถึง: สำนักงานตำรวจแห่งชาติ
    เนื้อหา: ขอความร่วมมือในการรักษาความปลอดภัย
    """
)
```

### Benefits
- Less code needed
- Claude handles orchestration
- Built-in retry logic
- Easy MCP integration

---

## Option 3: LlamaIndex ADW

### Why Choose
- Document-focused by design
- RAG integration
- Good for template retrieval

### Architecture
```python
from llama_index.core import VectorStoreIndex
from llama_index.core.agent import ReActAgent

# Load document templates into index
templates_index = VectorStoreIndex.from_documents(template_docs)

# Create retrieval tool
template_tool = templates_index.as_query_engine()

# Build agent
agent = ReActAgent.from_tools(
    tools=[template_tool, content_generator, validator],
    llm=llm,
    verbose=True
)

response = agent.chat("สร้างหนังสือภายใน...")
```

---

## Option 4: Hybrid Approach (Recommended)

### Combine Best of Both

```
┌─────────────────────────────────────────────────────┐
│                Claude Agent SDK                      │
│            (Orchestration + Tools)                   │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │              Custom MCP Server                 │ │
│  │                                               │ │
│  │  ┌─────────────┐  ┌─────────────┐            │ │
│  │  │ Template    │  │ Formatter   │            │ │
│  │  │ Manager     │  │ (DOCX/PDF)  │            │ │
│  │  └─────────────┘  └─────────────┘            │ │
│  │                                               │ │
│  │  ┌─────────────┐  ┌─────────────┐            │ │
│  │  │ Typhoon API │  │ Validator   │            │ │
│  │  │ (Thai LLM)  │  │             │            │ │
│  │  └─────────────┘  └─────────────┘            │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Implementation
```python
# MCP Server with all Thai document tools
class ThaiDocumentMCP:
    @mcp_tool
    def select_template(self, doc_type: str) -> str:
        """Select appropriate Thai document template"""
        pass

    @mcp_tool
    def generate_thai_content(self, prompt: str) -> str:
        """Generate content using Typhoon 2"""
        # Call Typhoon API
        pass

    @mcp_tool
    def validate_document(self, content: str) -> dict:
        """Validate against Thai standards"""
        pass

    @mcp_tool
    def create_docx(self, content: dict) -> str:
        """Create DOCX file, return path"""
        pass

# Use with Claude Agent SDK
client = ClaudeSDKClient(
    mcp_servers=["thai-document-server"]
)
```

---

## Recommendation Summary

| Scenario | Best Choice |
|----------|-------------|
| Quick prototype | Claude Agent SDK |
| Complex workflow | LangGraph |
| Document retrieval | LlamaIndex ADW |
| Production system | Hybrid (Claude + MCP) |
| Self-hosted | LangGraph + OpenThaiGPT |

### For Your Use Case

**Recommended**: Hybrid with Claude Agent SDK + Custom MCP

Why:
1. You already have MCP available
2. Claude excels at orchestration
3. Custom tools for Thai-specific logic
4. Can integrate Typhoon via tool
5. Production-ready architecture
