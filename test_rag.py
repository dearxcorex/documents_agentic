"""Test script for Thai Document RAG System"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.rag import index_directory, query, close_rag, get_entities_and_relations


async def test_index():
    """Test indexing templates"""
    print("\n=== Testing Index ===")
    await index_directory("corpus/templates", "*.md")
    print("Templates indexed successfully!")


async def test_query():
    """Test querying the RAG"""
    print("\n=== Testing Query ===")

    questions = [
        "ตัวอย่างบันทึกข้อความขออนุมัติเดินทาง",
        "รูปแบบหนังสือภายนอก",
        "คำลงท้ายสำหรับหนังสือราชการ",
    ]

    for q in questions:
        print(f"\nQuestion: {q}")
        print("-" * 40)

        # Get entities and relations
        entities, relations = await get_entities_and_relations(q)
        print(f"Entities found: {len(entities)}")
        if entities:
            for e in entities[:3]:
                print(f"  - {e}")

        print(f"Relations found: {len(relations)}")
        if relations:
            for r in relations[:3]:
                print(f"  - {r}")


async def test_generation():
    """Test document generation"""
    print("\n=== Testing Document Generation ===")

    from src.workflow import generate_document

    request = "ขอบันทึกข้อความขออนุมัติเดินทางไปราชการที่เชียงใหม่ วันที่ 15-17 มกราคม 2569"

    print(f"\nRequest: {request}")
    print("-" * 40)

    document = await generate_document(request)

    print("\nGenerated Document:")
    print("=" * 60)
    print(document)
    print("=" * 60)


async def main():
    try:
        # Step 1: Index templates
        await test_index()

        # Step 2: Test queries
        await test_query()

        # Step 3: Test generation (optional - uses DeepSeek API)
        if "--generate" in sys.argv:
            await test_generation()

    finally:
        await close_rag()


if __name__ == "__main__":
    print("Thai Document RAG System Test")
    print("=" * 60)
    asyncio.run(main())
