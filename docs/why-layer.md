# The WHY layer in Familiar

How this repository keeps intent next to code and method. It is Why1st
(`PRD -> Why Graph -> contracts -> validator`) in a shape chosen for agents that
read whole files, navigate with tools and work in bounded roles. Read this
before you edit the graph or a contract; do not pin it.

---

## 1) Load rule

| You are | Read at start | Open on demand |
|---|---|---|
| Working on the engine (this repo) | `AGENTS.md`, `docs/why-graph.xml` (the router) | the PRD section your capability points at; the one shard your task names; a second shard when an outgoing or incoming router edge touches the change |
| Working for a family (an instance) | the role sheet you were given | nothing here: the graph is not for you |
| A delegated subagent | what the brief names: one shard or less | — |

For core changes, use `python scripts/why_impact.py <module-id|path|feature-id|PRD-key>`
when declared coupling is not already clear. It retrieves direct dependencies and consumers in both shard and router,
feature guarantees, named checks, reverse contracts and PRD keys. Follow relevant
consumers as well as dependencies; load their shards on demand.

The layer promises orientation and declared coupling, not a complete blast radius.
Imports, literal fixtures, packaging and undeclared conventions still need search.
The command prints a starting `rg` command; add domain vocabulary and inspect
matches before stopping. Structural validity does not prove semantic completeness.

## 2) The four artifacts

| Artifact | File | Holds |
|---|---|---|
| PRD | `docs/PRD.md` | what and for whom; sections carry `<!-- PRD_ANCHOR: KEY -->` markers |
| Router | `docs/why-graph.xml` | use cases, one entry per capability, **every** cross-capability edge |
| Shard | `docs/why-graph/<capability>.xml` | one capability: its features and modules |
| Module contract | head of each governed file | purpose, invariants with what holds them, hidden coupling |

Optional reference diagnostic: `python -X utf8 scripts/validate_why.py`. Core
graph nodes, contracts and code move in one commit. Surface contracts are optional.

## 3) Module contract

Core files listed in `src/familiar/check-weights.json` have a module node and
a contract. Surface code, reader/desk pages, method prose and styles need neither;
an optional purpose line is enough. Existing explicit references remain navigable.
No duplicated-prose, field-order, reviewer-name or per-invariant test lint remains.
Keep purpose, guarantees and hidden coupling useful to a reader of the code.

```python
# START_MODULE_CONTRACT: MOD-RULES-CASCADE
# PURPOSE: Resolve a setting or a rule mode for a scope and say which layer decided.
# PRD_REF: docs/PRD.md#SETTINGS
# INVARIANTS:
# - a trust rule cannot be weakened by any layer [test: tests/gate/test_data_guarantees.py::test_f9_trust_mode_cannot_be_changed]
# - every resolution carries the chain of layers, engine first, winner last [review: engine lead]
# CHANGES_WITH:
# - MOD-RULES-MODEL (record fields)
# - docs/PRD.md#RULES-MODEL
# :END_MODULE_CONTRACT
```

Markdown uses one `<!-- ... -->` comment after front matter; TOML uses `#`.

- **The marker carries the module ID.** The same string is the graph node, the
  contract, and the name used in tests and logs: one `grep` lands on all of them.
- **`PURPOSE`** — why the file exists, not what its functions do.
- **`INVARIANTS`** — guarantees other parts rely on. Each ends with what
  **holds** it: `[test: path::name]` naming the shared installed journey or a data check,
  or `[review: role]` naming a declared reviewer.
  A module needs no test of its own; most are held by a journey that passes
  through them or by the reviewer who reads their diff. An invariant nothing
  holds is a wish. A reviewer is sufficient: no companion test is required. An explicit
  test reference is checked for validity, not for semantic coverage.
- **`CHANGES_WITH`** — only coupling the code does not show: data schemas,
  documents, modules in another layer. One target per line: a module ID, a
  path, or a PRD key; a note in brackets may follow. Imports are not repeated.
- Nothing else. No file path, no version, no change history: the file system
  and git already hold them.

## 4) What is deliberately absent

- **Module INTENT on implemented nodes.** PURPOSE in the file is authoritative;
  the validator rejects a second intent. PLANNED nodes retain intent until extraction.
