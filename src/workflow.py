"""LangGraph workflow for Thai Document Generation with LightRAG"""

from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END
import operator

from .rag import get_rag, query, get_entities_and_relations
from .llm import deepseek_complete
from .config import DEFAULT_QUERY_MODE
from .templates import (
    TemplateType,
    get_template_example,
    get_template_features,
    list_templates,
    TEMPLATES,
)


class DocumentState(TypedDict):
    """State for document generation workflow"""
    # Input
    user_request: str
    template_type: TemplateType

    # RAG Retrieved Context
    retrieved_context: dict
    entities: list
    relations: list

    # Generation
    draft: str

    # Validation
    validation_errors: Annotated[list[str], operator.add]
    retry_count: int

    # Output
    final_document: str


async def retrieve_context(state: DocumentState) -> DocumentState:
    """Retrieve relevant context from LightRAG"""

    # Create search query combining template type and user request
    search_query = f"{state['template_type']} {state['user_request']}"

    # Get entities and relations
    entities, relations = await get_entities_and_relations(search_query)

    # Get full context
    context = await query(search_query, mode=DEFAULT_QUERY_MODE, only_context=True)

    print(f"Retrieved {len(entities)} entities, {len(relations)} relations")

    return {
        **state,
        "retrieved_context": context,
        "entities": entities,
        "relations": relations,
    }


async def generate_draft(state: DocumentState) -> DocumentState:
    """Generate document draft using exact template format"""

    template_type = state['template_type']
    template_example = get_template_example(template_type)
    template_features = get_template_features(template_type)

    # Format features as bullet list
    features_text = "\n".join([f"  - {f}" for f in template_features])

    prompt = f"""คุณเป็นผู้เชี่ยวชาญในการเขียนหนังสือราชการไทย
ตามระเบียบสำนักนายกรัฐมนตรีว่าด้วยงานสารบรรณ พ.ศ. 2526

ประเภทเอกสาร: {template_type}

คุณสมบัติสำคัญของรูปแบบนี้:
{features_text}

=== ตัวอย่างรูปแบบที่ถูกต้อง (ต้องทำตามนี้เป๊ะ) ===
{template_example}
=== จบตัวอย่าง ===

คำขอของผู้ใช้:
{state['user_request']}

คำสั่งสำคัญมาก:
1. สร้างเอกสารตามรูปแบบในตัวอย่างด้านบนเป๊ะๆ
2. ใส่ข้อมูลจริงทั้งหมด ห้ามใส่ [...] หรือช่องว่างให้กรอก
3. ใช้การจัดหน้าและการเว้นวรรคเหมือนตัวอย่าง
4. {"ใช้เลขไทย ๑. ๒. สำหรับหัวข้อหลัก และ 1.1, 2.1 สำหรับหัวข้อย่อย" if template_type == "บันทึกข้อความ" else "จัดชิดขวาสำหรับที่อยู่และลายเซ็น"}
5. {"สำคัญมาก: 2.1.1, 2.1.2, 2.1.3 ต้องเป็นรายชื่อบุคคลเท่านั้น! เช่น '2.1.1 นายสมชาย ใจดี ตำแหน่ง พนักงาน' ห้ามใส่หัวข้อ เช่น 'ผู้เดินทาง', 'วัตถุประสงค์', 'การเดินทาง'" if template_type == "บันทึกข้อความ" else "สร้างเนื้อหาที่สมบูรณ์"}
6. สร้างเนื้อหาที่สมบูรณ์ ละเอียด เป็นทางการ

เอกสารที่สมบูรณ์:"""

    draft = await deepseek_complete(prompt)

    print("Draft generated")
    return {**state, "draft": draft}


