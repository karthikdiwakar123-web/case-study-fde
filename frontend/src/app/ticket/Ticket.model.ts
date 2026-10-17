// Mirrors backend/schema.py — keep these in sync when the API changes.

export interface TicketNew {
  ticket_id: string;
  subject: string;
  description: string | null;
}

export interface NewTicketInput {
  subject: string;
  description: string | null;
}

export interface SimilarTicketResult {
  ticket_id: string;
  subject: string;
  description: string | null;
  category: string;
  status: string;
  resolution_notes: string;
  similarity_score: number;
}

export interface TicketDetail {
  ticket_id: string;
  category: string;
  subject: string;
  description: string | null;
  resolution_notes: string | null;
  tags: string | null;
  created_at: string | null;
  status: string;
}