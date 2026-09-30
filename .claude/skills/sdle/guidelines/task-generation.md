## Guideline — Service-scoped tasks

Advisory. Tasks are where an approved placement either survives or quietly evaporates. A task that does not say which service it changes is a task that can be implemented in the wrong one.

### Every meaningful task names five things

| Field | Why |
|---|---|
| **Service** | which deployable unit this changes. Never "the backend" |
| **Requirement** | the requirement id(s) it satisfies |
| **Architecture** | the placement decision id it works under |
| **Contract** | the API or event contract it adds, changes or consumes, where there is one |
| **Verification** | how anyone knows it is done — the test, the check, the observable behaviour |

Housekeeping tasks (formatting, a dependency bump) need not carry all five. Anything that changes behaviour does.

### Cross-service work is three tasks, never one

```
service-local task in A   +   service-local task in B   +   integration verification
```

One task spanning two services cannot be sequenced, cannot be assigned, and cannot fail informatively. The integration task is the one that proves the contract actually holds end to end — it is not optional, and it is not the same as either side's unit tests.

### Per outcome

**`EXTRACT_EXISTING_CAPABILITY`** needs three families of task, and the middle one is the family that gets forgotten:

1. **build** the new service — structure, data store, contracts, deployment;
2. **migrate** the existing behaviour and its data into it, and repoint callers;
3. **regress** — tests proving the behaviour that lived in the old owner still holds after the move.

If the task list has no migration tasks and no regression tasks, it is not an extraction; it is a new service beside an old one that still does the same job.

**`KEEP_EMBEDDED_AND_MONITOR`** needs at least one task that establishes the module seam, and it should say so in those words, so a reviewer can check the seam exists rather than inferring it from the diff.

**`CREATE_NEW_SERVICE`** needs the unglamorous ones: configuration, observability, health, deployment. A service that exists only in application code is not deployable and the implementation gate will say so.
