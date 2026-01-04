"""LangGraph workflow for Thai Document Generation - Dynamic Category-Based System"""

from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, END

from .rag import query, get_entities_and_relations
from .llm import deepseek_complete
from .config import DEFAULT_QUERY_MODE
from .categories import (
    CategoryType,
    get_category,
    get_required_sections,
    list_categories,
    CATEGORIES,
    CLASSIFICATION_PROMPT,
)
from .templates import (
    get_templates_for_category,
    get_random_example_for_category,
    get_draft_template,
    get_placeholders_for_category,
    PLACEHOLDERS,
)


class DocumentState(TypedDict):
    """State for document generation workflow"""
    # Input
    user_request: str
    category: Optional[CategoryType]  # User-selected or auto-classified

    # Classification
    auto_category: Optional[CategoryType]  # LLM-classified category
    classification_confidence: float

    # RAG Retrieved Context
    rag_context: str  # Full RAG response
    rag_examples: list[str]  # Similar document examples from RAG
    entities: list
    relations: list

    # Generation
    draft: str

    # Validation - NOT using operator.add to avoid accumulation
    validation_errors: list[str]
    retry_count: int
    is_valid: bool  # Flag to indicate validation passed

    # Output
    final_document: str


async def classify_category(state: DocumentState) -> DocumentState:
    """Classify user request into one of 3 categories using LLM"""

    # If user already selected category, skip classification
    if state.get('category'):
        print(f"Category pre-selected: {state['category']}")
        return {
            **state,
            "auto_category": state['category'],
            "classification_confidence": 1.0,
        }

    user_request = state['user_request']
    prompt = CLASSIFICATION_PROMPT.format(user_request=user_request)

    response = await deepseek_complete(prompt)
    response = response.strip()

    # Parse response to get category
    category = None
    confidence = 0.8

    for cat_name in CATEGORIES.keys():
        if cat_name in response:
            category = cat_name
            break

    # Default to internal memo if unclear
    if not category:
        category = "หนังสือภายใน"
        confidence = 0.5

    print(f"Auto-classified: {category} (confidence: {confidence})")

    return {
        **state,
        "category": category,
        "auto_category": category,
        "classification_confidence": confidence,
    }


async def retrieve_context(state: DocumentState) -> DocumentState:
    """Retrieve relevant context from LightRAG based on category"""

    category = state.get('category') or state.get('auto_category') or "หนังสือภายใน"
    category_info = get_category(category)
    user_request = state['user_request']

    # Build more specific search query for better RAG results
    # Extract key action words from user request
    action_keywords = []
    if "ขออนุมัติ" in user_request:
        action_keywords.append("ขออนุมัติ")
    if "เดินทาง" in user_request:
        action_keywords.append("เดินทาง ปฏิบัติงาน")
    if "ตรวจสอบ" in user_request:
        action_keywords.append("ตรวจสอบ คลื่นความถี่")
    if "รายงาน" in user_request:
        action_keywords.append("รายงานผล")

    # Combine action keywords with category
    action_str = " ".join(action_keywords) if action_keywords else ""
    search_query = f"บันทึกข้อความ {action_str} {user_request[:100]}"

    # Get entities and relations
    entities, relations = await get_entities_and_relations(search_query)

    # Get full RAG context
    rag_context = await query(search_query, mode=DEFAULT_QUERY_MODE, only_context=True)

    # Try to extract example documents from RAG
    rag_examples = []
    if isinstance(rag_context, dict) and 'context' in rag_context:
        context_str = rag_context.get('context', '')
        # RAG context may contain document examples
        rag_examples = [context_str] if context_str else []
    elif isinstance(rag_context, str) and rag_context:
        rag_examples = [rag_context]

    # If RAG returns little context, use template examples as fallback
    if not rag_examples or len(str(rag_examples)) < 200:
        fallback_example = get_random_example_for_category(category)
        if fallback_example:
            rag_examples.append(fallback_example)
            print("Using template fallback for examples")

    print(f"Retrieved {len(entities)} entities, {len(relations)} relations")
    print(f"RAG examples: {len(rag_examples)}")

    return {
        **state,
        "rag_context": str(rag_context),
        "rag_examples": rag_examples,
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
        "names": [],
        "organization": None,
    }

    # Extract location (จังหวัด) - Thai province names are typically short (2-10 chars)
    # Stop at common action words or punctuation
    loc_match = re.search(r'จังหวัด\s*([ก-๙]+?)(?:ตรวจ|เพื่อ|ระหว่าง|วันที่|ใน|และ|$|\s)', user_request)
    if loc_match:
        data["location"] = loc_match.group(1)
    else:
        loc_match = re.search(r'พื้นที่\s*([ก-๙]+?)(?:ตรวจ|เพื่อ|ระหว่าง|วันที่|ใน|และ|$|\s)', user_request)
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

    # Extract organization/company names
    org_match = re.search(r'บริษัท\s*([^\s,]+)', user_request)
    if org_match:
        data["organization"] = org_match.group(1)

    return data