- **Function contracts and block anchors.** A module small enough to read in
  one call needs no map of its inside; names, signatures and docstrings carry
  it. If a file seems to need anchors, split the file: the budget is about 400
  lines per module, and the validator warns above it.
- **`ANCHOR` elements in the graph.** A module node names its file; the
  contract in that file carries the node's ID. One link to keep true instead of
  two.
- **Semantic logs.** They come with the first runtime workflow extracted here,
  and their `anchor` field will carry module IDs.

## 5) Graph shape

Prompt-XML as in Why1st: the tag is the entity, relations sit inside the entity
that owns them, no `<?xml?>` line, no generic `<node kind=...>`. A distinctive
tag and ID make every entity a one-command search across PRD, graph, code and
tests, which is how agents here actually find things.

```xml
<CAPABILITY_RULES ID="CAP-RULES" SHARD="docs/why-graph/rules.xml" STATE="STARTED">
  <INTENT>Four kinds of rules, one registry of settings, one cascade, first-class exceptions.</INTENT>
  <PRD_REF>docs/PRD.md#SETTINGS</PRD_REF>
  <REL TYPE="DEPENDS_ON" TARGET="CAP-INSTANCE"/>
</CAPABILITY_RULES>
```

```xml
<MODULE_RULES_CASCADE ID="MOD-RULES-CASCADE" FILE="src/familiar/rules/cascade.py" STATE="IMPLEMENTED">
  <INTENT>Resolution with provenance.</INTENT>
  <REL TYPE="DEPENDS_ON" TARGET="MOD-RULES-MODEL"/>
</MODULE_RULES_CASCADE>
```

A feature may declare shared guarantees as direct children:

```xml
<INVARIANT REVIEW="cold reviewer">each sheet fits in 6 KB</INVARIANT>
<INVARIANT REVIEW="cold reviewer">letters ask a witness before the guess</INVARIANT>
```

Exactly one attribute: `TEST` names one function of a declared test kind
(optionally class-qualified, a parametrized function without its case suffix);
`REVIEW` names a declared reviewer. Nonempty text and at least one direct
`IMPLEMENTED_BY` module are required. The guarantee applies to every such
module, without transitive inheritance.

- Families: `USECASE_*` (router), `CAPABILITY_*` (router), `FEATURE_*` and
  `MODULE_*` (shards). Add a family only when something real needs it.
- Relations: `COVERS`, `IMPLEMENTED_BY`, `DEPENDS_ON`, `READS`, `WRITES`,
  `IMPACTS`. Targets are bare IDs.
- `STATE`: `PLANNED`, `STARTED`, `IMPLEMENTED`. A `PLANNED` module needs no
  file; a `PLANNED` capability needs no shard. Anything else is enforced.
- **Edge-home rule.** An edge between two entities of one capability lives in
  the shard. An edge that crosses capabilities lives only in the router, on the
  source capability's entry, written between capabilities. If a module in one
  capability needs a module in another, that is a capability edge plus a line
  in the module's `CHANGES_WITH`.
- Budgets: router up to 12 capabilities and 40 edges; shard up to 30 elements.
  Over budget means merge or question the boundary, never a second router.
  Shard elements means entities with IDs; use-case-to-capability edges are the
  router exception to the capability-only cross-capability edge rule.
- A shard has one owner at a time. Parallel agents take different shards.
- Whoever creates a shard registers it: `SHARD` and `STATE` on its own
  capability entry in the router, and nothing else there. Edges between
  capabilities are the lead's to add.

## 6) Order of work

- **Intent changes or crosses capabilities:** PRD, then router or shard, then
  contracts, then code and tests, then the validator.
- **Local change inside a core module:** code, contract and shard in the same
  commit. Surface changes do not require a contract or graph edit.
- **Stale graph found:** fix the graph and the contract of the file you are
  touching anyway. Never bend code to match a stale graph.

## 7) What the validator proves and what it does not

The optional validator reports missing explicit files, graph IDs, PRD keys and
named tests, plus missing core contracts/nodes. Every such finding is advice;
it does not require a change before committing. Surface omissions are silent.
It no longer checks naming, graph shape/placement, prose duplication, module
size, reviewer labels, method vocabulary or skill command tables.

Neither a resolved reference nor a green suite proves semantic completeness.
Read the changed code and primary material. Only test size is a blocking budget.

## 8) Why this differs from canonical Why1st

