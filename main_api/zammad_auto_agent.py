#main_api/zammad_auto_agent.py
import os
import requests
import mysql.connector
import asyncio


from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv
from main_api.intent_classifier import detect_intent

from main_api.tools.repair_flow_tool import get_solution_or_fallback
from main_api.tools.zammad_tool import assign_ticket_to_ai, get_ticket_title_by_id
from main_api.llm_router import ask_openai_then_local, ask_hermes, ask_openai

load_dotenv()

ZAMMAD_URL = os.getenv("ZAMMAD_URL")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN")
AI_USER_ID = 3
DEFAULT_OWNER_ID = 5

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB")
}

router = APIRouter()
conversation_counter = {}

class ZammadWebhookPayload(BaseModel):
    ticket: dict
    article: dict = {}

def is_handover_requested(text: str) -> bool:
    keywords = [
    "ขอให้เจ้าหน้าที่", "ขอช่าง", "รบกวนช่วยตรวจสอบ", "อยากคุยกับคน", 
    "ส่งต่อให้คน", "ไม่อยากคุยกับ ai",
    "talk to staff", "need technician", "want human support"
    ]
    return any(k in text.lower() for k in keywords)
    print(f"[ASSIGN] 🎯 Ticket {ticket_id} assigned to skill_owner {skill_owner}")

def is_critical_issue(text: str) -> bool:
    critical_keywords = [
        "จอแตก", "เครื่องดับ", "เข้าไม่ได้เลย", "เครือข่ายล่ม", "เสียหาย", "เปิดไม่ติด", "boot ไม่ได้", "ดับทั้งหมด"
    ]
    return any(k in text.lower() for k in critical_keywords)

def is_question_too_general_or_unsolvable(text: str) -> bool:
    keywords = ["ดับทั้งหมด", "ใช้งานไม่ได้", "ไม่เปิด", "เครือข่ายล่ม", "จอดำ", "ซับซ้อน"]
    return any(word in text.lower() for word in keywords)

def get_ticket(ticket_id):
    headers = {"Authorization": f"Token {ZAMMAD_TOKEN}"}
    return requests.get(f"{ZAMMAD_URL}/tickets/{ticket_id}", headers=headers).json()

def assign_ticket_owner(ticket_id, owner_id):
    headers = {"Authorization": f"Token {ZAMMAD_TOKEN}", "Content-Type": "application/json"}
    requests.put(f"{ZAMMAD_URL}/tickets/{ticket_id}", headers=headers, json={"owner_id": owner_id})
    print(f"[ASSIGN] 🎯 Ticket {ticket_id} assigned to owner_id {owner_id}")

def reply_to_ticket(ticket_id, message):
    headers = {"Authorization": f"Token {ZAMMAD_TOKEN}", "Content-Type": "application/json"}
    data = {
        "ticket_id": ticket_id,
        "subject": "AI ตอบกลับ",
        "body": message,
        "type": "note",
        "internal": False
    }
    requests.post(f"{ZAMMAD_URL}/ticket_articles", headers=headers, json=data)

