import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_context_from_mysql(question: str, intent: str) -> str:
    connection = pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database="test",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    context = ""

    with connection:
        with connection.cursor() as cursor:
            if intent == "product":
                cursor.execute("SELECT name, description FROM products LIMIT 5")
            elif intent == "company":
                cursor.execute("SELECT * FROM company_info LIMIT 2")
            elif intent == "solution":
                cursor.execute("SELECT name, description FROM product_types LIMIT 42")
            elif intent == "sales" or intent == "contact":
                cursor.execute("SELECT name, email, phone, ext FROM sales LIMIT 15")
            else:
                return "[RAG] ยังไม่ได้รองรับ intent นี้"

            results = cursor.fetchall()
            for row in results:
                context += " ".join(str(v) for v in row.values()) + "\n"
    return context.strip()
