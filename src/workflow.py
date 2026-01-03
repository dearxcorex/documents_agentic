"""LangGraph workflow for Thai Document Generation with LightRAG"""

from typing import TypedDict, Literal, Annotated
from langgraph.graph import StateGraph, END
import operator

from .rag import get_rag, query, get_entities_and_relations
from .llm import deepseek_complete
from .config import DEFAULT_QUERY_MODE
from .templates import (
    TemplateType,
    get_template,
    get_template_example,
    get_template_features,
    list_templates,
    list_templates_by_category,
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
    template = get_template(state['template_type'])
    search_query = f"{template['category']} {state['template_type']} {state['user_request']}"

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


def extract_user_data(user_request: str) -> dict:
    """Extract specific data from user request"""
    import re

    data = {
        "location": None,
        "doc_number": None,
        "date_range": None,
        "reference_doc": None,
        "year": None,
    }

    # Extract location (จังหวัด) - must be Thai province name pattern
    loc_match = re.search(r'จังหวัด\s*(\S+)', user_request)
    if loc_match:
        data["location"] = loc_match.group(1)
    else:
        # Try พื้นที่
        loc_match = re.search(r'พื้นที่\s*(\S+)', user_request)
        if loc_match:
            data["location"] = loc_match.group(1)

    # Extract document number (สทช pattern)
    doc_match = re.search(r'(สทช\s*\d+[./]?\d*)', user_request)
    if doc_match:
        data["doc_number"] = doc_match.group(1)

    # Extract year (25XX or 256X)
    year_match = re.search(r'(25\d{2}|256\d)', user_request)
    if year_match:
        data["year"] = year_match.group(1)

    # Extract date range
    date_match = re.search(r'วันที่\s*(\d+\s*[-–]\s*\d+\s*\S+\s*\d{4})', user_request)
    if date_match:
        data["date_range"] = date_match.group(1)

    return data


async def generate_draft(state: DocumentState) -> DocumentState:
    """Generate document draft using exact template format"""

    template_type = state['template_type']
    template = get_template(template_type)
    template_example = template['example']
    template_features = template['key_features']
    category = template['category']
    user_request = state['user_request']

    # Extract user data
    user_data = extract_user_data(user_request)

    # Format features as bullet list
    features_text = "\n".join([f"  - {f}" for f in template_features])

    # Build user data section
    user_data_text = ""
    if user_data["doc_number"]:
        user_data_text += f"\n- เลขที่หนังสืออ้างอิง: {user_data['doc_number']}"
    if user_data["location"]:
        user_data_text += f"\n- สถานที่/จังหวัด: {user_data['location']}"
    if user_data["year"]:
        user_data_text += f"\n- ปี พ.ศ.: {user_data['year']}"
    if user_data["date_range"]:
        user_data_text += f"\n- ช่วงวันที่: {user_data['date_range']}"

    prompt = f"""คุณเป็นผู้เชี่ยวชาญในการเขียนหนังสือราชการไทย

##################################
# ข้อมูลจากผู้ใช้ (ต้องใช้ข้อมูลนี้!)
##################################

คำขอ: {user_request}
{user_data_text if user_data_text else ""}

สำคัญมาก: ต้องใช้ข้อมูลจากผู้ใช้ด้านบนเท่านั้น! ห้ามใช้ข้อมูลจากตัวอย่าง!

##################################
# รูปแบบเอกสาร (ดูโครงสร้างเท่านั้น)
##################################

ประเภท: {template_type} ({category})

คุณสมบัติ:
{features_text}

ตัวอย่างโครงสร้าง (ดูรูปแบบการจัดหน้าเท่านั้น ห้ามคัดลอกข้อมูล!):
{template_example}

##################################
# คำสั่ง
##################################

1. ใช้โครงสร้างและรูปแบบจากตัวอย่าง
2. ใส่ข้อมูลจากผู้ใช้เท่านั้น (เลขที่หนังสือ, จังหวัด, วันที่)
3. ห้ามคัดลอกข้อมูลจากตัวอย่าง เช่น:
   - ห้ามใช้ "นครราชสีมา" ถ้าผู้ใช้ไม่ได้ระบุ
   - ห้ามใช้ "สทช 2303.3/19" ถ้าผู้ใช้ระบุเลขอื่น
   - ห้ามใช้ชื่อบุคคลจากตัวอย่าง
4. สร้างเนื้อหาที่สมบูรณ์ ห้ามใส่ [...] หรือช่องว่าง

เอกสาร:"""

    draft = await deepseek_complete(prompt)

    print("Draft generated")
    return {**state, "draft": draft}


async def validate_document(state: DocumentState) -> DocumentState:
    """Validate the generated document based on template type"""

    errors = []
    draft = state['draft']
    template_type = state['template_type']
    template = get_template(template_type)
    category = template['category']
    user_request = state['user_request']

    # Check user data is used (not example data)
    user_data = extract_user_data(user_request)

    # If user provided doc number, check it's in the output
    if user_data["doc_number"]:
        # Normalize for comparison
        user_num = user_data["doc_number"].replace(" ", "")
        if user_num not in draft.replace(" ", ""):
            errors.append(f"User doc number not used: {user_data['doc_number']}")

    # If user provided location, check it's in the output
    if user_data["location"]:
        if user_data["location"] not in draft:
            errors.append(f"User location not used: {user_data['location']}")

    # Validation based on category
    if category == "บันทึกข้อความ":
        # Check for บันทึกข้อความ header
        if "บันทึกข้อความ" not in draft:
            errors.append("Missing header: บันทึกข้อความ")

        # Check for agency
        if "หน่วยงาน" not in draft and "ส่วนราชการ" not in draft:
            errors.append("Missing: หน่วยงาน")

        # Check other required sections
        required = ["ที่", "วันที่", "เรื่อง", "เรียน"]
        for section in required:
            if section not in draft:
                errors.append(f"Missing: {section}")

    elif category == "หนังสือภายนอก":
        # Check required sections
        required = ["เรื่อง", "เรียน", "ขอแสดงความนับถือ"]
        for section in required:
            if section not in draft:
                errors.append(f"Missing: {section}")

    elif category == "รายงานการประชุม":
        # Check for meeting report sections
        required = ["รายงานการประชุม", "ผู้เข้าประชุม", "ระเบียบวาระ", "มติที่ประชุม"]
        for section in required:
            if section not in draft:
                errors.append(f"Missing: {section}")

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
    template_type: TemplateType = "ขออนุมัติเดินทาง",
) -> str:
    """
    Generate a Thai government document based on user request.

    Args:
        user_request: Description of what document to generate
        template_type: Type of template to use

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
    """Show available templates for user selection with categories"""
    print("\n" + "=" * 50)
    print("     เลือกประเภทเอกสาร")
    print("=" * 50)

    categories = list_templates_by_category()
    all_templates = []
    idx = 1

    for cat_name, templates in categories.items():
        print(f"\n[{cat_name}]")
        print("-" * 40)
        for t in templates:
            print(f"  {idx}. {t['name']}")
            print(f"     {t['description']}")
            all_templates.append(t)
            idx += 1

    print()
    return all_templates


async def interactive_generate():
    """Interactive document generation with template selection"""
    templates = show_templates()
    num_templates = len(templates)

    # Get user choice
    while True:
        try:
            choice = input(f"เลือกประเภท (1-{num_templates}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < num_templates:
                template_type = templates[idx]["type"]
                break
            print(f"กรุณาเลือก 1-{num_templates}")
        except ValueError:
            print("กรุณาใส่ตัวเลข")

    # Get user request
    template = get_template(template_type)
    print(f"\nเลือก: {template_type} ({template['category']})")
    request = input("ระบุรายละเอียดเอกสารที่ต้องการ: ").strip()

    if not request:
        request = template['description']

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
            # Command line mode - show help with template types
            if sys.argv[1] in ["-h", "--help", "help"]:
                print("\nUsage: python -m src.workflow [OPTIONS] [REQUEST]")
                print("\nOptions:")
                print("  -t, --template TYPE   Template type (use number or name)")
                print("  -l, --list            List all templates")
                print("  -h, --help            Show this help")
                print("\nExamples:")
                print("  python -m src.workflow")
                print("  python -m src.workflow -l")
                print("  python -m src.workflow -t 1 'ขออนุมัติเดินทางไปราชการ'")
                print("  python -m src.workflow -t ขออนุมัติเดินทาง 'ไปประชุมที่กรุงเทพ'")
                return

            if sys.argv[1] in ["-l", "--list"]:
                show_templates()
                return

            # Parse template flag
            template_type = "ขออนุมัติเดินทาง"  # default
            request_parts = []
            i = 1

            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg in ["-t", "--template"]:
                    if i + 1 < len(sys.argv):
                        template_arg = sys.argv[i + 1]
                        # Check if it's a number
                        try:
                            idx = int(template_arg) - 1
                            templates = list_templates()
                            if 0 <= idx < len(templates):
                                template_type = templates[idx]["type"]
                        except ValueError:
                            # It's a template name
                            if template_arg in TEMPLATES:
                                template_type = template_arg
                        i += 2
                        continue
                request_parts.append(arg)
                i += 1

            request = " ".join(request_parts)
            if not request:
                request = get_template(template_type)['description']

            print(f"Template: {template_type}")
            print(f"Request: {request}\n")

            document = await generate_document(request, template_type)
            print(document)

        await close_rag()

    asyncio.run(main())
