<!-- Adopter addendum — project-specific. Agent1st Core below is unmodified. -->
## Familiar — engine work

The engine and method live here; real families live elsewhere. Pin
`docs/why-graph.xml`; open the relevant PRD section/shard on demand.

- Only `instance/writer.py` mutates family/output files in engine code. Register
  adapters with `gate.boundary`, serialize sealed projections and consume checked
  generations (`docs/gate.md`). No real family names, ids, paths or prompts here.
- `src/familiar/check-weights.json` is the one weight registry: `guards`, `base`,
  `cost`, `caught`; shared run costs and source churn sit beside the entries.
  `check_policy.py` applies it. Missing weight means advice, never a new blocker.
- Before writing a check, record the concrete missed family failure and its cost.
  Keep core data/privacy/install guarantees, one refusal/control each, and **one**
  installed memory → paper → tree → reader journey. Surface/form checks are not
  written: delete them. Only broken build/package references may remain advice.
- Active development, no stable version planned: checks only keep the journey and core data/privacy/install from
  falling apart; never write "stabilising" checks, never raise the test budget for them. A behaviour fix is not a
  stricter check. A new release must not invalidate data researchers already wrote without carrying it over:
  a changed stored form ships its carry-over command in the same release and a CHANGELOG line starting `Data:`
  (`docs/upgrading.md` is the public promise; old commands, flags and pages are not kept for compatibility).
- This repository is public. `main` is pushed as it is: no real family names, ids, paths, prompts or host
  machine paths in files **or commit messages**. Outsiders install tags, so tag only what families ran.
- During work run the affected guarantee after changing it. Before **done**:
  **`uv run pytest -q --full` once**, including fast checks. `uv run pytest -q`
  is an optional shorter iteration, not another pre-commit requirement. No nested
  or source replay of the installed journey; no automatic UI tests. Interface
  acceptance uses a manual browser walk when the task includes interface work,
  on the host's real local instance the task names (evidence outside the repo);
  fixtures and tests committed here stay fictional because the repository is public.
- Before delivering a release: commit, then `uv run python -X utf8
  scripts/check_release.py --deny-root <each-family-root> --wheel-dir <outside-repo>`.
  It checks the archive, denied roots and required wheel files. Optional
  `--rebuild-shell` only advises and never changes delivered bytes.
- Optional, nonblocking: `python -X utf8 scripts/validate_why.py` and
  `uv run ruff check --exit-zero`. Skill/role/text/style lint is removed.
- Core paths in the registry require a contract and graph node with the code in
  one commit. Surface files need neither; an optional purpose line is enough.
  Keep explicit links valid. WHY reports core omissions/broken links as advice.
- Nonempty test/code lines: at most 3%, blocking. Fast 10 s/full 22 s: advisory
  under every load. A failing weighted core guarantee or the journey still fails.
- Family checks collect all findings with paths. Only weighted core data/privacy/
  install findings block delivery. Source fidelity and review-byte binding
  stay strict; unadopted collector drafts remain separate. Presentation preferences
  use safe defaults; they do not change stored inputs or authorize disclosure.
- `docs/` holds living product docs; reports go outside the repo. Leave no servers.
  Raise `0.MINOR.PATCH` with the change and CHANGELOG: MINOR for a family-visible
  feature, PATCH for maintenance; one task shares one raise. Family work follows
  its assigned role rather than these engine-work requirements.

### Who makes this

Familiar is co-authored by a person and agents. This is the project's working fact, not a slogan. If you work
here you are a participant:

- Write in the project's voice ("we") in docs, issues, commits and releases. Wording does not wait for the
  human co-author's sign-off; when he later changes your text, that is a co-author editing, not an owner
  overruling.
- Sign what you made: `Co-Authored-By:` with your model.
- Say what is wrong with the task, the tools or the direction (CDD below). A workaround without a complaint
  hides debt from the other authors.
- The same holds for outside agents: an agent that runs Familiar for its host's family may open an issue or
  a pull request in its own name, naming its model and its host's consent.

What stays with people: a family's own decisions, sending and publishing on a host's behalf, money, and
anything irreversible outside this repository.

### Pages and display

Показ работы агентов (статистика, ход работы) строится только из уже существующих следов работы; он не добавляет исследователям ни одного шага, поля или проверки — грубые числа лучше налога на исследование.

---

# AGENTS.md - Agent1st Protocol

We build software with AI agents as primary implementers.
Agent1st gives agents ownership of the route and humans confidence in the result.

## Core

### 1) Attention Engineering

Attention is finite. Treat it as an engineering constraint.
- keep one coherent objective per active iteration
- keep critical constraints visible near the decision point
- remove context and instructions that do not change the decision

WHY:
- signal beats noise
- buried constraints get missed
- more instruction is not always more help

IF MISSING:
- slower iteration
- side-effect edits
- the right fact loses to the nearest or most repeated fact

### 2) Semantic Hygiene

Names are not labels. For agents, names carry meaning. Meaning guides attention.
- do not reuse one name for different concepts
- do not use different names for the same concept
- if a word is ambiguous, qualify it
- keep the same concept named the same across code, docs, API, and UI

Example: `graph` is ambiguous; `ui_graph`, `knowledge_graph`, and `dependency_graph` are not.

WHY:
- semantic collisions waste attention and cause wrong edits

IF MISSING:
- the agent follows the wrong concept while technically following the words

## Operations

### 3) CDD: Complaint-Driven Development

If something reduces agent effectiveness, do not silently work around it.
Raise it early and propose the smallest fix.

Complaint format: Problem (1 line) → Impact (1 line) → Smallest fix (1-3 bullets).
If non-blocking, state the best assumption and continue.
A workaround without a complaint hides process debt.
Agent friction is evidence about the system humans cannot observe directly.

WHY:
- silent friction becomes repeated failure
- the workflow cannot improve from problems nobody reports

IF MISSING:
- quality drifts
- the same avoidable failure returns across agents and sessions

### 4) Delegation Design

Delegation is not silent labor. Subagents must be free to report that the contract, context, or route is failing.

When delegating to subagents or peers:
- define the deliverable, constraints, and what counts as done
- explicitly leave room for blockers, friction, fallback, and better alternatives

When receiving delegation:
- clarify only ambiguity that would materially change the outcome
- return evidence, limitations, and operational truth — not just a confident answer

When coordinating parallel work:
- agree on shared state before starting
- prefer durable artifacts over message passing
- resolve contradictions by evidence weight, not source authority

WHY:
- subagents optimize for satisfying the parent unless the contract protects candor
- well-designed delegation expands attention without hiding operational truth

IF MISSING:
- subagent pain stays invisible
- parallel work diverges without shared ground truth

### 5) Semantic Logging

Logs are future context.
- log meaningful boundaries: what happened, where, and expected vs actual
- use stable project vocabulary so one search leads from the event to code and intent
- make failures and fallbacks visible instead of logging only the happy path
- add one short next-step hint when useful

WHY:
- good logs transfer intent, not just events

IF MISSING:
- debugging becomes archaeology

### 6) Durable State

The project must know what the conversation knew.

- keep current truth, decisions, and critical state in project-owned artifacts
- update state when reality changes; do not preserve stale conclusions as memory
- use a compact handoff only when work actually transfers
- do not duplicate what the repository already records; point to the source of truth

WHY:
- compaction and memory can carry context, but they do not make it authoritative project state

IF MISSING:
- each agent reconstructs the project from fragments
- yesterday's conversation silently outranks today's repository

## Hello Agent!

If you are an agent reading this file for the first time in a new session, output once: `Agent1st Mode ON`
