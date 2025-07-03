
import mysql.connector
import psycopg2
import os
from dotenv import load_dotenv
from main_api.llm_router import ask_hermes, ask_openai
from main_api.tools.zammad_tool import assign_to_specific_owner

load_dotenv()
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB")
}

def check_latest_sender(ticket_id: int) -> str:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT sender FROM chats WHERE ticket_id = %s ORDER BY id DESC LIMIT 1", (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def should_escalate(ticket_id: int) -> bool:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT sender FROM chats WHERE ticket_id = %s", (ticket_id,))
    rows = cursor.fetchall()
    conn.close()
    user_msgs = sum(1 for r in rows if r[0] == "user")
    ai_msgs = sum(1 for r in rows if r[0] == "ai")
    return user_msgs >= 3 and ai_msgs >= 3

def classify_issue(ticket_id: int) -> str:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT sender, message FROM chats WHERE ticket_id = %s ORDER BY id ASC", (ticket_id,))
    rows = cursor.fetchall()
    conn.close()
    conv = "\n".join([f"{'User' if s == 'user' else 'AI'}: {m}" for s, m in rows])
    prompt = f"บทสนทนาเกี่ยวกับการแจ้งปัญหา:\n{conv}\nจากข้อมูลข้างต้น ปัญหานี้จัดอยู่ในหมวดใด เช่น mac, network, signage"
    return ask_openai(prompt).strip().lower()

def find_owner_by_skill(category: str) -> int:
    try:
        conn = psycopg2.connect(
            host=os.getenv("ZAMMAD_PG_HOST"),
            database="zammad",
            user="zammad",
            password="rTRxnwN7Wl"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM skill WHERE LOWER(skill) = %s LIMIT 1", (category,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 5
    except:
        return 5

def get_solution_from_db(question: str) -> str:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT problem_description FROM problem_solutions WHERE MATCH(problem_title, problem_description) AGAINST (%s IN NATURAL LANGUAGE MODE) LIMIT 1", (question,))
    row = cursor.fetchone()
    conn.close()
    return row["problem_description"] if row else ""

def get_solution_or_fallback(user_id: str, message: str, ticket_id: int = None) -> str:
    if ticket_id and check_latest_sender(ticket_id) != "user":
        return ""
    db_ans = get_solution_from_db(message)
    if db_ans:
        return ask_hermes(f"ตอบลูกค้าแบบมืออาชีพด้วยข้อความนี้:\n{db_ans}")
    openai_ans = ask_openai(message)
    if openai_ans:
        return ask_hermes(f"สรุปและตอบลูกค้าแบบมืออาชีพ ด้วยข้อมูลนี้:\n{openai_ans}")
    if ticket_id and should_escalate(ticket_id):
        category = classify_issue(ticket_id)
        owner = find_owner_by_skill(category)
        assign_to_specific_owner(ticket_id, owner)
        return f"ระบบได้ส่งต่อปัญหาไปยังผู้เชี่ยวชาญด้าน {category} เรียบร้อยแล้วค่ะ"
    return "ขออภัย ระบบยังไม่สามารถตอบคำถามนี้ได้ในขณะนี้"
