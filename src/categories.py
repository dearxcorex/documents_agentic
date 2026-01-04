"""Thai Government Document Categories - Dynamic Category-Based System"""

from typing import Literal, TypedDict

# High-level document categories (3 options instead of 13 templates)
CategoryType = Literal[
    "หนังสือภายใน",      # Internal memo (บันทึกข้อความ)
    "หนังสือภายนอก",     # External letter
    "รายงานการประชุม",   # Meeting minutes
]

class CategoryInfo(TypedDict):
    """Category information structure"""
    name: str
    name_en: str
    description: str
    keywords: list[str]
    required_sections: list[str]
    optional_sections: list[str]


# Category definitions with validation rules
CATEGORIES: dict[CategoryType, CategoryInfo] = {
    "หนังสือภายใน": {
        "name": "หนังสือภายใน",
        "name_en": "Internal Memo",
        "description": "บันทึกข้อความภายในหน่วยงาน เช่น ขออนุมัติ รายงานผล เชิญประชุม",
        "keywords": [
            "บันทึกข้อความ", "ขออนุมัติ", "รายงาน", "เรียน", "หน่วยงาน",
            "ตรวจสอบ", "เชิญประชุม", "แจ้ง", "ขอความอนุเคราะห์",
            "เดินทาง", "คลื่นความถี่", "ทุบทำลาย", "สถานี"
        ],
        "required_sections": [
            "บันทึกข้อความ",  # Header
            "ส่วนราชการ",     # Agency (ส่วนราชการ per official format)
            "ที่",            # Document number
            "วันที่",         # Date
            "เรื่อง",         # Subject
            "เรียน",          # To
            "เรื่องเดิม",     # Background (required for all internal memos)
        ],
        "optional_sections": [
            "จึงเรียนมาเพื่อ",  # Closing
        ],
        # Document must have ONE of these content section patterns:
        "content_patterns": [
            ["เรื่องเพื่อพิจารณา"],  # For requests/approvals (ขออนุมัติ)
            ["ข้อเท็จจริง"],          # For reports (รายงานผล)
        ],
    },
    "หนังสือภายนอก": {
        "name": "หนังสือภายนอก",
        "name_en": "External Letter",
        "description": "หนังสือติดต่อภายนอกหน่วยงาน เช่น เชิญตรวจร่วม ขอรื้อถอน ขอขยายสัญญาณ",
        "keywords": [
            "เรียน", "อ้างถึง", "ขอแสดงความนับถือ", "สิ่งที่ส่งมาด้วย",
            "บริษัท", "ผู้จัดการ", "ผู้อำนวยการ", "เชิญ", "ขอความอนุเคราะห์",
            "ตรวจสอบร่วม", "รื้อถอน", "ขยายสัญญาณ"
        ],
        "required_sections": [
            "เรื่อง",           # Subject
            "เรียน",            # To (external)
            "ขอแสดงความนับถือ",  # Formal closing
        ],
        "optional_sections": [
            "อ้างถึง",          # Reference
            "สิ่งที่ส่งมาด้วย",  # Attachments
            "ที่อยู่",          # Address header
        ],
    },
    "รายงานการประชุม": {
        "name": "รายงานการประชุม",
        "name_en": "Meeting Minutes",
        "description": "บันทึกรายงานการประชุมคณะกรรมการหรือคณะทำงาน",
        "keywords": [
            "รายงานการประชุม", "คณะกรรมการ", "ครั้งที่", "ผู้เข้าประชุม",
            "ระเบียบวาระ", "มติที่ประชุม", "ประธาน", "เลขานุการ",
            "เริ่มประชุม", "เลิกประชุม"
        ],
        "required_sections": [
            "รายงานการประชุม",   # Header
            "ผู้เข้าประชุม",     # Attendees
            "ระเบียบวาระ",       # Agenda items
            "มติที่ประชุม",      # Resolutions
        ],
        "optional_sections": [
            "ครั้งที่",         # Meeting number
            "เริ่มประชุมเวลา",  # Start time
            "เลิกประชุมเวลา",   # End time
            "ณ",               # Location
        ],
    },
}


def get_category(category_type: CategoryType) -> CategoryInfo:
    """Get category info by type"""
    return CATEGORIES.get(category_type, CATEGORIES["หนังสือภายใน"])


def get_category_keywords(category_type: CategoryType) -> list[str]:
    """Get keywords for a category"""
    return CATEGORIES.get(category_type, CATEGORIES["หนังสือภายใน"])["keywords"]


def get_required_sections(category_type: CategoryType) -> list[str]:
    """Get required sections for validation"""
    return CATEGORIES.get(category_type, CATEGORIES["หนังสือภายใน"])["required_sections"]


def list_categories() -> list[dict]:
    """List all available categories for user selection"""
    return [
        {
            "type": k,
            "name": v["name"],
            "name_en": v["name_en"],
            "description": v["description"],
        }
        for k, v in CATEGORIES.items()
    ]


def get_category_names() -> list[str]:
    """Get list of category type names"""
    return list(CATEGORIES.keys())


# Classification prompt for LLM
CLASSIFICATION_PROMPT = """คุณเป็นผู้เชี่ยวชาญในการจำแนกประเภทหนังสือราชการไทย

จากคำขอของผู้ใช้ด้านล่าง ให้จำแนกว่าเป็นหนังสือประเภทใด:

1. หนังสือภายใน - บันทึกข้อความภายในหน่วยงาน เช่น ขออนุมัติ รายงานผล เชิญประชุม
2. หนังสือภายนอก - หนังสือติดต่อภายนอกหน่วยงาน เช่น เชิญตรวจร่วม ขอรื้อถอน
3. รายงานการประชุม - บันทึกรายงานการประชุมคณะกรรมการ

คำขอ: {user_request}

ตอบเฉพาะชื่อประเภท (หนังสือภายใน, หนังสือภายนอก, หรือ รายงานการประชุม):"""
