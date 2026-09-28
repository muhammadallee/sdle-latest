# Link Shortener Service

## Purpose

Internal teams currently paste long, unwieldy URLs into chat and documentation, which breaks link
previews and makes tracking click-through hard. This service lets any employee turn a long URL into a
short, memorable one and see how many times it was used.

## Scope

In scope:

- Creating a short link from a long URL, with an optional custom slug
- Redirecting a short link to its target URL
- Reporting click counts per short link
- Expiring a short link after a chosen date

Out of scope:

- Public (non-employee) link creation
- Custom domains other than `go.internal.example`
- Link preview generation or metadata scraping

## Data Model

A **Link** has: `slug` (string, unique), `target_url` (string), `created_by` (employee id),
`created_at` (timestamp), `expires_at` (timestamp, optional), `click_count` (integer, defaults to 0).

## Compatibility

- Redirects must return HTTP 301 so existing link-preview bots (already deployed, unmodified) continue
  to work exactly as they do with the current ad-hoc shortener.
- The slug format must remain compatible with the URLs already shared in the last six months (lowercase
  alphanumeric plus hyphen, 4-12 characters) so old links keep resolving.

## Dependencies

- Internal SSO service (SAML 2.0, existing internal endpoint, version already pinned by platform team).
- Shared Postgres 14 instance (existing, no schema changes to other services' tables).

## Security and Data Handling

- Only authenticated employees may create links; redirection itself is unauthenticated (short links are
  meant to be shared externally once created).
- Target URLs are logged for audit; no other personal data is collected beyond `created_by`.
- Slugs must not be guessable sequential integers, to prevent enumeration of internal links.

## Non-Functional Requirements

- A redirect must complete within 100 ms at the 95th percentile at up to 200 redirects per second.
- The service must support at least 50 link creations per second at peak.

## Acceptance

1. AC-1: Creating a link with a valid URL and no slug returns a generated 6-character slug and a 201
   response.
2. AC-2: Visiting a valid short link returns an HTTP 301 to the target URL, served with `Cache-Control: no-store` so every visit reaches the service, and increments `click_count`.
3. AC-3: Visiting an expired short link returns an HTTP 410.
4. AC-4: Creating a link with a slug that is already taken returns an HTTP 409.
