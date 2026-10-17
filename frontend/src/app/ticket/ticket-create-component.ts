import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TicketService } from './Ticket.service';
import { TicketNew } from './Ticket.model';

@Component({
  selector: 'app-ticket-create',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './ticket-create-component.html',
  styleUrls: ['./ticket-create-component.css'],
})
export class TicketCreateComponent {
  subject = '';
  description = '';
  isSubmitting = false;
  error: string | null = null;
  createdTicket: TicketNew | null = null;

  constructor(private ticketService: TicketService) {}

  submitTicket(): void {
    const subject = this.subject.trim();
    if (this.isSubmitting || !subject) {
      this.error = 'Enter a subject before submitting.';
      return;
    }

    this.isSubmitting = true;
    this.error = null;
    this.createdTicket = null;

    this.ticketService.createNewTicket({
      subject,
      description: this.description.trim() || null,
    }).subscribe({
      next: (ticket) => {
        this.createdTicket = ticket;
        this.subject = '';
        this.description = '';
        this.isSubmitting = false;
      },
      error: (err) => {
        this.error = 'Could not create the ticket. Please try again.';
        this.isSubmitting = false;
        console.error(err);
      },
    });
  }
}
