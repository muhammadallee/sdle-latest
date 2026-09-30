## Guideline — Implementing inside an approved boundary

Advisory. Implementation **realises** the approved placement. It may not silently redesign it.

### The one hard rule

If implementation reveals the placement was wrong — the boundary does not hold, the data cannot be owned where the decision says, the contract cannot work — **stop and say so**. Raise it as an architecture change and let a human decide. Moving code between services because the original placement proved awkward is exactly the drift the placement gate exists to prevent, and it leaves the catalog describing an architecture the repository no longer has.

### Per outcome

**`EXTEND_EXISTING_SERVICE`** — all the work lands in the owning service. If a second deployable unit appears in the diff, the boundary changed without a decision.

**`CREATE_NEW_SERVICE`** — build it as a real service: its own configuration, its own data store, its own health and observability, its own deployment. It stays `PLANNED` in the catalog until the implementation gate is approved, at which point the engine marks it implemented.

**`EXTRACT_EXISTING_CAPABILITY`** — the migrated behaviour must still work, and must be **demonstrably** still working. Regression coverage for the behaviour that moved is part of the implementation, not a follow-up. Repoint callers deliberately; leave compatibility in place for as long as the plan said.

### `KEEP_EMBEDDED_AND_MONITOR` — preserve the seam

The capability stays inside the owning service **and** stays extractable. In practice:

```
application-service/
├── application/          the owner's own domain
└── risk-assessment/      the embedded capability, whole
```

- one directory or package, containing the capability's model, rules and persistence access;
- an explicit interface the rest of the service calls — not scattered calls into its internals;
- no shared mutable state reaching across the seam;
- its data reachable through its own access layer, even when it lives in a shared schema.

What this is **not**: a second deployable unit, a network hop, or a premature abstraction layer with one implementation for its own sake. The seam is a directory boundary and an interface. That is the whole cost, and it is what makes a later extraction a move instead of a rewrite.

A seam nobody can find in the diff is a seam that does not exist. If the code review cannot point at it, it was not preserved.
