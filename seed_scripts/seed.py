import sys
from pathlib import Path
import json
# Let this script import database.py from the backend folder,
# regardless of which directory it's actually run from.
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from database import init_db, SessionLocal, Ticket,TicketNew
from sqlalchemy import text
DATA_DIR = Path(__file__).parent.parent / "data"

TICKETS_JSON_PATH = DATA_DIR / "tickets.json"
NEW_TICKETS_JSON_PATH = DATA_DIR / "new_tickets_example.json"

def load_json(path: Path):
    if not path.exists():
        print(f"ERROR: JSON file not found at {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def truncate_tables(session):
    print("Truncating Tickets and TicketsNew tables...")
    # Note: Use DELETE if foreign key constraints or table ordering require it, 
    # otherwise TRUNCATE works if no constraints are active.
    try:
        session.execute(text("TRUNCATE TABLE Tickets"))
        session.execute(text("TRUNCATE TABLE TicketsNew"))
    except Exception:
        session.execute(text("DELETE FROM Tickets"))
        session.execute(text("DELETE FROM TicketsNew"))
    session.commit()


def insert_tickets(session):
    data = load_json(TICKETS_JSON_PATH)
    tickets_list = data.get("tickets", [])
    print(f"Inserting {len(tickets_list)} rows into Tickets...")
    
    tickets = [
        Ticket(
            ticket_id=t["ticket_id"],
            category=t["category"],
            subject=t["subject"],
            description=t.get("description", ""),
            resolution_notes=t.get("resolution_notes", ""),
            tags=", ".join(t.get("tags", [])),  # Flatten tags list to comma-separated string
            created_at=t.get("created_at", ""),
            status=t.get("status", ""),
            Embedding=None,
            EmbeddingModelVersion=None,
        )
        for t in tickets_list
    ]
    session.bulk_save_objects(tickets)
    session.commit()


def insert_new_tickets(session):
    data = load_json(NEW_TICKETS_JSON_PATH)
    new_tickets_list = data.get("new_tickets", [])
    print(f"Inserting {len(new_tickets_list)} rows into TicketsNew...")
    
    tickets_new = [
        TicketNew(
            ticket_id=t["ticket_id"],
            subject=t["subject"],
            description=t.get("description", ""),
            Embedding=None,
            EmbeddingModelVersion=None,
        )
        for t in new_tickets_list
    ]
    session.bulk_save_objects(tickets_new)
    session.commit()


def main():
    print("Initializing database (creating tables if they don't exist)...")
    init_db()

    session = SessionLocal()
    try:
        truncate_tables(session)
        insert_tickets(session)
        insert_new_tickets(session)
        
        t_count = session.query(Ticket).count()
        tn_count = session.query(TicketNew).count()
        print(f"Done. Tickets table has {t_count} rows, TicketsNew table has {tn_count} rows.")
    finally:
        session.close()


if __name__ == "__main__":
    main()