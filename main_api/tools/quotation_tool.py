from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel
import mysql.connector
from jinja2 import Template
import os
from fpdf import FPDF
from datetime import datetime
import logging
from dotenv import load_dotenv

# โหลด config จาก .env
load_dotenv()

class QuotationInput(BaseModel):
    product_name: str
    quantity: int

class QuotationTool(BaseTool):
    name: str = "Quotation Tool"
    description: str = "ใช้สำหรับสร้างใบเสนอราคา"
    args_schema: Type[BaseModel] = QuotationInput

    def _run(self, product_name: str, quantity: int):
        # 1. เชื่อมต่อ MySQL
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DB")
        )
        cursor = conn.cursor(dictionary=True)

        # 2. ค้นหาสินค้าจากชื่อ
        cursor.execute("SELECT name, price FROM products WHERE name LIKE %s LIMIT 1", (f"%{product_name}%",))
        product = cursor.fetchone()

        if not product:
            return f"ไม่พบสินค้าที่ชื่อ {product_name}"

        # 3. สร้าง PDF ใบเสนอราคา
        pdf_link = create_quotation_pdf(
            product_name=product["name"],
            quantity=quantity,
            unit_price=product["price"]
        )
        return f"สร้างใบเสนอราคาเรียบร้อยแล้ว: <a href='{pdf_link}' target='_blank'>ดาวน์โหลด PDF</a>"

    def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async not supported")


def create_quotation_pdf(product_name: str, quantity: int, unit_price: float, output_path: str = "main_api/frontend/quotation.pdf") -> str:
    total = unit_price * quantity

    # 1. เตรียม PDF
    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join("main_api", "fonts", "THSarabun.ttf")
    pdf.add_font("THSarabun", "", font_path, uni=True)
    pdf.set_font("THSarabun", size=16)

    # 2. เพิ่มเนื้อหา
    lines = [
        "ใบเสนอราคา",
        "========================",
        f"สินค้า: {product_name}",
        f"จำนวน: {quantity}",
        f"ราคาต่อหน่วย: {unit_price:.2f} บาท",
        f"ราคารวม: {total:.2f} บาท",
        "",
        f"วันที่ออกใบเสนอราคา: {datetime.now().strftime('%d/%m/%Y')}"
    ]
    for line in lines:
        pdf.cell(0, 10, line, ln=True)

    # 3. บันทึก PDF
    pdf.output(output_path)

    # 4. คืนลิงก์สำหรับดาวน์โหลด
    return "/static/quotation.pdf"

def create_quotation(question: str) -> str:
    """
    ตัวช่วยแปลงข้อความคำถามจากผู้ใช้ เช่น "ขอใบเสนอราคา Cisco Switch จำนวน 5 ตัว"
    แล้วพยายามแยก product_name กับ quantity เพื่อนำไปสร้าง PDF
    """
    import re

    # ดึงชื่อสินค้าและจำนวนโดยใช้ regex แบบง่าย (เช่น "Switch จำนวน 5 ตัว")
    product_match = re.search(r"(?:เสนอราคา|ใบเสนอราคา)?\s*([\w\s]+?)\s*(?:จำนวน)?\s*(\d+)", question)
    if not product_match:
        return "กรุณาระบุชื่อสินค้าและจำนวน เช่น 'ใบเสนอราคา Switch จำนวน 5 ตัว'"

    product_name = product_match.group(1).strip()
    quantity = int(product_match.group(2))

    tool = QuotationTool()
    return tool._run(product_name=product_name, quantity=quantity)
