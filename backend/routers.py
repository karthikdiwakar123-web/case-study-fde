from typing import List

from fastapi import APIRouter, HTTPException, status
from database import SessionLocal, Ticket, TicketNew
from schema import (
    TicketNewCreateRequest,
    TicketNewResponse,
    ResolveTicketRequest,
    SimilarTicketResult,
    TicketDetailResponse,
    TicketSearchRequest,
)
import search_engine

# Create the router instance
router = APIRouter(
    prefix="/api",      # Automatically prepends "/api" to all routes in this file
    tags=["tickets"],        # Groups these routes together in the Swagger /docs
)

@router.get("/new-tickets", response_model=List[TicketNewResponse])
def list_new_tickets():
    session = SessionLocal()
    try:
        return session.query(TicketNew).all()
    finally:
        session.close()

@router.post(
    "/new-tickets",
    response_model=TicketNewResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_ticket(request: TicketNewCreateRequest):
    embedding = search_engine.create_embedding(request.subject, request.description)
    session = SessionLocal()
    try:
        ticket_number = session.query(TicketNew).count() + 1
        ticket_id = f"NT-{ticket_number}"
        while session.query(TicketNew.ticket_id).filter(
            TicketNew.ticket_id == ticket_id
        ).first():
            ticket_number += 1
            ticket_id = f"NT-{ticket_number}"

        new_ticket = TicketNew(
            ticket_id=ticket_id,
            subject=request.subject,
            description=request.description,
            Embedding=embedding,
            EmbeddingModelVersion=search_engine.MODEL_NAME,
        )
        session.add(new_ticket)
        session.commit()
        session.refresh(new_ticket)
        return new_ticket
    finally:
        session.close()

@router.post("/tickets/similar", response_model=List[SimilarTicketResult])
def get_similar_tickets(request: TicketSearchRequest):
    results = search_engine.search_similar_tickets(
        subject=request.subject,
        description=request.description,
        category=request.category,
    )
    return results

@router.post("/new-tickets/{ticket_id}/resolve")
def resolve_new_ticket(ticket_id: str, request: ResolveTicketRequest):
    session = SessionLocal()
    try:
        new_ticket = session.query(TicketNew).filter(TicketNew.ticket_id == ticket_id).first()
        if not new_ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found in new tickets")

        # Archive into the historical Tickets table, now with resolution notes
        resolved = Ticket(
            ticket_id=new_ticket.ticket_id,
            category="general",
            subject=new_ticket.subject,
            description=new_ticket.description,
            resolution_notes=request.resolution_notes,
            tags="",
            created_at="",
            status="resolved",
            Embedding=new_ticket.Embedding,              # reuse — text hasn't changed
            EmbeddingModelVersion=new_ticket.EmbeddingModelVersion,
        )
        session.add(resolved)

        # Remove from new tickets after archive succeeds
        session.delete(new_ticket)
        session.commit()

        # Refresh in-memory search index so it's searchable immediately
        search_engine.load_index()

        return {"message": f"Ticket {ticket_id} resolved and moved to historical knowledge base."}
    finally:
        session.close()

@router.get("/tickets/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_detail(ticket_id: str):
    """Returns full details of a single historical (resolved) ticket."""
    session = SessionLocal()
    try:
        ticket = session.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
        return ticket
    finally:
        session.close()