async def generate_draft(state: DocumentState) -> DocumentState:
    """Generate document by filling in placeholder template"""

    category = state.get('category') or state.get('auto_category') or "หนังสือภายใน"
    category_info = get_category(category)
    user_request = state['user_request']
    rag_examples = state.get('rag_examples', [])

    # Extract user data
    user_data = extract_user_data(user_request)

    # Detect if it's a request or report for internal memos
    # Priority: ขออนุมัติ always uses REQUEST template (เรื่องเพื่อพิจารณา)
    is_approval_request = "ขออนุมัติ" in user_request or "ขอพิจารณา" in user_request
    is_report = any(kw in user_request for kw in ["รายงานผล", "ผลการตรวจสอบ", "ผลการดำเนินการ"])

    # ขออนุมัติ takes precedence over report keywords
    use_request_template = is_approval_request or (not is_report and "ขอ" in user_request)

    # Get the appropriate draft template with placeholders
    draft_template = get_draft_template(category, is_request=use_request_template)

    # Get placeholders for this category
    placeholders = get_placeholders_for_category(category)

    # Build placeholder descriptions for the prompt
    placeholder_list = []
    for name, info in placeholders.items():
        if f"[{name}]" in draft_template:
            req = "จำเป็น" if info.get("required", False) else "ถ้ามี"
            placeholder_list.append(f"  - [{name}]: {info['description']} ({req})")
            placeholder_list.append(f"    ตัวอย่าง: {info['example']}")

    placeholders_text = "\n".join(placeholder_list)

    # Build user data section
    user_data_text = ""
    if user_data["doc_number"]:
        user_data_text += f"\n- เลขที่หนังสือ: {user_data['doc_number']}"
    if user_data["location"]:
        user_data_text += f"\n- สถานที่/จังหวัด: {user_data['location']}"
    if user_data["year"]:
        user_data_text += f"\n- ปี พ.ศ.: {user_data['year']}"
    if user_data["date_range"]:
        user_data_text += f"\n- ช่วงวันที่: {user_data['date_range']}"
    if user_data["organization"]:
        user_data_text += f"\n- หน่วยงาน/บริษัท: {user_data['organization']}"

    # Build example section from RAG (limit to 1 example for reference)
    example_text = ""
    if rag_examples:
        example_text = f"\n--- ตัวอย่างอ้างอิง (ดูรูปแบบเท่านั้น) ---\n{rag_examples[0][:1500]}\n"

    prompt = f"""<role>
คุณเป็นเจ้าหน้าที่ธุรการผู้เชี่ยวชาญในการร่างหนังสือราชการไทยตามระเบียบสำนักนายกรัฐมนตรี
</role>

<task>
กรอกแบบฟอร์มหนังสือราชการโดยแทนที่ [PLACEHOLDER] ทุกตัวด้วยเนื้อหาจริง
</task>

<input>
คำขอ: {user_request}
ประเภท: {category} ({category_info['name_en']})
{user_data_text if user_data_text else ""}
</input>

<template>
{draft_template}
</template>

<placeholders>
{placeholders_text}
</placeholders>

<reference>
{example_text if example_text else "(ใช้รูปแบบมาตรฐานราชการ)"}
</reference>

<rules>
1. แทนที่ [PLACEHOLDER] ทุกตัวด้วยเนื้อหาจริงที่เหมาะสม
2. ห้ามมี [ หรือ ] เหลือในเอกสารสุดท้าย
3. ใช้ข้อมูลจาก <input> เป็นหลัก ถ้าไม่มีให้สร้างข้อมูลที่สมเหตุสมผล
4. ใช้เลขไทย ๑. ๒. ๓. สำหรับลำดับหัวข้อ
5. ใช้ปี พ.ศ. (เช่น ๒๕๖๘) ไม่ใช่ ค.ศ.
6. รักษาโครงสร้างและการย่อหน้าตาม <template>
7. ภาษาราชการ: ใช้คำสุภาพ เป็นทางการ
</rules>

<output_format>
ตอบเฉพาะเอกสารที่กรอกแล้วเท่านั้น ไม่ต้องมีคำอธิบายนำหรือสรุปท้าย
เริ่มต้นด้วย "บันทึกข้อความ" หรือเนื้อหาเอกสารทันที
</output_format>

<document>"""

    draft = await deepseek_complete(prompt)

    print("Draft generated using RAG context")
    return {**state, "draft": draft}


