# Understanding the Ticket Search Engine

This document explains `backend/search_engine.py` for readers who have not worked
with artificial intelligence (AI), machine learning (ML), or semantic search before.
It describes what the code currently does, how a search request travels through the
system, and the terms used along the way.

## In plain language

The search engine compares the *meaning* of a new ticket with the meaning of past
tickets. It does not need the tickets to use the same words. For example, these
descriptions use different wording but may describe a similar problem:

- New ticket: “The office printer keeps losing its wireless connection.”
- Historical ticket: “Printer goes offline from WiFi several times each day.”

The search engine turns each ticket's subject and description into a list of numbers.
It compares the new list with lists saved for historical tickets, ranks the historical
tickets by similarity, and returns up to five matches that have resolution notes.

This is an inference/search feature. The application uses a model that was trained
beforehand; it does not train or fine-tune a model on this project's ticket data.

## The overall flow

```text
Historical tickets in the Tickets table
        |
        | npm run embed computes and stores their vectors
        v
Database Embedding blobs
        |
        | backend starts; load_index() reads them
        v
In-memory vector matrix + ticket details

Agent selects a new ticket
        |
        | POST /api/tickets/similar sends subject and description
        v
Model embeds the selected ticket's text
        |
        | cosine similarity compares it to the matrix
        v
Scores are optionally category-boosted, thresholded, and ranked
        |
        v
Up to five historical matches, including descriptions and solutions
```

## Step-by-step explanation

### 1. Model and search settings

`MODEL_NAME` is `all-MiniLM-L6-v2`, a pretrained sentence-transformer model. It is
loaded into the Python process when `load_index()` runs. The model can encode text into
a 384-number vector.

The module also defines two ranking settings:

- `SIMILARITY_THRESHOLD = 0.45`: matches with a score below this are not returned.
- `CATEGORY_BOOST = 1.15`: a matching category multiplies a ticket's score by 1.15.

The category multiplier changes ranking; it does not make the search faster. The
current new-ticket table and UI do not provide a category for selected new tickets, so
the frontend's normal similarity-search request does not use this boost. See the
category discussion below.

### 2. Build consistent text

`build_text(subject, description)` joins the subject and description with a space and
trims whitespace. If either value is missing, it is treated as an empty string.

For example:

```text
subject:     Printer not connecting to WiFi
description: The printer disconnects from the office network every afternoon.

combined:    Printer not connecting to WiFi The printer disconnects from the office network every afternoon.
```

Using the same text-building rule for stored ticket vectors and search queries is
important: it ensures that the model sees the same fields in the same way. The
embedding generator in `seed_scripts/generate_embeddings.py` follows this rule for
both `Tickets` and `TicketsNew`.

### 3. Create embeddings

An **embedding** is a numeric representation of text. In this project the model
produces a vector with 384 values. Those values encode learned language patterns and
relationships; they are not a word count or a human-readable explanation.

For historical tickets, `npm run embed` runs
`seed_scripts/generate_embeddings.py`. It:

1. Loads the same `all-MiniLM-L6-v2` model.
2. Combines each ticket's subject and description.
3. Encodes the combined text as a vector.
4. Converts the vector to 32-bit floating-point numbers and stores its bytes in the
   database `Embedding` column.
5. Stores the model name in `EmbeddingModelVersion`.

New tickets created through the application are embedded by
`search_engine.create_embedding()` when they are submitted. Their vectors are stored
with the ticket in `TicketsNew`. They are not search candidates while they remain new:
the search index is built from historical rows in `Tickets`.

### 4. Load historical vectors at backend startup

`load_index()` loads the model if it has not already been loaded in the current Python
process. It then queries the `Tickets` table for rows with a non-null `Embedding`.

It builds three pieces of in-memory state:

- `_ticket_ids`: the historical ticket IDs in vector order.
- `_ticket_meta`: a lookup from ticket ID to the ticket row, used to return the
  subject, description, category, status, and resolution.
- `_vector_matrix`: a NumPy matrix containing all the stored ticket vectors, with one
  ticket vector per row.

The matrix lets a single query be compared with all loaded tickets in one vectorized
calculation. This avoids fetching the historical ticket rows from the database for
every similarity search.

If there are no historical rows with embeddings, the search index is empty and the
search function returns no matches. Seed the database and generate embeddings before
expecting results.

The index is a snapshot held in process memory. It is initially populated at backend
startup. When the resolve endpoint moves a ticket into `Tickets`, that endpoint calls
`load_index()` again so the newly resolved ticket becomes searchable. Restarting the
backend also creates a fresh index from the database.

### 5. Embed the selected ticket

The frontend calls `POST /api/tickets/similar` with a selected new ticket's subject
and description. The route passes those fields to `search_similar_tickets()`.

