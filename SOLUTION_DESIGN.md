# Solution Design: Support Ticket Similarity Assistant

## Problem

Support agents need a quick way to find previously resolved tickets that may help
with a new customer issue. Similar issues are not always described with the same
keywords, so the system should compare the meaning of ticket text and show useful
past cases—including their resolution notes—while leaving the decision to the agent.

## Assumptions and scope

- Historical tickets in `Tickets` are the knowledge base. Only tickets with stored
  embeddings and resolution notes can be returned as useful matches.
- A ticket's subject and description contain enough information for a first version
  of similarity search. Category and tags are not included in the embedding text.
- The supplied synthetic seed data is representative enough to demonstrate the flow,
  but not enough to validate search quality for a real support organization.
- A locally hosted, pretrained sentence-transformer is an acceptable way to explore
  semantic search without sending ticket text to an external inference API.
- The prototype runs as one FastAPI process with its own in-memory search index. The
  expected demo-scale dataset fits in memory; production throughput and maximum
  historical-data size have not been measured.
- The similarity score is a ranking signal, not a probability or a guarantee that two
  tickets have the same cause or resolution. Agents review the examples themselves.

## Proposed approach and architecture

```text
                         Create / list new tickets
Angular frontend  --------------------------------------> FastAPI
      |                                                     |
      | Select a ticket                                     | SQLAlchemy
      +---------------- POST /api/tickets/similar --------> SQL Server LocalDB
                                                            |
                                                TicketsNew  |  Tickets
                                                open queue  |  resolved history
                                                            |
                                           search_engine.py |
                                     sentence embeddings + cosine similarity
                                                            |
      <--------------- ranked resolved tickets ------------+
      show subject, description, resolution, and score

Resolve a new ticket:
Angular -> POST /api/new-tickets/{ticket_id}/resolve -> move to Tickets
                                                    -> refresh in-memory index
```

The backend loads `all-MiniLM-L6-v2` and the stored historical ticket vectors when
FastAPI starts. The index keeps ticket IDs, ticket records, and a NumPy matrix of
embeddings in matching order. When the frontend requests matches, the backend builds
text from the new ticket's subject and description, encodes it with the same model,
and computes cosine similarity against the historical vectors.

The results are sorted by score. Candidates below the configured `0.10` threshold
are excluded; tickets without resolution notes are skipped; and up to five results
are returned. The deliberately low threshold is used for the demo scenario discussed
here—finding a resolved download/browser issue even when a new ticket describes the
problem with different wording. For example, the query about files not downloading in
a browser returned T-2145 (“Attachment download”) with a score of `0.3925`. This
threshold surfaces weaker candidates, so agents must assess whether each result is
actually useful. An optional exact-category match can multiply a score by `1.15`,
though the current new-ticket UI does not provide a category, so this boost is not
normally used in that flow.

The frontend presents the resolved examples as decision support. Creating a new
ticket stores its embedding; resolving it moves the ticket into historical `Tickets`
with its resolution notes and reuses its embedding because its subject and description
have not changed. The search index is then reloaded so that ticket is immediately
available for later searches.

## Trade-offs

### Semantic embeddings instead of keyword-only matching

The brief allows keyword matching and makes AI/ML optional. We chose embeddings
because they can identify related text with different wording, which is a central
part of the customer's problem. A pretrained local model avoids building a training
pipeline and avoids sending ticket text to a hosted model service. The trade-offs are
model startup/download cost, additional dependencies, and scores that require
calibration against real examples.

### Exact similarity search in memory

For this prototype, all historical vectors are loaded into a NumPy matrix and
compared directly. This keeps the retrieval path easy to understand and avoids
introducing a separate vector database. It is appropriate for the supplied dataset
and a demo, but memory use and comparison work grow with the number of historical
tickets. No latency or capacity target has yet been measured.

### Relational database for ticket records

SQL Server LocalDB stores ticket fields and embeddings together, keeping the
prototype's persistence model straightforward. It also makes this implementation
specific to a local Windows development setup. A deployed service would likely use a
shared database and a separate vector index or managed vector-search capability if
its measured scale justified one.

### Threshold, top-five limit, and category boost

The `0.10` threshold and five-result limit are demo heuristics rather than values
validated with agents. The intentionally permissive threshold can increase recall,
but it also makes weaker or false-positive candidates more likely. The optional
category multiplier can help when labels are reliable; it can also elevate a weaker
semantic match. Category is not currently carried through the new-ticket form and
resolution flow, so category-based ranking is not fully wired end to end.

### Agent remains in control

The system shows past tickets and their resolutions rather than automatically
answering the customer or closing a ticket. This reduces the risk of treating a
similarity score as certainty and lets the agent account for context the model may
miss.

## What I would do next

With more time and real ticket data, I would:

1. **Evaluate search quality with support agents.** Create a representative set of
   new-ticket queries and have agents judge whether the top results are useful. Track
   measures such as whether a useful resolved ticket appears in the top five, then
   tune the threshold and ranking based on those judgments.
2. **Measure performance and growth limits.** Benchmark model startup, request
   latency, and memory use at expected and projected ticket volumes before changing
   the retrieval architecture.
3. **Wire and validate metadata.** Add controlled categories end to end only if
   agents maintain consistent labels; evaluate whether category improves relevance
   rather than assuming that a boost helps.
4. **Harden embedding lifecycle.** Validate vector dimensions and model versions
   during index loading, and provide a clear re-embedding workflow when the model or
   text construction changes.
5. **Improve operational behavior.** Add automated tests around the API and ranking,
   structured logs and health/readiness checks, and deployment configuration suitable
   for a shared environment rather than LocalDB.
6. **Revisit retrieval if measurements require it.** If a full in-memory scan no
   longer meets the response-time or capacity target, evaluate a vector index or
   database-supported approximate-nearest-neighbor search, comparing its operational
   cost and retrieval quality with the current exact approach. A managed service such
   as Azure AI Search could host and search a growing vector index. This scale-up does
   not inherently require an LLM: the application still needs an embedding model to
   represent ticket text, while the search service retrieves similar vectors. An LLM
   could be added separately if there is a clear need to summarize past resolutions,
   refine queries, or produce a grounded draft for the agent; it would add cost and
   would need careful evaluation and safeguards.

## Summary

The implementation is a deliberately scoped, end-to-end prototype of agent-assisted
ticket retrieval. Its main design choice is to use local semantic embeddings to rank
historical resolved examples, while keeping the agent responsible for deciding
whether those examples apply. The current system demonstrates the intended workflow;
search quality, production capacity, and operational readiness remain to be validated
against the customer's real data and requirements.
