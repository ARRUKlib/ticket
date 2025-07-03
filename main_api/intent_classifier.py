import os
import pymysql
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def fallback_detect_intent(question: str) -> str:
    q = question.lower()
    if "ใบเสนอราคา" in q or "quotation" in q:
        return "quotation"
    elif any(word in q for word in ["แจ้งซ่อม", "เสีย", "พัง", "repair", "ปัญหา"]):
        return "repair"
    elif "ติดต่อ" in q or "เบอร์" in q or "sale" in q:
        return "contact"
    elif "wtc ขายอะไร" in q or "มีสินค้า" in q or "product" in q:
        return "product"
    return "general"

def detect_intent(question: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an intent classifier for a helpdesk system. "
                        "Return one of: quotation, repair, contact, product, company, general."
                    )
                },
                {"role": "user", "content": question}
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        print("[Intent Classification Fallback]", e)
        return fallback_detect_intent(question)

def is_zammad_repair_intent(text: str) -> bool:
    lower = text.lower()
    keyword = ["แจ้งซ่อม", "เสีย", "ปัญหา", "error", "network", "mac", "จอ", "ระบบ"]
    return any(k in lower for k in keyword)


def is_related_to_wtc(text: str) -> bool:
    connection = pymysql.connect(host="150.95.30.49", user="link_Q", password="Lifelinkk1223", db="test")
    cursor = connection.cursor()
    cursor.execute("SELECT keyword FROM company_info")
    keywords = [row[0].lower() for row in cursor.fetchall()]
    connection.close()
    return any(k in text.lower() for k in keywords)

def classify_intent_zammad(text: str) -> str:
    if is_repair_related(text) and is_related_to_wtc(text):
        return "repair"
    return "not_repair"