The search function combines the fields with `build_text()` and calls the already
loaded model's `encode()` method to create the query vector. The historical vectors
are already in memory, so they do not need to be re-embedded for each request.

### 6. Calculate cosine similarity

The code calls `sentence_transformers.util.cos_sim()` to calculate the **cosine
similarity** between the new ticket vector and each historical ticket vector.

Cosine similarity compares the direction of two vectors:

- A higher score means the vectors point in more similar directions, and the text is
  considered more semantically similar by the model.
- A lower score means the text is considered less similar.

An intuitive analogy: imagine each vector points in a direction in a space with many
dimensions. If two vectors point in nearly the same direction, their angle is small
and their cosine similarity is high. The application uses this score as a ranking
signal; it is not a probability that the tickets are identical.

### 7. Optionally boost matching categories

If a category is provided to the search function, the code checks whether each
historical ticket has exactly the same category. A matching score is multiplied by
`1.15`; a non-matching score is left alone.

For example:

```text
semantic score: 0.60
same category:  0.60 × 1.15 = 0.69
different category:           0.60
```

The boosted ticket can move above another match. The current frontend does not send a
category for a new ticket, so this boost is not normally applied from the UI. Adding
category support end-to-end could improve ranking when categories are correct and
consistently assigned. It would require collecting/storing category for new tickets,
preserving it when resolving a ticket, and sending it with the similarity request.
Incorrect or overly broad categories could instead promote less relevant matches.

The multiplier is applied directly to a cosine score. As a result, a boosted score can
exceed `1.0`; it should therefore be treated as a ranking score, not a normalized
probability or guaranteed “percent match.”

### 8. Filter, rank, and return results

After calculating the scores, the code:

1. Sorts historical tickets from highest score to lowest.
2. Stops when it reaches a score below `0.45`.
3. Skips tickets without `resolution_notes`, since the feature is intended to surface
   useful resolved cases.
4. Adds ticket ID, subject, description, category, status, resolution notes, and the
   score rounded to four decimal places to the response.
5. Stops after collecting five results (`top_n = 5`).

The API response schema in `backend/schema.py` validates the returned fields, and the
Angular UI displays the description and resolution for each match.

## Worked example

Suppose an agent selects:

```text
Subject: The office printer keeps losing WiFi
Description: It goes offline several times during the workday.
```

The model turns this text into a 384-value query vector. The search engine compares it
with the historical ticket vectors. It might rank results like this:

| Historical ticket | Similarity score | Outcome |
|---|---:|---|
| “Printer goes offline from wireless network” | 0.78 | Returned if it has resolution notes |
| “Laptop drops VPN connection” | 0.51 | Returned if it has resolution notes and fits in the top five |
| “Invoice has an incorrect total” | 0.18 | Excluded because it is below 0.45 |

These scores are illustrative, not measured results from the current dataset. The
returned ticket includes its description and resolution so the agent can judge whether
the match is useful.

## AI/ML glossary

| Term | Meaning in this application |
|---|---|
| Artificial intelligence (AI) | The broad field of making software perform tasks that appear to require intelligence. Here, the application uses a language model to compare ticket text. |
| Machine learning (ML) | A way of building models that learn patterns from data. The sentence-transformer was trained before this application uses it. |
| Pretrained model | A model trained elsewhere and then reused for a task. `all-MiniLM-L6-v2` is used as-is; this code does not train it. |
| Sentence transformer | A model that maps text such as a sentence or paragraph into a vector that can be compared with other text vectors. |
| Embedding / vector | A list of numbers representing text in a form useful for comparing meaning. |
| Semantic search | Search based on meaning rather than requiring exact keyword overlap. |
| Inference / encoding | Applying the already-trained model to new text to produce its embedding. |
| Cosine similarity | A score comparing the directions of two vectors; used here to rank candidate tickets. |
| Threshold | A minimum score required for a candidate to be considered. The current value is `0.45`. |
| Ranking boost | A score adjustment that can move a candidate higher in the results. The category multiplier is `1.15`. |
| In-memory index | The IDs, ticket details, and vector matrix held in the backend process so searches can compare against them without reading all vectors from the database on each request. |
| Vectorized computation | Performing the same numerical operation across many vectors efficiently, rather than looping through every individual number in Python. |

## Python and NumPy concepts used in the search function

The examples in this section use a small pretend dataset so you can see what values
the code holds. In C# terms, a Python `list` is similar to `List<T>`, and a Python
`dict` is similar to `Dictionary<TKey, TValue>`.

### A `for` loop and a list comprehension

In Python, this loop:

```python
for ticket in tickets:
    print(ticket.ticket_id)
```

