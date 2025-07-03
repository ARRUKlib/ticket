# main_api/tools/contact_tool.py

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

def get_contact_info() -> str:
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT name, phone, email FROM sales LIMIT 5;")
            rows = cursor.fetchall()

            if not rows:
                return "ไม่พบข้อมูลฝ่ายขายในระบบ"

            contact_list = "\n".join(
                f"- {r['name']} โทร: {r['phone']} อีเมล: {r['email']}" for r in rows
            )

            return f"ข้อมูลติดต่อฝ่ายขายของ WTC:\n{contact_list}"

    except Exception as e:
        return f"เกิดข้อผิดพลาดในการดึงข้อมูลฝ่ายขาย: {e}"
