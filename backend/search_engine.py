"""
Handles semantic similarity search against the historical Tickets table.

Responsibilities:
- Load the embedding model once at startup
- Load every historical ticket's stored vector into an in-memory matrix
- Given a new ticket's text, find the top N most similar historical tickets
"""

import numpy as np
from sentence_transformers import SentenceTransformer, util

from database import SessionLocal, Ticket

MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.10      # intentionally loose for demo mode: surface weak but relevant matches
CATEGORY_BOOST = 1.15           # multiplier applied when category matches

# Module-level state, populated once by load_index() at FastAPI startup.
_model: SentenceTransformer|None = None
_ticket_ids: list = []
_ticket_meta: dict = {}         # ticket_id -> Ticket row, for returning full details
_vector_matrix: np.ndarray|None = None


def build_text(subject: str|None, description: str|None) -> str:
    """Builds the text that gets embedded, from a ticket's subject + description.

    IMPORTANT: this exact same logic is used in generate_embeddings.py to build
    the text for historical tickets. Both must match, or query vectors and
    stored vectors won't be comparable.
    """
    parts = [subject or "", description or ""]
    return " ".join(p for p in parts if p).strip()


def get_model() -> SentenceTransformer:
    """Returns the already-loaded model instance."""
    if _model is None:
        raise RuntimeError("Model not loaded — ensure load_index() has run at startup.")
    return _model


def create_embedding(subject: str, description: str | None = None) -> bytes:
    """Generate a stored vector using the same text construction as search."""
    text = build_text(subject, description)
    return get_model().encode(text).astype(np.float32).tobytes()


def load_index():
    """Loads the model and every historical ticket's vector into memory."""
    global _model, _ticket_ids, _ticket_meta, _vector_matrix

    if _model is None:
        print(f"Loading embedding model '{MODEL_NAME}'...")
        _model = SentenceTransformer(MODEL_NAME)

    print("Loading ticket vectors from database...")
    session = SessionLocal()
    try:
        tickets = session.query(Ticket).filter(Ticket.Embedding.isnot(None)).all()
    finally:
        session.close()

    if not tickets:
        print("WARNING: No tickets have embeddings yet. Run embedding generation first.")
        _ticket_ids, _ticket_meta, _vector_matrix = [], {}, np.zeros((0, 384), dtype=np.float32)
        return

    _ticket_ids = [t.ticket_id for t in tickets]
    _ticket_meta = {t.ticket_id: t for t in tickets}
    _vector_matrix = np.stack(
        [np.frombuffer(t.Embedding, dtype=np.float32) for t in tickets] # type: ignore
    )
    print(f"Loaded {len(_ticket_ids)} ticket vectors.")


def search_similar_tickets(subject: str, description: str |None= None,
                            category: str |None= None, top_n: int = 5):
    """Given a new ticket's details, returns the top N most similar
    historical tickets, each with its resolution notes and a similarity score.
    """
    if _model is None or _vector_matrix.shape[0] == 0: # type: ignore
        return []

    query_text = build_text(subject, description) # type: ignore
    query_vector = _model.encode(query_text)

    scores = util.cos_sim(query_vector, _vector_matrix)[0].numpy()  # type: ignore # shape: (N,)

    if category:
        for i, ticket_id in enumerate(_ticket_ids):
            if _ticket_meta[ticket_id].category == category:
                scores[i] *= CATEGORY_BOOST

    ranked_indices = np.argsort(scores)[::-1]  # descending order

    results = []
    for idx in ranked_indices:
        score = float(scores[idx])
        if score < SIMILARITY_THRESHOLD:
            break

        ticket = _ticket_meta[_ticket_ids[idx]]

        if not ticket.resolution_notes:
            continue

        results.append({
            "ticket_id": ticket.ticket_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category,
            "status": ticket.status,
            "resolution_notes": ticket.resolution_notes,
            "similarity_score": round(score, 4),
        })

        if len(results) == top_n:
            break

    return results