visits each item in `tickets` and assigns the current item to `ticket`. Python uses
indentation to show which statements belong inside the loop.

A **list comprehension** is a compact way to build a list from another iterable:

```python
_ticket_ids = [t.ticket_id for t in tickets]
```

It means “for every ticket `t` in `tickets`, take `t.ticket_id` and put it in a new
list.” The equivalent expanded Python is:

```python
_ticket_ids = []
for t in tickets:
    _ticket_ids.append(t.ticket_id)
```

The C#-style equivalent is:

```csharp
var ticketIds = tickets.Select(t => t.TicketId).ToList();
```

If `tickets` contains records `T-1001`, `T-1002`, and `T-1003`, then
`_ticket_ids` contains:

```python
["T-1001", "T-1002", "T-1003"]
```

A list keeps an order and uses zero-based positions: `_ticket_ids[0]` is `"T-1001"`,
`_ticket_ids[1]` is `"T-1002"`, and so on.

### A `dict` and a dictionary comprehension

A **dictionary** stores key/value pairs. In this code:

```python
_ticket_meta = {t.ticket_id: t for t in tickets}
```

each ticket ID is a key, and the complete ticket object is its value. This is a
**dictionary comprehension**. Its expanded form is:

```python
_ticket_meta = {}
for t in tickets:
    _ticket_meta[t.ticket_id] = t
```

The C#-style equivalent is:

```csharp
var ticketMeta = tickets.ToDictionary(t => t.TicketId, t => t);
```

Conceptually, the result looks like:

```python
{
    "T-1001": <Ticket object for T-1001>,
    "T-1002": <Ticket object for T-1002>,
    "T-1003": <Ticket object for T-1003>,
}
```

The value is not just the ID—it is the complete database row object. For example:

```python
ticket = _ticket_meta["T-1002"]
print(ticket.subject)
print(ticket.resolution_notes)
```

This retrieves the ticket's fields from memory without issuing another database
query. Dictionary keys must be unique: if two rows had the same ticket ID, the later
value would replace the earlier value in this dictionary. The database ticket ID is
the primary key, so it is expected to be unique.

### How vector positions connect to actual tickets

The ticket records, IDs, vectors, and scores all use corresponding positions. For
example, suppose the database query returned three tickets in this order:

| Position | `_ticket_ids[position]` | Ticket subject |
|---:|---|---|
| 0 | `T-1001` | Login problem |
| 1 | `T-1002` | Sync problem |
| 2 | `T-1003` | Printer problem |

`_vector_matrix` is built from the same `tickets` sequence, so its rows are:

```text
_vector_matrix[0] = embedding for T-1001
_vector_matrix[1] = embedding for T-1002
_vector_matrix[2] = embedding for T-1003
```

When the search calculates similarity, `scores` also follows that order:

```python
scores = [0.42, 0.81, 0.56]
```

So `scores[1]` is the score for `_ticket_ids[1]`, which is `T-1002`. The score itself
contains no ticket ID; the position is what connects the score to the ticket. This
matching order is essential: the vector matrix is constructed from `tickets`, and the
ID list and metadata dictionary are also constructed from that same sequence.

### What `ranked_indices` contains

This line:

```python
ranked_indices = np.argsort(scores)[::-1]
```

does not sort the ticket IDs. It produces the **positions** of the scores, ordered
from highest score to lowest.

Given:

```python
scores = [0.42, 0.81, 0.56]
```

`np.argsort(scores)` gives positions in ascending score order:

```python
[0, 2, 1]  # scores at those positions are 0.42, 0.56, 0.81
```

The slice `[::-1]` reverses that sequence:

```python
ranked_indices = [1, 2, 0]
```

This says: look at the ticket at position 1 first, then position 2, then position 0.
It contains neither ticket IDs nor scores—only positions (NumPy integer values).

The C# equivalent in spirit would be to sort the original positions by their score:

```csharp
int[] rankedIndices = Enumerable.Range(0, scores.Length)
    .OrderByDescending(index => scores[index])
    .ToArray();
```

### What `idx` means in the loop

```python
for idx in ranked_indices:
    score = float(scores[idx])
```

For the example above, the loop visits `idx` values `1`, then `2`, then `0`.
`idx` is a position into the original arrays, not a ticket ID.

The first iteration therefore does the following:

```python
idx = 1
score = float(scores[1])             # 0.81
ticket_id = _ticket_ids[1]            # "T-1002"
ticket = _ticket_meta[ticket_id]      # complete T-1002 database row
```

That is the path from a similarity score to the actual ticket data:

```text
idx = 1
  -> scores[1] is 0.81
  -> _ticket_ids[1] is "T-1002"
  -> _ticket_meta["T-1002"] is the full ticket object
  -> ticket.description and ticket.resolution_notes are read for the response
```

