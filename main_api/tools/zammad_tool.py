import os
import requests
from dotenv import load_dotenv

load_dotenv()
ZAMMAD_URL = os.getenv("ZAMMAD_URL")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_TOKEN")

HEADERS = {
    "Authorization": f"Token {ZAMMAD_TOKEN}",
    "Content-Type": "application/json"
}

def assign_to_specific_owner(ticket_id: int, owner_id: int):
    try:
        requests.put(f"{ZAMMAD_URL}/tickets/{ticket_id}", headers=HEADERS, json={"owner_id": owner_id})
    except Exception as e:
        print("[Zammad Error] assign:", e)

def assign_ticket_to_ai(ticket_id: int, ai_owner_id: int = 3):
    assign_to_specific_owner(ticket_id, ai_owner_id)

def get_owner_id_by_ticket_id(ticket_id: int) -> int:
    try:
        res = requests.get(f"{ZAMMAD_URL}/tickets/{ticket_id}", headers=HEADERS)
        return res.json().get("owner_id", 1)
    except:
        return 1

def get_ticket_state_by_id(ticket_id: int) -> str:
    try:
        res = requests.get(f"{ZAMMAD_URL}/tickets/{ticket_id}", headers=HEADERS)
        return res.json().get("state", "new")
    except:
        return "new"

def get_ticket_title_by_id(ticket_id: int) -> str:
    try:
        res = requests.get(f"{ZAMMAD_URL}/tickets/{ticket_id}", headers=HEADERS)
        return res.json().get("title", "")
    except:
        return ""
