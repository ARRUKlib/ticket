# auth.py — FastAPI endpoints สำหรับ Register และ Login

import os
import mysql.connector
from uuid import uuid4
from datetime import datetime
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

load_dotenv()

router = APIRouter()

# 🔐 Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB")  
}

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(req: RegisterRequest):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    # ตรวจสอบ email ซ้ำ
    cursor.execute("SELECT * FROM users WHERE email = %s", (req.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email นี้มีผู้ใช้แล้ว")

    # สร้าง user_id + เข้ารหัส password
    user_id = f"u{uuid4().hex[:8]}"
    password_hash = pwd_context.hash(req.password)

    # บันทึกลงฐานข้อมูล
    cursor.execute("""
        INSERT INTO users (user_id, name, email, password_hash, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, req.name, req.email, password_hash, datetime.now()))
    conn.commit()
    conn.close()

    return {"message": "สมัครสมาชิกสำเร็จ", "user_id": user_id}

@router.post("/login")
def login(req: LoginRequest):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email = %s", (req.email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="ไม่พบผู้ใช้นี้")

    if not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="รหัสผ่านไม่ถูกต้อง")

    return {
        "message": "เข้าสู่ระบบสำเร็จ",
        "user_id": user["user_id"],
        "user_name": user["name"]
    }