### Other Python expressions in this function

- **Function parameters and defaults:** `description: str | None = None` means the
  argument can be a string or `None`; if omitted, it defaults to `None`.
  `top_n: int = 5` defaults to five results. The `|` union syntax means “either type.”
- **`None`:** Python's value for “no value,” roughly comparable to `null` in C#.
- **`if` and early return:** `if _model is None ...: return []` exits immediately
  when search cannot run. `[]` is an empty list, so the API has no matches to return.
- **`enumerate`:** `for i, ticket_id in enumerate(_ticket_ids)` loops with both a
  position (`i`) and the ID at that position. It is similar to looping over indexes
  while also reading the item in C#.
- **Dictionary lookup:** `_ticket_meta[ticket_id]` gets the value for a key. It is
  similar to `ticketMeta[ticketId]` in C#. Looking up a missing key would raise an
  error, so the code relies on the IDs and dictionary being built from the same ticket
  records.
- **`continue`:** `continue` skips the rest of the current loop iteration. Here it
  skips a similar ticket if it has no resolution notes and continues to the next
  ranked ticket.
- **`break`:** `break` exits the loop completely. The function uses it when the score
  has fallen below the threshold and when it has collected `top_n` results.
- **`append`:** `results.append({...})` adds one new item to the end of the results
  list. This dictionary is one API result.
- **Dictionary literal:** `{ "ticket_id": ..., "subject": ... }` constructs one
  result as key/value fields, similar to building an object or dictionary in C#.
- **`float()` and `round()`:** `float(scores[idx])` converts the NumPy scalar to a
  regular Python float. `round(score, 4)` keeps four digits after the decimal point
  for the returned score.
- **`return results`:** sends the completed list of result dictionaries back to the
  FastAPI route, which serializes it as JSON.
- **`[0]` after `cos_sim`:** the similarity function returns a two-dimensional
  result (one query compared with each historical ticket). `[0]` selects the first
  query's row, giving one score per historical ticket.
- **`.numpy()`:** converts the tensor returned by Sentence Transformers into a NumPy
  array so NumPy operations such as `argsort()` can be used.

### Same example through the ranking loop

Assume:

```python
_ticket_ids = ["T-1001", "T-1002", "T-1003"]
scores = [0.42, 0.81, 0.56]
ranked_indices = [1, 2, 0]
SIMILARITY_THRESHOLD = 0.45
```

1. `idx = 1`: score is `0.81`; look up `T-1002`; if its resolution notes exist, add
   that ticket to `results`.
2. `idx = 2`: score is `0.56`; look up `T-1003`; if its resolution notes exist, add it.
3. `idx = 0`: score is `0.42`; this is below `0.45`, so `break` stops the loop.

The function returns the qualifying result dictionaries. The returned order is ranked
by score, not by ticket ID or database insertion order.

## Important limitations and interpretation

- **Similarity is not certainty.** The score is not a probability and does not prove
  that two tickets have the same cause or solution.
- **The threshold is a heuristic.** `0.45` is a configurable cutoff, not a universal
  definition of a good match. Its usefulness depends on this model and the ticket
  content.
- **The model can miss domain-specific context.** It is a general pretrained model,
  not one trained on this support team's labeled examples.
- **Text quality matters.** Empty, vague, or very short descriptions provide little
  information for meaningful matching.
- **Only tickets with vectors and resolution notes can be returned.** Missing
  embeddings prevent a ticket from entering the index; missing resolution notes cause
  a candidate to be skipped.
- **Category boosting depends on consistent labels.** The current UI does not provide
  a category for a new ticket, so the boost is not normally active in that flow.
- **The index is process-local.** Each new backend process loads the model and
  historical vectors into its own memory.
- **Embedding compatibility matters.** Historical vectors and query vectors should be
  generated with the same model and text-building logic. `EmbeddingModelVersion`
  records the model name for stored vectors, but the current index loader does not
  filter or validate vectors by that version.
- **The model may need to be downloaded once.** If its weights are not cached on the
  machine, the first model load requires access to the Hugging Face model repository.

## Main code locations

- `backend/search_engine.py` — model loading, text construction, embedding generation,
  index loading, similarity scoring, ranking, and response data.
- `backend/routers.py` — API endpoints that call the search engine and manage ticket
  creation/resolution.
- `backend/schema.py` — API request and response models.
- `backend/database.py` — `Tickets` and `TicketsNew` table definitions and database
  sessions.
- `seed_scripts/generate_embeddings.py` — batch embedding generation for seeded
  tickets.
- `frontend/src/app/ticket/Ticket.service.ts` — frontend calls to the ticket APIs.
