# Meeting Notes Service

## Purpose

Project teams keep meeting notes in personal documents, so decisions are hard to find later and action
items are forgotten. This service gives every team one searchable place for meeting notes and the action
items that come out of them.

## Scope

In scope:

- Creating, editing and deleting a meeting note, with a title, date, attendees and free text
- Recording action items on a note, each with an owner and a due date
- Searching notes by title, attendee or text
- Listing the open action items owned by the signed-in user

Out of scope:

- Audio recording or transcription of meetings
- Calendar integration or sending meeting invitations
- Editing a note simultaneously by several people (the last save wins)

## Data Model

A **Note** has: `id` (unique), `title` (string, 1-200 characters), `held_on` (date), `attendees` (list of
employee ids), `body` (text, up to 50,000 characters), `created_by` (employee id).

An **ActionItem** has: `id` (unique), `note_id`, `description` (string), `owner` (employee id), `due_on`
(date) and `done` (boolean, defaults to false).

Notes and action items are persisted in a relational store. Attachments up to 10 MB are kept in an object
store and referenced from the note.

## Constraints

- Must run inside the existing internal Kubernetes cluster.
- Must authenticate every request against the existing internal SSO (OpenID Connect); there is no separate
  login.
- No new paid third-party services.

## Compatibility

- Employee ids are the ids the internal SSO already issues; no new identifier scheme is introduced.
- Dates are exchanged as ISO 8601 calendar dates.

## Dependencies

- Internal SSO service (OpenID Connect, the existing internal endpoint operated by the platform team).
- Internal email relay at `smtp.internal.example`, used to remind owners of action items due the next day.

## Security and Data Handling

- Only authenticated employees may read or write notes; a note is visible only to its attendees and its
  creator.
- Notes may contain personal data about attendees; they are never written to application logs.
- Attachments are scanned for malware before they are stored.

## Non-Functional Requirements

- A search must return within 500 ms at the 95th percentile for up to 100,000 stored notes.
- The service must handle at least 20 concurrent users without degraded response times.

## Acceptance

1. AC-1: Creating a note with a title, a date and at least one attendee returns a 201 response and the new
   note's id.
2. AC-2: Recording an action item with an owner and a due date returns a 201 response, and the item
   appears in that owner's open-items list.
3. AC-3: A signed-in user who is neither an attendee nor the creator of a note receives a 404 when
   requesting it.
4. AC-4: Marking an action item done removes it from the owner's open-items list.
