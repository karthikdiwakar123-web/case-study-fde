import sys
from pathlib import Path

# Let this script import database.py from the backend folder,
# regardless of which directory it's actually run from.
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from database import SessionLocal, Ticket, TicketNew
from sentence_transformers import SentenceTransformer
import numpy as np

MODEL_NAME = "all-MiniLM-L6-v2"


def build_ticket_text(ticket: Ticket) -> str:
    """Combines the fields that matter for similarity into one string for Tickets."""
    parts = [ticket.subject or "", ticket.description or ""]
    return " ".join(p for p in parts if p).strip() # type: ignore


def build_ticket_new_text(ticket: TicketNew) -> str:
    """Combines the fields that matter for similarity into one string for TicketsNew."""
    parts = [ticket.subject or "", ticket.description or ""]
    return " ".join(p for p in parts if p).strip() # type: ignore


def process_tickets(model, session):
    tickets = session.query(Ticket).all()
    print(f"Found {len(tickets)} tickets in 'Tickets' to embed.")

    if not tickets:
        print("No tickets found in 'Tickets' table.")
        return

    texts = [build_ticket_text(t) for t in tickets]

    print("Encoding 'Tickets' texts...")
    vectors = model.encode(texts, show_progress_bar=True)

    print("Writing vectors back to 'Tickets' table...")
    for ticket, vector in zip(tickets, vectors):
        ticket.Embedding = vector.astype(np.float32).tobytes()
        ticket.EmbeddingModelVersion = MODEL_NAME # type: ignore

    session.commit()
    print(f"Done. {len(tickets)} tickets in 'Tickets' now have embeddings.")


def process_new_tickets(model, session):
    new_tickets = session.query(TicketNew).all()
    print(f"Found {len(new_tickets)} tickets in 'TicketsNew' to embed.")

    if not new_tickets:
        print("No tickets found in 'TicketsNew' table.")
        return

    texts = [build_ticket_new_text(t) for t in new_tickets]

    print("Encoding 'TicketsNew' texts...")
    vectors = model.encode(texts, show_progress_bar=True)

    print("Writing vectors back to 'TicketsNew' table...")
    for ticket, vector in zip(new_tickets, vectors):
        ticket.Embedding = vector.astype(np.float32).tobytes()
        ticket.EmbeddingModelVersion = MODEL_NAME # type: ignore

    session.commit()
    print(f"Done. {len(new_tickets)} tickets in 'TicketsNew' now have embeddings.")


def main():
    print(f"Loading model '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)

    session = SessionLocal()
    try:
        process_tickets(model, session)
        print("-" * 40)
        process_new_tickets(model, session)
    finally:
        session.close()
        print("Database session closed.")


if __name__ == "__main__":
    main()