| Canonical | Here | Reason |
|---|---|---|
| Module, class, method contracts and block anchors | Module contract only | A whole module is read in one call; inner contracts restate code and go stale first. What cannot be read from code is why the module exists, what others rely on, and what changes with it |
| Invariants as prose | Each invariant names what holds it: the shared journey, a data check, or a reviewer | A sentence nobody holds is a wish. But "a test per invariant" made agents write and maintain unit tests for code rewritten the same day: 404 test functions on 8 000 lines, four green-suite reviews in a row that found real breakage only by walking the installed engine (12.11.2026). A shared end-to-end holder is the tripwire that caught things |
| Invariants repeated per module | Shared guarantees on the feature, local guarantees in contracts | Field evidence: nine role sheets forced eighteen wrapper tests and role-labelled sentences for two shared guarantees |
| Outgoing navigation alone | Impact command follows incoming edges and reverse contracts | Cold review: three simulations missed mode fixtures, host-provenance checks and the role registry; those links are now declared, search remains required |
| `LINKS` per method | `CHANGES_WITH` per module, hidden coupling only | Import graphs are cheap to read; repeated links are noise that hides the one link that matters |
| One graph file, shard later | Router and shards from the start | Roles here work in small contexts and by tools; the pinned surface must stay small for good. Splitting at zero costs nothing, splitting later is a migration. A shard is also a ready brief for a subagent and a unit of ownership for parallel work |
| `ANCHOR` elements pointing at `START_*` markers | Module node `FILE` plus the same ID in the contract | One reference instead of two |
| Tag shapes argued from attention in saturated context | Same shapes, argued from search | Retrieval by `grep` is the working path; distinctive IDs serve it |
| Code is what is governed | Code, method text and rule data | Half of this engine is text and data that steer agents; it drifts the same way |

Kept without change: marker-keyed PRD references, no line numbers, core graph and
code in one commit, stale nodes deleted rather than marked, the Agent1st core
of `AGENTS.md` byte-identical.

## 9) Checks by value

The registry is `src/familiar/check-weights.json`; `check_policy.py` applies it
in pytest and family findings. Each rule records `guards`, `base`, `cost`,
`caught`; costs reference shared run measurements and source-history counts.
`none` is an honest absence of evidence for a caught family bug, not a count of
passing assertions. History begins on 14 November: it cannot establish two weeks
of stability. Core means the stable data/security/installation responsibility,
with the observed file churn recorded beside it, not a claim its code never moves.

- `data`, `privacy`, `install` + `core`: block. One honest refusal and a valid
  control per guarantee; retain exact source, privacy boundaries and review-byte binding.
- `journey`: one installed memory → paper → tree → reader path, blocking.
- `surface` or `form`: delete; do not write a new check. Only broken references
  that could break a build/package may stay as advice. Missing weight: advice.
- Before adding a core check, record a concrete missed family failure, its
  evidence, observed churn and incremental cost. A second route or appearance
  variant does not justify another test. UI acceptance is a manual browser walk.

During work run the affected guarantee when its code changes. Before done:
`uv run pytest -q --full` once, including all fast checks and the one installed
journey. `uv run pytest -q` is an optional shorter iteration; no redundant replay
before each commit. Before release, commit and run `scripts/check_release.py`
with every real family root denied and the wheel output outside the checkout.

`python -X utf8 scripts/validate_why.py` and `uv run ruff check --exit-zero` are
optional advice. `validate_skills.py` was removed. Shell rebuild reproducibility
is optional `check_release.py --rebuild-shell`; required wheel files and denied
family access remain blocking. No new server or UI test is required here.

Test/code nonempty lines: at most 0.03, blocking by the owner's explicit size
exception. Fast 10 s and full 22 s: advisory targets on every host, quiet or busy;
a time overrun never changes exit status. A failing registered core guarantee or
the single journey still fails. A failing unregistered test prints its actual
finding as advice. Register a justified guarantee before using it as acceptance.

Core contracts and graph nodes remain required authoring artifacts in the code
commit. Their diagnostic is advisory because contracts describe responsibility;
they are not a second data guarantee. Surface omissions are never reported.
Declared reviewers may hold meaning without a companion test: engine lead,
cold reviewer, pack keeper, or the family's reviewer. Review is not another
mandatory validator run.
