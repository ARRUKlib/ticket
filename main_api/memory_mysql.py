import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB")
}

def save_message(ticket_id: int, user_id: str, role: str, content: str):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chat_memory (ticket_id, user_id, role, content)
            VALUES (%s, %s, %s, %s)
        """, (ticket_id, user_id, role, content))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[Save Memory Error]", e)

def load_memory(ticket_id: int, limit: int = 5) -> str:
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT role, content FROM chat_memory
            WHERE ticket_id = %s ORDER BY created_at DESC LIMIT %s
        """, (ticket_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return "\n".join([f"{r['role']}: {r['content']}" for r in reversed(rows)])
    except Exception as e:
        print("[Load Memory Error]", e)
        return ""

def save_chat_to_chats_table(user_id: str, message: str, response: str):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = """
        INSERT INTO chats (user_id, prompt_id, message, response, timestamp)
        VALUES (%s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (user_id, 3, message, response))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[Save Chat Error]", e)

def get_chat_history_from_db(user_id: str) -> list[str]:
    # ใส่ logic ตามที่คุณต้องการ เช่น ดึงข้อมูลจาก MySQL
    return ["สวัสดีครับ", "คุณต้องการแจ้งซ่อมหรือไม่?"]

def save_chat_to_db(user_id: str, message: str, response: str):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = """
        INSERT INTO chats (user_id, message, response, created_at)
        VALUES (%s, %s, %s, NOW())
        """
        cursor.execute(query, (user_id, message, response))
        conn.commit()
        conn.close()
    except Exception as e:
        print("[DB Error] ❌", e)