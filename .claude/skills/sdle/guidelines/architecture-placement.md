## Guideline — Architecture placement heuristics

Advisory. Position 5 in the precedence chain in `modules/architecture-placement.md`: approved requirements, the constitution, approved architecture decisions and this WorkItem's approved artifacts all outrank everything below. A guideline that contradicts an approved decision loses.

These are heuristics for a judgement the engine deliberately does not make. Nothing here is checked mechanically; the engine checks the *shape* of your answer, never its wisdom.

---

### Prefer `EXTEND_EXISTING_SERVICE`

- the capability is already owned by that service;
- the same invariants and the same aggregate apply;
- the data is the same data, under the same owner;
- there is no independent business lifecycle — the two things are released, scaled and operated together;
- separating would add a network hop, a contract and a deployment unit while adding no autonomy.

This is the default for most WorkItems in a mature repository, and it is not a lesser answer.

### Consider `CREATE_NEW_SERVICE`

Look for several of these together, not one of them alone:

- a cohesive capability with a business meaning of its own;
- meaningful independent data it, and only it, owns;
- a distinct business lifecycle — it changes for different reasons, on a different rhythm;
- a different security boundary: different actors, different sensitivity, different audit obligations;
- distinct integration responsibility toward an external system;
- independent release behaviour, or operational characteristics (scaling, availability, latency) that genuinely differ.

**WorkItem size is never the criterion.** A large WorkItem inside one capability is still one capability; a small WorkItem that opens a genuinely separate capability with its own data and lifecycle may justify a service.

### Prefer `KEEP_EMBEDDED_AND_MONITOR`

- a boundary is visible, but the scope today is small;
- growth is plausible but not yet evidenced;
- the data is not yet independently meaningful;
- independent deployment would cost more than it returns right now.

Record the candidate with honest re-evaluation conditions — *"a second WorkItem lands in this capability"*, *"this capability acquires its own external integration"*, *"its data stops being read transactionally with the owner's"*. A candidate nobody will revisit is not monitoring, it is a note.

Implementation must then preserve a real module seam. Embedded is a decision about deployment, not an excuse for scattering the logic.

### Consider `EXTRACT_EXISTING_CAPABILITY`

Extraction is justified by *accumulation*, and usually by several of:

- related WorkItems have piled up in the embedded capability;
- the owning service's responsibilities have become incoherent to describe;
- data ownership has become independently meaningful;
- an independent lifecycle or a distinct integration has emerged;
- change coupling is rising — edits to one part keep forcing edits to the other;
- the existing seam makes extraction a move rather than a rewrite.

An extraction is never only a new feature. Its scope always includes the existing behaviour that has to keep working, the contract changes, the data-ownership move, backward compatibility and regression coverage.

### Choose `ARCHITECTURE_REVIEW_REQUIRED` when you would otherwise guess

- two services appear to own the same capability or the same data;
- the aggregate boundary is genuinely unclear;
- existing architecture decisions contradict each other;
- the WorkItem implies a transaction spanning services;
- the requirements do not say enough to place the capability anywhere.

This is a correct answer, not a failure. It stops the WorkItem and asks a human, which is cheaper than a boundary the repository then has to live with.

---

### Anti-patterns — warn, and do not propose

- **One service per entity.** An entity is not a capability.
- **One service per table.** Physical schema is not an architecture boundary.
- **One service per controller or endpoint.** That is a routing table, distributed.
- **One service per screen.** The UI's shape is not the domain's.
- **One service per WorkItem.** WorkItems are delivery units; services are capability boundaries. Nothing makes them correspond.
- **One service per SRS section.** A document's headings are an editorial decision.
- **Nanoservices.** A service with no independent data, no independent lifecycle and no independent reason to change is a function call with a network in the middle, a deployment pipeline of its own and a new failure mode.
- **Extraction on aesthetics.** "This feels like it should be separate" is not evidence. Name the dimension that moved.

### Two failure modes worth naming

**Premature distribution** buys autonomy nobody needed and pays for it in latency, partial failure, eventual consistency and operational surface. **Permanent entanglement** saves that cost and pays it later, all at once, in a service nobody can pull apart. `KEEP_EMBEDDED_AND_MONITOR` exists precisely because the honest answer is often *"not yet, and here is what would change our mind"*.
