# Agentic Thai Document Generation - Brainstorm

## Project Goal
Build an agentic AI system to generate Thai official government documents (หนังสือราชการ) following the Prime Minister's Office Regulations on Correspondence B.E. 2526.

---

## Folder Structure

```
brainstorm/
├── README.md                          # This file
├── research/
│   ├── 01_thai_official_documents.md  # Thai document standards
│   └── 02_thai_llm_options.md         # LLM comparison for Thai
├── architecture/
│   ├── 01_system_design.md            # System architecture
│   └── 02_agentic_frameworks.md       # Framework comparison
├── templates/
│   ├── 01_external_letter.md          # หนังสือภายนอก template
│   └── 02_internal_memo.md            # บันทึกข้อความ template
├── prompts/
│   └── 01_system_prompts.md           # All agent prompts
└── references/
    └── (external resources)
```

---

## Quick Summary

### Document Types (6 types)
1. หนังสือภายนอก - External letters (inter-agency)
2. หนังสือภายใน - Internal memos
3. หนังสือประทับตรา - Stamped letters
4. หนังสือสั่งการ - Orders/Commands
5. หนังสือประชาสัมพันธ์ - Announcements
6. หนังสือรับรอง - Certificates/Records

### Recommended Stack
| Component | Technology |
|-----------|------------|
| Orchestration | Claude Agent SDK + LangGraph |
| Thai LLM | Typhoon 2 (primary) |
| Fallback | OpenThaiGPT / Claude |
| Document Gen | python-docx / reportlab |
| API | FastAPI |
| UI | Streamlit |

### Key Standards
- Font: TH Sarabun PSK, 16pt
- Garuda emblem: 3cm height, centered
- Margins: Top 2.5cm, Bottom 2cm, Left 3cm, Right 2cm

---

## Next Steps

### Phase 1: Foundation
- [ ] Set up Python project with uv
- [ ] Create document templates (DOCX)
- [ ] Implement Typhoon 2 API integration

### Phase 2: Agents
- [ ] Build Template Selector Agent
- [ ] Build Content Generator Agent
- [ ] Build Validation Agent
- [ ] Build Document Formatter

### Phase 3: Orchestration
- [ ] Wire up LangGraph workflow
- [ ] Add error handling and retries
- [ ] Implement MCP server (optional)

### Phase 4: Interface
- [ ] Create Streamlit UI
- [ ] Add FastAPI endpoints
- [ ] Deploy

---

## Key Resources

### Thai Documents
- [ระเบียบสำนักนายกรัฐมนตรี พ.ศ. 2526](https://lawreform.go.th/uploads/files/1678240071-b99vw-cbccp.pdf)
- [หนังสือราชการคือ](https://หนังสือราชการ.com/blog/หนังสือราชการคือ)

### Thai LLMs
- [Typhoon](https://opentyphoon.ai/)
- [OpenThaiGPT](https://github.com/OpenThaiGPT)

### Agentic Frameworks
- [LangGraph](https://www.langchain.com/langgraph)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- [LlamaIndex ADW](https://www.llamaindex.ai/blog/introducing-agentic-document-workflows)

---

## Ideas to Explore

1. **Template retrieval via RAG** - Store many example documents
2. **Grammar checking** - Use Thai-specific grammar tools
3. **Style transfer** - Learn from existing documents
4. **Multi-language** - Generate Thai + English versions
5. **Voice input** - Use Typhoon audio model
6. **PDF parsing** - Extract info from existing documents
