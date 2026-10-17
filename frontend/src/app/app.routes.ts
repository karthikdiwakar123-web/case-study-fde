import { Routes } from '@angular/router';

export const routes: Routes = [
  { 
    path: '', 
    redirectTo: 'MyTickets', 
    pathMatch: 'full' 
  },
  { 
    path: 'MyTickets', 
    loadComponent: () => import('./ticket/ticket-new-component').then(m => m.TicketNewComponent)
  },
  {
    path: 'create-ticket',
    loadComponent: () => import('./ticket/ticket-create-component').then(m => m.TicketCreateComponent)
  },
  { 
    path: 'ticket/:ticketNo', // Dynamic route parameter
    loadComponent: () => import('./ticket/ticket-detail-component').then(m => m.TicketDetailComponent) 
  },
  { 
    path: '**', // Wildcard route for 404 pages
    loadComponent: () => import('./not-found/not-found.component').then(m => m.NotFoundComponent) 
  }
];