async def validate_document(state: DocumentState) -> DocumentState:
    """Validate the generated document based on category requirements"""
    import re

    errors = []
    draft = state['draft']
    category = state.get('category') or state.get('auto_category') or "หนังสือภายใน"
    user_request = state['user_request']

    # Check for unreplaced placeholders [PLACEHOLDER]
    unreplaced = re.findall(r'\[([A-Z_]+)\]', draft)
    if unreplaced:
        errors.append(f"Unreplaced placeholders: {', '.join(unreplaced[:5])}")

    # Get required sections for this category
    required_sections = get_required_sections(category)

    # Check required sections exist
    for section in required_sections:
        if section not in draft:
            errors.append(f"Missing required section: {section}")

    # For หนังสือภายใน, check content pattern (must have either เรื่องเพื่อพิจารณา OR ข้อเท็จจริง)
    if category == "หนังสือภายใน":
        has_consideration = "เรื่องเพื่อพิจารณา" in draft
        has_facts = "ข้อเท็จจริง" in draft
        if not has_consideration and not has_facts:
            errors.append("Missing content section: ต้องมี 'เรื่องเพื่อพิจารณา' หรือ 'ข้อเท็จจริง'")

    # Check user data is used (not example data)
    user_data = extract_user_data(user_request)

    if user_data["doc_number"]:
        user_num = user_data["doc_number"].replace(" ", "")
        if user_num not in draft.replace(" ", ""):
            errors.append(f"User doc number not used: {user_data['doc_number']}")

    if user_data["location"]:
        if user_data["location"] not in draft:
            errors.append(f"User location not used: {user_data['location']}")

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
            "is_valid": False,
        }
    else:
        print("Validation passed")
        return {
            **state,
            "validation_errors": [],
            "is_valid": True,
            "final_document": draft,
        }


def should_retry(state: DocumentState) -> Literal["generate", "end"]:
    """Determine if we should retry generation"""

    # If valid, stop
    if state.get('is_valid', False):
        return "end"

    # If not valid but haven't exceeded retries, retry
    if state.get('retry_count', 0) < 3:
        return "generate"

    # Max retries exceeded, stop
    return "end"


def build_workflow() -> StateGraph:
    """Build the LangGraph workflow with category classification"""

    workflow = StateGraph(DocumentState)

    # Add nodes: classify → retrieve → generate → validate
    workflow.add_node("classify", classify_category)
    workflow.add_node("retrieve", retrieve_context)
    workflow.add_node("generate", generate_draft)
    workflow.add_node("validate", validate_document)

    # Set entry point
    workflow.set_entry_point("classify")

    # Add edges
    workflow.add_edge("classify", "retrieve")
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
    category: Optional[CategoryType] = None,
) -> str:
    """
    Generate a Thai government document based on user request.

    Args:
        user_request: Description of what document to generate
        category: Optional category (auto-classified if not provided)

    Returns:
        Generated document text
    """
    initial_state = DocumentState(
        user_request=user_request,
        category=category,
        auto_category=None,
        classification_confidence=0.0,
        rag_context="",
        rag_examples=[],
        entities=[],
        relations=[],
        draft="",
        validation_errors=[],
        retry_count=0,
        is_valid=False,
        final_document="",
    )

    result = await app.ainvoke(initial_state)

    return result.get('final_document') or result.get('draft', '')


