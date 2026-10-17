import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { TicketNew, NewTicketInput, SimilarTicketResult, TicketDetail } from './Ticket.model';

const API_BASE = 'http://127.0.0.1:8000/api';

@Injectable({
  providedIn: 'root',
})
export class TicketService {
  constructor(private http: HttpClient) {}

  /** New tickets list. */
  getNewTickets(): Observable<TicketNew[]> {
    return this.http.get<TicketNew[]>(`${API_BASE}/new-tickets`);
  }

  /** Creates a new ticket and stores its generated embedding. */
  createNewTicket(ticket: NewTicketInput): Observable<TicketNew> {
    return this.http.post<TicketNew>(`${API_BASE}/new-tickets`, ticket);
  }

  /** Semantic search: given a new ticket's details, find the top 5 similar
   * historical tickets. */
  getSimilarTickets(ticket: TicketNew): Observable<SimilarTicketResult[]> {
    return this.http.post<SimilarTicketResult[]>(`${API_BASE}/tickets/similar`, {
      subject: ticket.subject,
      description: ticket.description,
    });
  }

  /** Full details of a single historical (resolved) ticket, for the
   * detail page opened in a new tab. */
  getTicketDetail(ticketId: string): Observable<TicketDetail> {
    return this.http.get<TicketDetail>(
      `${API_BASE}/tickets/${encodeURIComponent(ticketId)}`
    );
  }
}