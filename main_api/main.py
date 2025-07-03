# main.py

import os
import logging
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from main_api import auth
from main_api.intent_classifier import detect_intent 
from main_api.llm_router import ask_openai, ask_hermes, ask_local_llm
from main_api.rag_mysql_retriever import get_context_from_mysql
from main_api.utils import detect_language, log_event
from main_api.memory_mysql import get_chat_history_from_db, save_chat_to_db
from main_api.zammad_auto_agent import router as zammad_router
from main_api.zammad_auto_agent import handle_ticket_async



logging.basicConfig(level=logging.INFO)
app = FastAPI()

app.include_router(auth.router)
app.include_router(zammad_router)

app.mount("/static", StaticFiles(directory="main_api/frontend"), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("main_api/frontend/index.html", "r", encoding="utf-8") as f:
        return f.read()

class AskRequest(BaseModel):
    user_id: str
    question: str

@app.post("/ask")
def ask(req: AskRequest):
    user_id = req.user_id.strip()
    question = req.question.strip()
    logging.info(f"[REQ] from {user_id}: {question}")

    language = detect_language(question)
    logging.info(f"[LANG] = {language}")

    # ดึงข้อมูล ticket_id
    ticket_id = None
    if user_id.startswith("zammad_"):
        try:
            ticket_id = int(user_id.split("_")[1])
        except:
            ticket_id = None

    owner_id = get_owner_id_by_ticket_id(ticket_id)
    ticket_state = get_ticket_state_by_id(ticket_id)
    logging.info(f"[TICKET] owner_id={owner_id}, state={ticket_state}")

    # ✅ ถ้า owner เป็น 1 (ยังว่าง) หรือ 3 (AI) → takeover
    if owner_id in [1, 3] and ticket_state != "closed":
        assign_ticket_to_ai(ticket_id)
        logging.info(f"[TAKEOVER] Assigned to AI (owner_id=3)")

    # วิเคราะห์ intent จาก title + message
    title = get_ticket_title_by_id(ticket_id)
    combined = f"{title}\n\n{question}" if title else question

    # ถ้ามีการใช้ repair_flow ค้างไว้
    ongoing_repair = user_repair_state.get(user_id, {}).get("step", 0) > 0
    if ongoing_repair:
        intent = "repair"
    else:
        intent = detect_intent(combined)
    logging.info(f"[INTENT] = {intent}")

    # ดึงประวัติจาก DB เพื่อใส่ memory
    history = get_chat_history_from_db(user_id, limit=3)
    memory_context = ""
    for h in history:
        memory_context += f"User: {h['message']}\nAI: {h['response']}\n"

    # ตรวจสอบ RAG (ใช้เฉพาะบาง intent)
    if intent in ["product", "solution", "company", "sales", "contact"]:
        rag_context = get_context_from_mysql(question, intent=intent)
        full_context = f"""ประวัติการสนทนาเดิมของผู้ใช้ (context เท่านั้น):\n{memory_context}\n\nคำถามใหม่:\n{rag_context}"""
        answer = ask_local_llm(question, full_context, intent=intent, user_id=user_id, ticket_id=ticket_id)
        logging.info("[Hermes] Answered.")
        save_chat_to_db(user_id, question, answer)
        return {"answer": answer}

    # กรณีใบเสนอราคา
    elif intent == "quotation":
        pdf_link = ask_local_llm(question, intent=intent, user_id=user_id, ticket_id=ticket_id)
        logging.info("[Quotation] Generated.")
        save_chat_to_db(user_id, question, pdf_link)
        return {"answer": f"<a href='{pdf_link}' target='_blank'>📄 ดาวน์โหลดใบเสนอราคา</a>"}

    # กรณีแจ้งซ่อม หรือปัญหาอื่น
    else:
        answer = ask_local_llm(question, intent=intent, user_id=user_id, ticket_id=ticket_id)
        if answer:
            save_chat_to_db(user_id, question, answer)
            return {"answer": answer}
        else:
            return {"answer": ""}  # ไม่ตอบซ้ำ

@app.post("/zammad-webhook")
async def zammad_webhook(req: Request):
    data = await req.json()
    ticket_id = data.get("ticket_id")
    if ticket_id:
        asyncio.create_task(handle_ticket_async(ticket_id))  # ทำงานทันทีแบบ async
    return {"status": "processing"}