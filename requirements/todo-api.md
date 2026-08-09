# Todo List REST API

A small REST API for managing personal todo items. This document is the ground
truth input for the SDLE workflow: it is the repository's test fixture, and the
subject of every transcript under `docs/dry-runs/`.

## Purpose

Let a single user create, read, update, complete and delete todo items over
HTTP, with enough structure to exercise validation, filtering and persistence
without becoming a large system.

## Scope

In scope:

- CRUD over todo items
- Filtering the list by completion state
- A shortcut endpoint for marking an item complete
- Input validation with a consistent error format
- Persistence to a relational store

Out of scope:

- Authentication, authorisation and multi-user accounts
- Sharing, collaboration or assignment
- Attachments, comments and reminders
- Rate limiting and quotas

## Data Model

A **Todo** has:

| Field | Type | Rules |
|---|---|---|
| `id` | integer | Server-assigned, immutable |
| `title` | string | Required, 1–200 characters, trimmed |
| `notes` | string | Optional, up to 2000 characters |
| `completed` | boolean | Defaults to `false` |
| `due_date` | date | Optional, ISO-8601 (`YYYY-MM-DD`) |
| `created_at` | timestamp | Server-assigned, UTC, immutable |
| `updated_at` | timestamp | Server-assigned, UTC, updated on every write |

## Endpoints

| Method | Path | Behaviour |
|---|---|---|
| `POST` | `/todos` | Create a todo. Returns `201` and the created item. |
| `GET` | `/todos` | List todos. Supports `?completed=true\|false`. |
| `GET` | `/todos/{id}` | Fetch one todo. `404` if absent. |
| `PATCH` | `/todos/{id}` | Partial update. `404` if absent. |
| `POST` | `/todos/{id}/complete` | Mark complete. Idempotent. |
| `DELETE` | `/todos/{id}` | Delete. Returns `204`. `404` if absent. |

## Behavioural Requirements

1. Completed todos are **included** in the default list view; `?completed=false`
   is opt-in filtering, not the default.
2. The list is ordered by `created_at` descending.
3. `POST /todos/{id}/complete` on an already-complete todo succeeds and changes
   nothing — completing twice is not an error.
4. `PATCH` accepts any subset of the writable fields. An empty body is a `400`.
5. `updated_at` changes only when a write actually modifies a field.

## Validation and Errors

Every failure returns the same envelope:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Human-readable summary",
    "details": [ { "field": "title", "issue": "must be 1-200 characters" } ]
  }
}
```

- `400` — malformed body or failed validation
- `404` — no such todo
- `422` — well-formed but semantically invalid (e.g. `due_date` in the past)
- `500` — unexpected failure; never leaks a stack trace to the client

Validation happens at the boundary. No unvalidated user data reaches the
persistence layer.

## Non-Functional Constraints

- Single-process deployment is acceptable; no clustering required.
- A read of the list must return within 200 ms for 10,000 stored items.
- All timestamps are stored and returned in UTC.
- No secrets in source. Configuration comes from the environment.
- Every endpoint has automated test coverage, including its failure modes.

## Acceptance

The feature is done when all six endpoints behave as described above, the error
envelope is consistent across every failure mode, the validation rules are
enforced, and the automated test suite passes.