def search_and_save_solution(text: str) -> str:
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT problem_description FROM problem_solutions
        WHERE LOWER(problem_title) LIKE %s
        LIMIT 1
        """
        cursor.execute(query, (f"%{text.lower()}%",))
        row = cursor.fetchone()

        if row:
            conn.close()
            return row["problem_description"]

        openai_summary = get_openai_response(text)
        description = openai_summary.strip()

        insert_query = """
        INSERT INTO problem_solutions (problem_title, problem_description, created_at)
        VALUES (%s, %s, NOW())
        """
        cursor.execute(insert_query, (text[:255], description))
        conn.commit()
        conn.close()

        return description
    except Exception as e:
        print("[DB Error]", e)
        return ""

def detect_skill_owner(text: str) -> int:
    text = text.lower()
    if "apple" in text:
        return 4
    elif any(word in text for word in ["network", "router", "switch"]):
        return 15
    elif "signage" in text or "display" in text:
        return 16
    return DEFAULT_OWNER_ID

@router.post("/zammad-webhook")
async def handle_zammad_webhook(payload: ZammadWebhookPayload):
    ticket_id = payload.ticket.get("id")
    ticket_title = payload.ticket.get("title", "")
    article_body = payload.article.get("body", "").strip()
    article_from = str(payload.article.get("from", "")).lower()

    if "helpdesk" in article_from or "wtc.co.th" in article_from or "true digital" in article_from:
        print(f"[Webhook] 🚫 Skipped (from = {article_from}) - internal update")
        return {"status": "ignored"}
    
    if not ticket_id or not article_body:
        print("[Webhook] ⛔ Ignored (missing ticket_id or body)")
        return {"status": "ignored"}
    
    print(f"[Webhook] 👤 article_from = {article_from}")
    print(f"[TICKET] id = {ticket_id}")
    print(f"[TITLE] {ticket_title}")
    print(f"[ARTICLE] {article_body}")

    ticket = get_ticket(ticket_id)
    owner_id = ticket.get("owner_id")
    print(f"[TICKET] owner_id = {owner_id}")

    full_text = f"{ticket_title}\n{article_body}"
    intent = detect_intent(full_text)
    print(f"[INTENT] 🔍 OpenAI analyzed intent: {intent}")

    # Critical case
    if intent == "repair" and is_critical_issue(full_text):
        skill_owner = detect_skill_owner(full_text)
        assign_ticket_owner(ticket_id, skill_owner)
        reply_to_ticket(ticket_id, "จากที่คุณแจ้งมา ดูเหมือนปัญหานี้จำเป็นต้องให้เจ้าหน้าที่ของเราตรวจสอบเพิ่มเติมครับ ThunJai ได้ดำเนินการส่งเรื่องให้ผู้เชี่ยวชาญดูแลต่อแล้วครับ ขอบคุณที่ติดต่อมา")
        print(f"[Webhook] 🚑 Critical issue detected → escalated to owner_id={skill_owner}")
        return {"status": "critical_assigned", "owner_id": skill_owner}
        
    if is_handover_requested(full_text):
        skill_owner = detect_skill_owner(full_text)
        assign_ticket_owner(ticket_id, skill_owner)
        reply_to_ticket(ticket_id, "Thunjai ได้ส่งเรื่องของคุณให้เจ้าหน้าที่ผู้เชี่ยวชาญแล้วค่ะ ขอขอบคุณที่ติดต่อมา")
        print("[Webhook] 🧍‍♂️ User requested human support → escalated")
        return {"status": "handover_by_user", "owner_id": skill_owner}
    
    if owner_id in [1, None]:
        assign_ticket_owner(ticket_id, AI_USER_ID)
        owner_id = AI_USER_ID
    elif owner_id != AI_USER_ID:
        print(f"[Webhook] ❌ Ticket already assigned to {owner_id}")
        return {"status": "skipped"}

    if intent == "handover":
        skill_owner = detect_skill_owner(full_text)
        assign_ticket_owner(ticket_id, skill_owner)
        reply_to_ticket(ticket_id, "Thunjai ได้ส่งเรื่องของคุณให้เจ้าหน้าที่ผู้เชี่ยวชาญแล้วค่ะ ขอขอบคุณที่ติดต่อมา")
        print("[Webhook] 🚨 Escalated to human agent")
        return {"status": "handover"}

    if is_question_too_general_or_unsolvable(full_text) or conversation_counter.get(ticket_id, 0) >= 3:
        skill_owner = detect_skill_owner(full_text)
        assign_ticket_owner(ticket_id, skill_owner)
        reply_to_ticket(ticket_id, "Thunjai ได้ส่งเรื่องของคุณให้เจ้าหน้าที่ผู้เชี่ยวชาญแล้วค่ะ ขอขอบคุณที่ติดต่อมา")
        print("[Webhook] 🧑‍💻 Escalated to human agent")
        return {"status": "assigned_to_human", "owner_id": skill_owner}

    # ✅ ใช้ OpenAI → ถ้ามีข้อมูล → ส่งไป Hermes
    context = search_and_save_solution(full_text)
    prompt = f"สรุปและตอบลูกค้าแบบมืออาชีพ (intent: {intent}) สำหรับ user: zammad_{ticket_id}"
    reply_text = ask_hermes(prompt=prompt, context=context)

    print(f"[Hermes] Prompt: {prompt}")
    print(f"[Hermes] Context: {context[:100]}...")

    if conversation_counter.get(ticket_id, 0) == 0:
        greeting = "สวัสดีครับ ผม Thunjai ผู้ช่วย AI ที่ดูแลเรื่องการ Support สำหรับคุณ\n\n"
        reply_text = greeting + reply_text

    conversation_counter[ticket_id] = conversation_counter.get(ticket_id, 0) + 1
    print(f"[TURN] 🤖 AI responded {conversation_counter[ticket_id]} time(s)")
    
    reply_to_ticket(ticket_id, reply_text)

    return {
        "status": "ai_replied",
        "turn": conversation_counter[ticket_id],
        "intent": intent,
        "reply": reply_text[:80] + "..."
    }

async def handle_ticket_async(ticket_id: int):
    ticket = get_ticket(ticket_id)
    ticket_title = ticket.get("title", "")
    owner_id = ticket.get("owner_id")
    article_body = get_last_article(ticket_id)
    full_text = f"{ticket_title}\n{article_body}"
    intent = detect_intent(full_text)

    if intent == "repair" and is_critical_issue(full_text):
        skill_owner = detect_skill_owner(full_text)
        assign_ticket_owner(ticket_id, skill_owner)
        reply_to_ticket(ticket_id, "จากที่คุณแจ้งมา ดูเหมือนปัญหานี้จำเป็นต้องให้เจ้าหน้าที่ของเราตรวจสอบเพิ่มเติมครับ ThunJai ได้ดำเนินการส่งเรื่องให้ผู้เชี่ยวชาญดูแลต่อแล้วครับ ขอบคุณที่ติดต่อมา")
        return

    if is_handover_requested(full_text):
        skill_owner = detect_skill_owner(full_text)
        assign_ticket_owner(ticket_id, skill_owner)
        reply_to_ticket(ticket_id, "Thunjai ได้ส่งเรื่องของคุณให้เจ้าหน้าที่ผู้เชี่ยวชาญแล้วค่ะ ขอขอบคุณที่ติดต่อมา")
        return

    if owner_id in [1, None]:
        assign_ticket_owner(ticket_id, AI_USER_ID)
    elif owner_id != AI_USER_ID:
        return

    if intent == "handover" or is_question_too_general_or_unsolvable(full_text) or conversation_counter.get(ticket_id, 0) >= 3:
        skill_owner = detect_skill_owner(full_text)
        assign_ticket_owner(ticket_id, skill_owner)
        reply_to_ticket(ticket_id, "Thunjai ได้ส่งเรื่องของคุณให้เจ้าหน้าที่ผู้เชี่ยวชาญแล้วค่ะ ขอขอบคุณที่ติดต่อมา")
        return

    solution = search_and_save_solution(full_text)
    reply_text = await ask_local_llm_async(solution, intent=intent, user_id=f"zammad_{ticket_id}")

    if conversation_counter.get(ticket_id, 0) == 0:
        reply_text = "สวัสดีครับ ผม Thunjai ผู้ช่วย AI ที่ดูแลเรื่องการ Support สำหรับคุณ\n\n" + reply_text

    conversation_counter[ticket_id] = conversation_counter.get(ticket_id, 0) + 1
    reply_to_ticket(ticket_id, reply_text)
