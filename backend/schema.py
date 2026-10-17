from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TicketNewCreateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None

    @field_validator("subject")
    @classmethod
    def subject_must_not_be_blank(cls, value: str) -> str:
        subject = value.strip()
        if not subject:
            raise ValueError("Subject must not be blank")
        return subject


class TicketNewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    subject: str
    description: Optional[str] = None


class TicketSearchRequest(BaseModel):
    subject: str
    description: Optional[str] = None
    category: Optional[str] = None


class SimilarTicketResult(BaseModel):
    ticket_id: str
    subject: str
    description: Optional[str] = None
    category: str
    status: str
    resolution_notes: str
    similarity_score: float


class ResolveTicketRequest(BaseModel):
    resolution_notes: str


class TicketDetailResponse(BaseModel):
    ticket_id: str
    category: str
    subject: str
    description: Optional[str] = None
    resolution_notes: Optional[str] = None
    tags: Optional[str] = None
    created_at: Optional[str] = None
    status: str