## Guideline — Planning against an approved placement

Advisory. Read the approved placement first: `sdle.sh architecture show` for the catalog, and the WorkItem's rendered placement for the decision. The plan implements that decision; it does not revisit it.

### What the plan must address

Whatever the outcome, say something concrete about each of these — including "no change", which is an answer:

- **Target service(s).** Which service each part of the work lands in, by name.
- **Existing versus new.** Whether a module, a package or a whole service is being created.
- **Data ownership.** Which service owns which data afterwards, and what moves.
- **API contracts.** What is added, changed or deprecated, and who consumes it.
- **Event contracts.** What is published and what is consumed.
- **External integrations.** Which outside systems this touches, and from which service.
- **Migration.** How existing data and behaviour get from where they are to where the placement says they belong.
- **Backward compatibility.** What keeps working during and after, and for how long.
- **Deployment impact.** New deployable units, configuration, secrets, infrastructure.
- **Regression impact.** What existing behaviour could break, and how it is covered.

### Per outcome

**`EXTEND_EXISTING_SERVICE`** — the plan stays inside one service. If it starts describing a second deployable unit, the placement is being redefined: stop and raise it rather than planning around it.

**`CREATE_NEW_SERVICE`** — plan the service as a first-class thing: its data store, its contracts, its deployment, its observability, and how the existing services reach it. The service is `PLANNED` in the catalog until the implementation gate is approved.

**`KEEP_EMBEDDED_AND_MONITOR`** — plan the **module seam** explicitly. The plan should name the boundary inside the owning service (its own package or directory, its own interface, no shared internal state) so a later extraction is a move, not a rewrite.

**`EXTRACT_EXISTING_CAPABILITY`** — plan **both halves**, and do not let the new feature crowd out the migration:

1. moving the existing behaviour, with its data, into the new service;
2. the new requirements this WorkItem brings;
3. the contracts the old service now calls instead of calling itself;
4. compatibility for anything already depending on the old placement;
5. regression coverage proving the migrated behaviour still holds.

A plan that covers only (2) is the most common way an extraction goes wrong.

### Cross-service work

Where work spans services, plan it as service-local work plus an explicit integration step. A plan that treats two services as one codebase produces tasks nobody can sequence or verify independently.