async def validate_document(state: DocumentState) -> DocumentState:
    """Validate the generated document based on template type"""

    errors = []
    draft = state['draft']
    template_type = state['template_type']

    if template_type == "บันทึกข้อความ":
        # Check for บันทึกข้อความ header
        if "บันทึกข้อความ" not in draft:
            errors.append("Missing header: บันทึกข้อความ")

        # Check for agency (accepts both terms)
        if "หน่วยงาน" not in draft and "ส่วนราชการ" not in draft:
            errors.append("Missing: หน่วยงาน")

        # Check for Thai numerals sections
        if "๑." not in draft:
            errors.append("Missing Thai numeral section: ๑.")
        if "๒." not in draft:
            errors.append("Missing Thai numeral section: ๒.")

        # Check other required sections
        required = ["ที่", "วันที่", "เรื่อง", "เรียน"]
        for section in required:
            if section not in draft:
                errors.append(f"Missing: {section}")

    elif template_type == "หนังสือภายนอก":
        # Check for ตราครุฑ mention
        if "ตราครุฑ" not in draft and "[ตราครุฑ]" not in draft:
            # It's OK if not explicitly mentioned, check structure instead
            pass

        # Check required sections
        required = ["ที่", "เรื่อง", "เรียน", "ขอแสดงความนับถือ"]
        for section in required:
            if section not in draft:
                errors.append(f"Missing: {section}")

        # Check for contact info at bottom
        if "โทร" not in draft:
            errors.append("Missing contact info: โทร")

    # Check minimum length
    if len(draft) < 200:
        errors.append("Document too short")

    retry_count = state.get('retry_count', 0)

    if errors:
        print(f"Validation errors: {errors}")
        return {
            **state,
            "validation_errors": errors,
            "retry_count": retry_count + 1,
        }
    else:
        print("Validation passed")
        return {
            **state,
            "validation_errors": [],
            "final_document": draft,
        }


def should_retry(state: DocumentState) -> Literal["generate", "end"]:
    """Determine if we should retry generation"""

    if state.get('validation_errors') and state.get('retry_count', 0) < 3:
        return "generate"
    return "end"


def build_workflow() -> StateGraph:
    """Build the LangGraph workflow"""

    workflow = StateGraph(DocumentState)

    # Add nodes (no classification - user picks template)
    workflow.add_node("retrieve", retrieve_context)
    workflow.add_node("generate", generate_draft)
    workflow.add_node("validate", validate_document)

    # Set entry point
    workflow.set_entry_point("retrieve")

    # Add edges
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "validate")

    # Conditional edge for retry
    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "generate": "generate",
            "end": END,
        }
    )

    return workflow.compile()


# Create compiled workflow
app = build_workflow()


async def generate_document(
    user_request: str,
    template_type: TemplateType = "บันทึกข้อความ",
) -> str:
    """
    Generate a Thai government document based on user request.

    Args:
        user_request: Description of what document to generate
        template_type: Type of template to use ("บันทึกข้อความ" or "หนังสือภายนอก")

    Returns:
        Generated document text
    """
    initial_state = DocumentState(
        user_request=user_request,
        template_type=template_type,
        retrieved_context={},
        entities=[],
        relations=[],
        draft="",
        validation_errors=[],
        retry_count=0,
        final_document="",
    )

    result = await app.ainvoke(initial_state)

    return result.get('final_document') or result.get('draft', '')


def show_templates():
    """Show available templates for user selection"""
    print("\n=== เลือกประเภทเอกสาร ===\n")
    templates = list_templates()
    for i, t in enumerate(templates, 1):
        print(f"{i}. {t['name']}")
        print(f"   {t['description']}")
        print()
    return templates


async def interactive_generate():
    """Interactive document generation with template selection"""
    templates = show_templates()

    # Get user choice
    while True:
        try:
            choice = input("เลือกประเภท (1-2): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(templates):
                template_type = templates[idx]["type"]
                break
            print("กรุณาเลือก 1 หรือ 2")
        except ValueError:
            print("กรุณาใส่ตัวเลข")

    # Get user request
    print(f"\nเลือก: {template_type}")
    request = input("ระบุรายละเอียดเอกสารที่ต้องการ: ").strip()

    if not request:
        request = "ขออนุมัติเดินทางไปราชการ"

    print(f"\nกำลังสร้างเอกสาร...")

    document = await generate_document(request, template_type)

    print("\n" + "=" * 60)
    print("GENERATED DOCUMENT")
    print("=" * 60)
    print(document)

    return document


# CLI interface
if __name__ == "__main__":
    import asyncio
    import sys
    from .rag import close_rag

    async def main():
        if len(sys.argv) < 2:
            # Interactive mode
            await interactive_generate()
        else:
            # Command line mode
            template_type = "บันทึกข้อความ"
            request = " ".join(sys.argv[1:])

            # Check for template flag
            if "--external" in sys.argv or "-e" in sys.argv:
                template_type = "หนังสือภายนอก"
                request = request.replace("--external", "").replace("-e", "").strip()

            print(f"Template: {template_type}")
            print(f"Request: {request}\n")

            document = await generate_document(request, template_type)
            print(document)

        await close_rag()

    asyncio.run(main())
