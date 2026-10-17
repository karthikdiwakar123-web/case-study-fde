import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { TicketService } from './Ticket.service';
import { TicketDetail } from './Ticket.model';

@Component({
  selector: 'app-ticket-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ticket-detail-component.html',
  styleUrls: ['./ticket-detail-component.css'],
})
export class TicketDetailComponent implements OnInit {
  ticket: TicketDetail | null = null;
  isLoading = true;
  error: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private ticketService: TicketService
  ) {}

  ngOnInit(): void {
    const ticketId = this.route.snapshot.paramMap.get('ticketNo');
    if (!ticketId) {
      this.error = 'No ticket number provided.';
      this.isLoading = false;
      return;
    }

    this.ticketService.getTicketDetail(ticketId).subscribe({
      next: (ticket) => {
        this.ticket = ticket;
        this.isLoading = false;
      },
      error: (err) => {
        this.error =
          err.status === 404
            ? `Ticket ${ticketId} was not found.`
            : 'Could not load ticket details.';
        this.isLoading = false;
        console.error(err);
      },
    });
  }
}