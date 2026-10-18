# Support Ticket Similarity Search

An AI-powered support tool that helps agents find the most similar historical tickets for a new incoming issue by comparing semantic meaning rather than exact wording. The project uses a local embedding model and cosine similarity to surface the closest resolved cases, along with their resolution notes.

Full-stack project: FastAPI + SQL Server LocalDB backend, Angular frontend.

---

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the project](#running-the-project)
- [API reference](#api-reference)
- [Frontend reference](#frontend-reference)
- [Data and seed workflow](#data-and-seed-workflow)
- [Known notes](#known-notes)
- [Search engine explanation](#search-engine-explanation)

---

## Overview

Support teams often get similar tickets repeatedly. The same issue may be described with different phrases, so simple keyword matching is unreliable.

This solution uses a local sentence embedding model (`all-MiniLM-L6-v2`) to convert each ticket into a vector. When a new ticket is selected, its vector is compared against the vectors of historical resolved tickets, and the closest matches are returned.

The current implementation differs from the older queue-based design in the README history. The active system uses:

- `TicketsNew` for new incoming tickets
- `Tickets` for historical resolved tickets
- `POST /api/tickets/similar` to find similar resolved tickets
- `POST /api/new-tickets/{ticket_id}/resolve` to archive a ticket into history

---

## Architecture

```text
Incoming ticket in TicketsNew
        |
        v
Angular frontend (localhost:4200)
        |
        v
FastAPI backend (http://127.0.0.1:8000)
        |
        +-- GET /api/new-tickets
        |
        +-- POST /api/tickets/similar
        |
        +-- POST /api/new-tickets/{ticket_id}/resolve
        |
        +-- GET /api/tickets/{ticket_id}
        |
        v
search_engine.py
  - loads all-MiniLM-L6-v2
  - embeds subject + description
  - compares against stored vectors in Tickets
  - returns top matches with similarity score and resolution notes

SQL Server LocalDB
  - Tickets (historical resolved tickets)
  - TicketsNew (new open/inbox tickets)
```

### Retrieval flow

1. A new ticket is loaded from `TicketsNew`.
2. The frontend sends `subject` and `description` to `/api/tickets/similar`.
3. The backend combines the fields into one text string and embeds it.
4. It compares the query vector against the stored vectors in the historical `Tickets` table.
5. The top matches are returned, ordered by cosine similarity.
6. When a ticket is resolved, it is copied from `TicketsNew` into `Tickets` and the in-memory index is refreshed.

### Category impact and current limitation

Historical `Tickets` rows have a `category`, and `search_engine.py` applies a
`1.15` score multiplier when a query category exactly matches a historical ticket's
category. This is a ranking boost applied after semantic similarity is calculated: it
does not make embedding generation or search more computationally efficient. A match
can move higher in the results, but the boost does not guarantee that the ticket is
actually more relevant.

Category boosting is not currently effective for tickets selected from `TicketsNew`:
that table has no category column, the create-ticket form does not collect a category,
and the frontend similarity request sends only the subject and description. Although
the similarity API accepts an optional category, the current UI does not supply it.

To use category boosting for newly created tickets, the feature would need to be wired
through the full flow:

1. Add a category column to `TicketsNew` and migrate the existing database. SQLAlchemy's
   `create_all()` creates missing tables but does not add columns to an existing table.
2. Collect a category when creating a ticket (preferably from a controlled list so the
   values are consistent) and include it in the create-ticket request and response.
3. Preserve that category when moving a ticket from `TicketsNew` into `Tickets` on
   resolution; the current resolve route assigns `"general"` to every archived ticket.
4. Send the new ticket's category with the similarity request so the existing exact-match
   boost can be applied.

This should improve ranking when categories are accurate and consistently assigned,
especially for issues with overlapping descriptions. If categories are missing,
inconsistent, or too broad, the boost may have little effect or may rank a less relevant
ticket above a better semantic match. The embedding itself would remain based on subject
and description; adding a category column and applying the current score boost would not
require changing the embedding model.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Angular standalone components |
| Backend | FastAPI |
| Database | SQL Server LocalDB |
| ORM | SQLAlchemy |
| DB driver | pyodbc |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector math | NumPy |
| Data seeding | Python + JSON |
| Dev runner | npm + concurrently |

---

## Project structure

```text
project-root/
├── backend/
│   ├── .env
│   ├── .env.example
│   ├── database.py
│   ├── main.py
│   ├── routers.py
│   ├── schema.py
│   ├── search_engine.py
│   ├── requirements.txt
│   └── .venv/
├── data/
│   ├── tickets.json
│   └── new_tickets_example.json
├── seed_scripts/
│   ├── seed.py
│   ├── generate_embeddings.py
│   └── package.json
├── frontend/
│   ├── src/
│   ├── angular.json
│   ├── package.json
│   └── node_modules/
├── README.md
├── package.json
├── case-study-brief.md
├── instructions.txt
└── README.backup.md
```

---

## Prerequisites

- The latest stable version of Visual Studio Code
- Python 3.14
- Node.js 24 and npm (required by Angular CLI)
- Angular CLI installed globally (`@angular/cli`)
- SQL Server LocalDB
- Microsoft ODBC Driver 17 for SQL Server (the app's configured driver name is
  `ODBC Driver 17 for SQL Server`)
- Internet access once the first time to download the embedding model

Install Angular CLI globally with:

```powershell
npm install --global @angular/cli
```

The global Angular CLI is used by the root `npm run dev:frontend` script. If you
run `npm start` from `frontend` instead, its project-local CLI is used after
`npm install`, so a global CLI is not necessary for that workflow.

---

## Setup on a new machine (order matters)

Use the following sequence on a fresh machine. The database and seed steps must be done before the app is started.

### 1. Install backend dependencies

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

The backend requirements include:

- fastapi
- pydantic
- sqlalchemy
- pyodbc
- python-dotenv
- numpy
- sentence-transformers
- uvicorn

Pip also installs the transitive dependencies required by these packages.

### 2. Create the LocalDB instance and database

If this is the first time on the machine, create the LocalDB instance and then create the database itself.

```powershell
sqllocaldb create "TicketSimilarityDB"
sqllocaldb start "TicketSimilarityDB"
```

Create the database once:

```powershell
sqlcmd -S "(localdb)\TicketSimilarityDB" -Q "CREATE DATABASE TicketSimilarity;"
```

If you prefer the VS Code SQL Server extension, you can also run the equivalent SQL command:

```sql
CREATE DATABASE TicketSimilarity;
```

### 3. Configure backend environment variables

Create or update `backend/.env` from `backend/.env.example`:

```env
DB_DRIVER={ODBC Driver 17 for SQL Server}
DB_SERVER=(localdb)\TicketSimilarityDB
DB_NAME=TicketSimilarity
DB_TRUSTED_CONNECTION=yes
```

The app connects to SQL Server LocalDB using SQLAlchemy + pyodbc.

### 4. Install frontend dependencies

```powershell
cd frontend
npm install
```

### 5. Install root dependencies for the dev runner

```powershell
cd ..
npm install
```

### 6. Seed the database before starting the app

From the project root, run:

```powershell
npm run seed
```

This step initializes the schema and fills the `Tickets` and `TicketsNew` tables with the bundled JSON seed data. Run it once when setting up a new machine, or again when you want to reset the database to the starter dataset.

The database and tables are not created manually by the app; the database itself must exist first, and `npm run seed` will create the tables automatically via `Base.metadata.create_all()`.

### 7. Generate embeddings before using similarity search

```powershell
npm run embed
```

This must run after `npm run seed`. It creates the vector embeddings used by `search_engine.py`. Without embeddings, the app can start but similarity search will return no matches.

---

## Running the project

After the database is seeded and embeddings are built, start the stack from the project root:

```powershell
npm run dev
```

This starts:

- backend: `http://127.0.0.1:8000`
- frontend: `http://localhost:4200`

The development command does not open a browser automatically. Wait until the
frontend server reports that it is ready in the terminal, then open the URL manually.
Stop any separately started backend or frontend first; only one process can use each
development port.

You can also run them separately:

```powershell
npm run dev:backend
npm run dev:frontend
```

Open `http://localhost:4200` to use the app.

Swagger UI is available at:

`http://127.0.0.1:8000/docs`

---

## API reference

Base URL:

`http://127.0.0.1:8000`

### GET `/api`

Returns a welcome message.

Example response:

```json
{ "message": "Welcome to the Support Ticket AI Tool" }
```

### GET `/api/new-tickets`

Returns all rows from the `TicketsNew` table.

Response example:

```json
[
  {
    "ticket_id": "T-2001",
    "subject": "Password reset loop",
    "description": "Customer keeps being redirected after reset."
  }
]
```

### POST `/api/new-tickets`

Creates a new ticket in `TicketsNew`. The backend generates the ticket ID and
embedding; clients provide only the subject and optional description. The embedding
model must be available to the running backend.
Ticket IDs use `NT-<number>`, starting at the current `TicketsNew` row count plus one;
if that ID is already occupied, the backend checks the following numbers until it finds
an unused ID.

Request body:

```json
{
  "subject": "Printer keeps disconnecting from WiFi",
  "description": "The office printer loses its network connection several times a day."
}
```

The endpoint returns the created ticket, including its generated `ticket_id`, with
HTTP `201 Created`. No database schema change is required.

### POST `/api/tickets/similar`

Searches historical resolved tickets for the closest matches. Each result includes
the matched ticket description along with its resolution details.

Request body:

```json
{
  "subject": "Printer not connecting to WiFi",
  "description": "The printer keeps dropping off the network after login.",
  "category": "networking"
}
```

Response example:

```json
[
  {
    "ticket_id": "T-1204",
    "subject": "Printer not connecting to WiFi",
    "description": "The office printer loses its network connection several times a day.",
    "category": "networking",
    "status": "resolved",
    "resolution_notes": "Reset the printer network adapter and rejoined it to the network.",
    "similarity_score": 0.91
  }
]
```

### POST `/api/new-tickets/{ticket_id}/resolve`

Archives a ticket from `TicketsNew` into `Tickets`, adds the resolution notes, and refreshes the in-memory search index.

Request body:

```json
{
  "resolution_notes": "Reset network adapter and re-added with static IP."
}
```

Response example:

```json
{
  "message": "Ticket T-2001 resolved and moved to historical knowledge base."
}
```

### GET `/api/tickets/{ticket_id}`

Returns the full historical ticket detail for a previously resolved ticket.

---

## Frontend reference

### Routes (`frontend/src/app/app.routes.ts`)

```ts
export const routes: Routes = [
  { path: '', redirectTo: 'MyTickets', pathMatch: 'full' },
  {
    path: 'MyTickets',
    loadComponent: () => import('./ticket/ticket-new-component').then(m => m.TicketNewComponent)
  },
  {
    path: 'create-ticket',
    loadComponent: () => import('./ticket/ticket-create-component').then(m => m.TicketCreateComponent)
  },
  {
    path: 'ticket/:ticketNo',
    loadComponent: () => import('./ticket/ticket-detail-component').then(m => m.TicketDetailComponent)
  },
  {
    path: '**',
    loadComponent: () => import('./not-found/not-found.component').then(m => m.NotFoundComponent)
  }
];
```

### `TicketNewComponent`

- Loads the current list of new tickets from `/api/new-tickets`
- Provides a link to the create-ticket page
- Displays a table of ticket IDs and subjects
- Filters by ticket ID, subject, or description locally in the browser without
  additional backend requests
- Always sorts ticket IDs in descending numeric-aware order, keeping the newest
  sequentially numbered ticket first
- Displays 10 matching tickets per page
- Selects a ticket to trigger similarity search
- Renders a list of similar resolved tickets with their score and resolution notes
- Opens matching ticket details in a new tab using `/ticket/:ticketNo`

### `TicketCreateComponent`

- Is available at `/create-ticket`, linked from the new-ticket queue
- Collects the `subject` and optional `description` fields used by `TicketsNew`
- Submits to `POST /api/new-tickets`; the backend generates the ticket ID and embedding

### `TicketDetailComponent`

- Reads the route param `ticketNo`
- Calls `/api/tickets/{ticket_id}`
- Displays the ticket subject, description, category, status, and notes

### `TicketService`

The Angular service centralizes API calls to the backend:

- `getNewTickets()`
- `createNewTicket(ticket)`
- `getSimilarTickets(ticket)`
- `getTicketDetail(ticketId)`

`API_BASE` is currently hardcoded to:

`http://127.0.0.1:8000/api`

---

## Data and seed workflow

### Seed files

The project currently seeds data from JSON files instead of Excel files:

- `data/tickets.json`
- `data/new_tickets_example.json`

These are loaded by `seed_scripts/seed.py`.

### Seed and embedding commands

```powershell
npm run seed
npm run embed
```

Run `npm run seed` only after the LocalDB connection is configured and before starting the app for the first time (or before resetting the dataset). It initializes the database schema, truncates the tables, and loads the starter data.

Then run `npm run embed` immediately after `npm run seed`. This creates the vectors that the similarity search reads during startup. If you skip this step, the backend can still run but the search results will be empty.

`npm run embed`:

- loads the `all-MiniLM-L6-v2` model
- computes embeddings for all rows in `Tickets`
- computes embeddings for all rows in `TicketsNew`
- writes binary vectors back into the database as `Embedding`

---

## Database model

### `Tickets`

Historical resolved tickets.

Columns include:

- `ticket_id`
- `category`
- `subject`
- `description`
- `resolution_notes`
- `tags`
- `created_at`
- `status`
- `Embedding`
- `EmbeddingModelVersion`

### `TicketsNew`

Active or incoming tickets waiting for review.

Columns include:

- `ticket_id`
- `subject`
- `description`
- `Embedding`
- `EmbeddingModelVersion`

---

## Known notes

- This is a local prototype and not a production multi-tenant system.
- The app depends on a valid SQL Server LocalDB connection configured in `backend/.env`.
- Embeddings are loaded into memory in `search_engine.load_index()` at startup.
- Tickets without an embedding are skipped by similarity search.
- Category boosting is currently available in the search engine, but new-ticket category
  collection and propagation are not implemented; see [Category impact and current limitation](#category-impact-and-current-limitation).
- The older queue design from the original README is not the active implementation in the current codebase.

## Search engine explanation

For a beginner-friendly, detailed walkthrough of embeddings, semantic similarity,
ranking, thresholds, category boosting, and the search engine's limitations, see
[README_search_engine.md](./README_search_engine.md).

---

## Quick summary of the current system

The codebase currently follows this design:

- `TicketsNew` contains incoming tickets
- `Tickets` contains historical resolved tickets
- semantic similarity is used to find the most relevant past fixes
- Angular shows the new ticket queue and similar matches
- resolved tickets are archived into history and immediately searchable

This README reflects the current implementation in the repository.
