# main_api/utils.py

from langdetect import detect

def detect_language(text: str) -> str:
    try:
        return detect(text)
    except:
        return "unknown"

def assign_ticket_to_owner(ticket_id, db, owner_id=12):
    with db.cursor() as cursor:
        cursor.execute("UPDATE tickets SET owner_id = %s WHERE id = %s", (owner_id, ticket_id))
        db.commit()

def log_step(ticket_id: int, step: str):
    import os
    os.makedirs("logs", exist_ok=True)
    with open(f"logs/ticket_{ticket_id}.log", "a", encoding="utf-8") as f:
        f.write(f"[{step}]\n")

def should_assign_due_to_convo(ticket_id, db, threshold=6):
    from main_api.memory_mysql import get_message_count
    return get_message_count(ticket_id, db) >= threshold

def log_and_assign(ticket_id, db, owner_id=12, reason=""):
    log_step(ticket_id, f"assign_to_owner_id_{owner_id} due_to_{reason}")
    assign_ticket_to_owner(ticket_id, db, owner_id)

def log_event(category: str, message: str):
    print(f"[{category.upper()}] {message}")
