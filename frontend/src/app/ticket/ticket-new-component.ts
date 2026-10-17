import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TicketService } from './Ticket.service';
import { TicketNew, SimilarTicketResult } from './Ticket.model';

@Component({
  selector: 'app-ticket-new',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './ticket-new-component.html',
  styleUrls: ['./ticket-new-component.css'],
})
export class TicketNewComponent implements OnInit {
  @ViewChild('similarSection') similarSection!: ElementRef<HTMLElement>;

  queueTickets: TicketNew[] = [];
  readonly pageSize = 10;
  currentPage = 1;
  filterText = '';
  selectedTicket: TicketNew | null = null;
  similarTickets: SimilarTicketResult[] = [];

  isLoadingQueue = false;
  isLoadingSimilar = false;
  queueError: string | null = null;
  similarError: string | null = null;
  private similarSearchId = 0;

  get totalPages(): number {
    return Math.ceil(this.filteredSortedQueueTickets.length / this.pageSize);
  }

  get filteredSortedQueueTickets(): TicketNew[] {
    const filter = this.filterText.trim().toLocaleLowerCase();
    const filteredTickets = this.queueTickets.filter((ticket) =>
      !filter ||
      ticket.ticket_id.toLocaleLowerCase().includes(filter) ||
      ticket.subject.toLocaleLowerCase().includes(filter) ||
      (ticket.description ?? '').toLocaleLowerCase().includes(filter)
    );
    const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

    return filteredTickets.sort((left, right) =>
      collator.compare(right.ticket_id, left.ticket_id)
    );
  }

  get pagedQueueTickets(): TicketNew[] {
    const startIndex = (this.currentPage - 1) * this.pageSize;
    return this.filteredSortedQueueTickets.slice(startIndex, startIndex + this.pageSize);
  }

  get firstVisibleTicket(): number {
    return this.filteredSortedQueueTickets.length === 0
      ? 0
      : (this.currentPage - 1) * this.pageSize + 1;
  }

  get lastVisibleTicket(): number {
    return Math.min(this.currentPage * this.pageSize, this.filteredSortedQueueTickets.length);
  }

  get totalFilteredTickets(): number {
    return this.filteredSortedQueueTickets.length;
  }

  constructor(
    private ticketService: TicketService,
    private changeDetectorRef: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadQueue();
  }

  loadQueue(): void {
    this.isLoadingQueue = true;
    this.queueError = null;

    this.ticketService.getNewTickets().subscribe({
      next: (tickets) => {
        this.queueTickets = tickets;
        this.currentPage = 1;
        this.isLoadingQueue = false;
      },
      error: (err) => {
        this.queueError = 'Could not load new tickets queue. Is the API running?';
        this.isLoadingQueue = false;
        console.error(err);
      },
    });
  }

  previousPage(): void {
    if (this.currentPage > 1) {
      this.currentPage--;
    }
  }

  nextPage(): void {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
    }
  }

  onFilterChange(): void {
    this.currentPage = 1;
  }

  selectTicket(ticket: TicketNew): void {
    const searchId = ++this.similarSearchId;
    this.selectedTicket = ticket;
    this.similarTickets = [];
    this.similarError = null;
    this.isLoadingSimilar = true;

    this.changeDetectorRef.detectChanges();
    this.similarSection.nativeElement.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });

    this.ticketService.getSimilarTickets(ticket).subscribe({
      next: (results) => {
        if (searchId !== this.similarSearchId) {
          return;
        }
        this.similarTickets = results;
        this.isLoadingSimilar = false;
      },
      error: (err) => {
        if (searchId === this.similarSearchId) {
          this.similarError = 'Could not fetch similar tickets.';
          this.isLoadingSimilar = false;
          console.error(err);
        }
      },
    });
  }

  formatScore(score: number): string {
    return `${Math.round(score * 100)}%`;
  }
}