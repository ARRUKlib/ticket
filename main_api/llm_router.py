import os
import requests
from openai import OpenAI
from dotenv import load_dotenv
from main_api.tools.image_caption_agent import caption_image

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#กรณีข้อความธรรมดา → ส่งเข้า OpenAI
def ask_openai(message: str) -> str:
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "คุณคือ AI Support สำหรับลูกค้าองค์กรไทยของบริษัท WTC"},
                {"role": "user", "content": message}
            ],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("[OpenAI Error]", e)
        return ""

#ถ้าให้ LLM ขององค์กร (Hermes) ช่วยสรุป
def ask_hermes(prompt: str, context: str = "") -> str:
    try:
        res = requests.post("http://127.0.0.1:8011/generate", json={
            "question": prompt,
            "context": context
        }, timeout=60)
        return res.json()["answer"]
    except Exception as e:
        print("[Hermes ERROR]", e)
        return "ขออภัย ระบบ AI ไม่สามารถปะมวลผลได้ในขณะนี้"

#ใช้ OpenAI วิเคราะห์ก่อน แล้วให้ Local LLM สรุปให้อีกครั้ง
def ask_openai_then_local(question: str) -> str:
    openai_ans = ask_openai(question)
    if not openai_ans:
        return "ขออภัย ระบบยังไม่สามารถให้คำตอบได้ในขณะนี้"
    
    return ask_hermes("สรุปและตอบลูกค้าแบบมืออาชีพ โดยใช้ข้อมูลจาก OpenAI", context=openai_ans)

#ส่งเข้า Local LLM โดยตรง พร้อม context และ intent
def ask_local_llm(question: str, context: str = "", intent: str = "", user_id: str = "", ticket_id: int = None) -> str:
    try:
        res = requests.post("http://127.0.0.1:8011/generate", json={
            "question": question,
            "context": context,
            "intent": intent,
            "user_id": user_id,
            "ticket_id": ticket_id
        }, timeout=60)
        return res.json()["answer"]
    except Exception as e:
        print("[Hermes ERROR]", e)
        return "ขออภัย ระบบ AI ไม่สามารถประมวลผลได้ในขณะนี้"

#กรณีที่มีภาพแนบจาก Zammad ให้ BLIP วิเคราะห์ภาพก่อน
def process_image_with_caption_agent(image_path: str, user_message: str) -> str:
    try:
        caption_text = caption_image(image_path)
        print("[📷 BLIP Caption]", caption_text)

        # รวมกับข้อความผู้ใช้เพื่อให้ OpenAI วิเคราะห์ต่อ
        prompt = f"""
ภาพที่ได้รับ: {caption_text}

ข้อความจากผู้ใช้: "{user_message}"

โปรดช่วยอธิบายปัญหานี้อย่างสุภาพ และเสนอแนวทางให้เหมาะกับระบบแจ้งซ่อม:
"""

        response = ask_openai(prompt)  # หรือจะใช้ ask_local_llm ก็ได้
        return response
    except Exception as e:
        print("[BLIP Agent ERROR]", e)
        return "ขออภัย ระบบวิเคราะห์ภาพยังไม่สามารถประมวลผลได้ในขณะนี้"