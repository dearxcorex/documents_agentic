# Thai Language LLM Options

## Comparison Matrix

| Model | Params | Thai Performance | License | API | Notes |
|-------|--------|-----------------|---------|-----|-------|
| **Typhoon 2** | 8B-70B | Best open-source | Custom | Yes | SCB10X, multimodal |
| **OpenThaiGPT** | 7B-70B | Excellent | Apache 2.0 | No | Community, beats GPT-3.5 |
| **WangChanGLM** | Various | Good | Apache 2.0 | No | AIResearch.in.th |
| **Claude 3.5/4** | - | Excellent | Proprietary | Yes | Best reasoning |
| **GPT-4** | - | Excellent | Proprietary | Yes | Strong overall |
| **Gemini** | - | Good | Proprietary | Yes | Good multimodal |

---

## Typhoon 2 (Recommended for Thai)

### Overview
- Developed by SCB10X (Thailand)
- Specifically optimized for Thai language
- 2.62x more efficient tokenization for Thai text
- Highest performance on Thai benchmarks

### Model Variants
```
typhoon-v2-8b-instruct     # Fast, good for simple tasks
typhoon-v2-70b-instruct    # Best quality
typhoon-v2-8b-vision       # Image understanding
typhoon-v2-audio           # Speech/audio
```

### Access
- Website: https://opentyphoon.ai/
- HuggingFace: scb10x/typhoon-*
- API: Available through SCB10X

### Strengths
- Native Thai understanding
- Formal Thai writing style
- Thai cultural context awareness
- Government/business document style

### Paper
- https://arxiv.org/abs/2312.13951

---

## OpenThaiGPT

### Overview
- Community-driven open-source project
- Based on Llama-2 architecture
- Focuses on Thai chatbot capabilities

### Model Variants
```
openthaigpt-1.0.0-7b-chat
openthaigpt-1.0.0-13b-chat
openthaigpt-1.0.0-70b-chat  # Best quality
```

### Access
- GitHub: https://github.com/OpenThaiGPT
- HuggingFace: openthaigpt/*

### Strengths
- Fully open-source
- Good for self-hosting
- Active community
- Thai exam performance > GPT-3.5

---

## Claude (Anthropic)

### Why Consider for Thai Documents
- Excellent instruction following
- Strong at formal writing
- Good at maintaining consistent style
- Agentic capabilities (Agent SDK)
- Tool use and MCP integration

### API Access
```python
from anthropic import Anthropic
client = Anthropic()

# or via Agent SDK
from claude_code_sdk import ClaudeSDKClient
```

### Best Use Cases
- Orchestration layer
- Complex reasoning
- Multi-step workflows
- Integration with other tools

---

## Recommended Hybrid Approach

```
┌─────────────────────────────────────────┐
│         Claude (Orchestrator)            │
│  - Workflow management                   │
│  - Tool coordination                     │
│  - Quality validation                    │
└────────────────────┬────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Typhoon 2     │    │   OpenThaiGPT   │
│   (Primary)     │    │   (Fallback)    │
│                 │    │                 │
│ - Thai content  │    │ - Self-hosted   │
│ - Formal style  │    │ - Backup        │
└─────────────────┘    └─────────────────┘
```

### Rationale
1. **Claude** for orchestration - best tool use, reasoning
2. **Typhoon 2** for Thai content - native performance
3. **OpenThaiGPT** as fallback - self-hosted option

---

## Thai Tokenization Efficiency

| Model | Thai Text Efficiency |
|-------|---------------------|
| Typhoon | 2.62x better than GPT-4 |
| OpenThaiGPT | ~2x better than base Llama |
| GPT-4 | Baseline |
| Claude | Similar to GPT-4 |

*Better efficiency = lower cost, faster processing*

---

## Sources
- https://opentyphoon.ai/
- https://arxiv.org/abs/2312.13951
- https://github.com/OpenThaiGPT
- https://huggingface.co/openthaigpt/openthaigpt-1.0.0-70b-chat
- https://www.scb10x.com/en/blog/introducing-typhoon-2-thai-llm
