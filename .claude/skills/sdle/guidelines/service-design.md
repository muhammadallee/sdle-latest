## Guideline — Service-aware design

Advisory. The primary design artifact stays exactly what it is — the single gated design document. This guideline says which **sections** it grows once a placement is approved, and what belongs in each.

Optional per-service secondary documents may sit under the existing `design/` structure, but the primary artifact remains the one gated truth. A design fact that lives only in a secondary document is a fact the gate never saw.

### Sections to add

Say something concrete about each of these — **including "no change", which is an answer**. The rows marked *(distributed only)* are about boundaries between deployable units: in a repository with one service, or for an `EXTEND_EXISTING_SERVICE` or `KEEP_EMBEDDED_AND_MONITOR` placement that adds no boundary, they are legitimately "none". A design that invents an event stream because the template had a row for it is the mildest form of premature distribution, and it is still premature distribution.

| Section | What belongs in it |
|---|---|
| **Service impact** | every service this WorkItem changes, and how |
| **Responsibilities** | what the owning service is responsible for after this change |
| **Explicit non-responsibilities** | what it is deliberately *not* responsible for. The most useful section on the list, and the one most often omitted |
| **Capability ownership** | which capability this service owns, and at what status |
| **Data ownership** | which data it owns, and which data it only reads |
| **API contracts** *(distributed only)* | endpoints or operations added, changed, deprecated — with their consumers |
| **Published / consumed events** *(distributed only)* | the asynchronous surface, in both directions |
| **Transaction boundaries** | where a transaction begins and ends, and what is deliberately outside it |
| **Consistency model** | what is strongly consistent, what is eventually consistent, and what the user-visible consequence is |
| **Failure handling** | what happens when a dependency is slow, down, or returns an error; retries, idempotency, compensation |
| **Security boundary** | who may call this, how they are authenticated and authorised, what data is sensitive |
| **Deployment impact** *(distributed only)* | new units, configuration, migrations, rollout order |
| **Migration / extraction design** | only for `EXTRACT_EXISTING_CAPABILITY` — how behaviour and data move without breaking callers |

### Rules that matter more than the section list

- **Non-responsibilities are load-bearing.** "This service does not own the applicant's identity" prevents a class of future mistakes that no positive statement prevents.
- **Never contradict the catalog.** If the design assigns data to a service the catalog says does not own it, that is a defect in one of the two — surface it rather than writing the design as though the catalog agreed.
- **Never redefine the boundary here.** The design realises the approved placement. If the design work shows the placement was wrong, stop and raise it; do not design a different architecture and let the gate discover it.
- **A transaction that crosses services is a finding, not a design.** Say so explicitly and name the consistency model that replaces it.