def show_categories():
    """Show available categories for user selection"""
    print("\n" + "=" * 50)
    print("     เลือกประเภทเอกสาร")
    print("=" * 50)

    categories = list_categories()

    for i, cat in enumerate(categories, 1):
        print(f"\n  {i}. {cat['name']} ({cat['name_en']})")
        print(f"     {cat['description']}")

    print()
    return categories


async def interactive_generate():
    """Interactive document generation with category selection"""
    categories = show_categories()
    num_categories = len(categories)

    # Get user choice
    while True:
        try:
            choice = input(f"เลือกประเภท (1-{num_categories}) หรือ Enter เพื่อให้ระบบเลือกอัตโนมัติ: ").strip()

            if not choice:
                # Auto-classify mode
                category = None
                print("จะจำแนกประเภทอัตโนมัติจากคำขอ")
                break

            idx = int(choice) - 1
            if 0 <= idx < num_categories:
                category = categories[idx]["type"]
                break
            print(f"กรุณาเลือก 1-{num_categories}")
        except ValueError:
            print("กรุณาใส่ตัวเลขหรือกด Enter")

    # Get user request
    if category:
        cat_info = get_category(category)
        print(f"\nเลือก: {category} ({cat_info['name_en']})")

    request = input("ระบุรายละเอียดเอกสารที่ต้องการ: ").strip()

    if not request:
        request = "สร้างเอกสารตัวอย่าง"

    print(f"\nกำลังสร้างเอกสาร...")

    document = await generate_document(request, category)

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
            if sys.argv[1] in ["-h", "--help", "help"]:
                print("\nUsage: python -m src.workflow [OPTIONS] [REQUEST]")
                print("\nOptions:")
                print("  -c, --category TYPE   Category type (1=ภายใน, 2=ภายนอก, 3=ประชุม)")
                print("  -l, --list            List all categories")
                print("  -h, --help            Show this help")
                print("\nCategories:")
                print("  1. หนังสือภายใน    - Internal memo (บันทึกข้อความ)")
                print("  2. หนังสือภายนอก   - External letter")
                print("  3. รายงานการประชุม - Meeting minutes")
                print("\nExamples:")
                print("  python -m src.workflow")
                print("  python -m src.workflow -l")
                print("  python -m src.workflow -c 1 'ขออนุมัติเดินทางไปราชการ'")
                print("  python -m src.workflow 'รายงานผลการตรวจสอบคลื่นความถี่'")
                return

            if sys.argv[1] in ["-l", "--list"]:
                show_categories()
                return

            # Parse category flag
            category = None
            request_parts = []
            i = 1

            category_names = list(CATEGORIES.keys())

            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg in ["-c", "--category"]:
                    if i + 1 < len(sys.argv):
                        cat_arg = sys.argv[i + 1]
                        # Check if it's a number (1, 2, 3)
                        try:
                            idx = int(cat_arg) - 1
                            if 0 <= idx < len(category_names):
                                category = category_names[idx]
                        except ValueError:
                            # It's a category name
                            if cat_arg in CATEGORIES:
                                category = cat_arg
                        i += 2
                        continue
                request_parts.append(arg)
                i += 1

            request = " ".join(request_parts)
            if not request:
                request = "สร้างเอกสารตัวอย่าง"

            if category:
                print(f"Category: {category}")
            else:
                print("Category: Auto-detect")
            print(f"Request: {request}\n")

            document = await generate_document(request, category)
            print(document)

        await close_rag()

    asyncio.run(main())
