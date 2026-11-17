---
name: generation-review
description: Review one bounded generation for duplicate or conflated identities, missing card evidence and anomalous links, retaining reversible decisions for independent checking.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-GENERATION-REVIEW
PURPOSE: Audit a generation without converting a convenient household arrangement into an accepted identity or deleting an unusual true link.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- a contested check can lower a version below one half or remove its lead without erasing it [review: cold reviewer]
- unusual parent dates retain literal events and the existing link until a replacement has supporting evidence [review: cold reviewer]
- accepted merges are explicit reversible decisions and every changed identity reaches an independent checker with primary inputs [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-RESEARCHER (generation review mode)
- MOD-RESEARCH-PACKET (two-stage second-look packet)
- MOD-TREE-IDENTITIES (merge acceptance and undo history)
- MOD-FAMILY-WRITER (validated mutation of family inputs)
- regions/questions.json (RP-64)
- docs/PRD.md#FORMS (case states and weighted versions)
:END_MODULE_CONTRACT
-->
# Generation review

Inputs: central person or pair, relationship radius/generation boundary,
question, current graph and decision history, case/record packet and budget.
Output: scoped inventory, decisions and remaining versions, card evidence gaps,
independent findings with owner response, and explained before/after counts.

## Order

1. Confirm the brief's people against their parents and dates before reading
   summaries. List namesakes and the selected couples, siblings and children;
   record the actual boundary if the brief confused two people. Include undated
   historical people; absent dates alone say nothing about whether someone lives.
   Preserve privacy limits on living and unknown-status people.
2. Obtain the line packet for every scoped person. Read original card notes,
   earlier family answers and literal records before case conclusions. Inspect
   the missing/omitted manifest; recover missing testimony before judging.
   Distinguish an assembled image reference from an image actually inspected.
   Compare what cases know with what cards display; stage supported missing
   claims separately from proposed identity changes.
3. Group candidate duplicates and possible conflations. Compare event intervals,
   parents, spouses, children, witnesses and places with source dependency
   groups. A shared spelling is a search key, not a merge. Two spouses can mean
   remarriage, two people or an error: do not default to one spouse. Compare
   spouse death, later marriage and children's records before choosing. Ask the
   region pack RP-64 about dates and household terms when they affect the test.
4. Open a separate weighted question for each identity or relationship. Keep
   literal dates and the existing link when flagging an anomaly. Compare event
   type, approximate dates, calendar and which parent died before a birth.
   A fourteen-year-old father and a posthumous child are test cases, not automatic
   repair instructions. Replace a link only after evidence supports the proposed
   replacement; keep the old reading and the argument for the change. Do not
   repair an unlikely chronology by manufacturing another person or spouse.
5. Record each action explicitly: merge, distinct people, split a conflation,
   revise a claim, retain as a version, or defer with a next test. A merge needs
   recorded acceptance, source references and an argument; resemblance alone is
   not an accepted merge. Change only through the validated family writer.
   Keep immutable inputs, both pre-merge cards/edges and the decision history;
   undo by withdrawing the decision and rebuilding, not editing the snapshot.
   The engine can apply recorded merges but has no dedicated decision-authoring
   or general split command; unsupported splits remain proposals to the lead.
6. Give the independent checker the scoped primary packet with --mode second-look
   at the evidence stage first. The checker records its own table and omitted
   inputs, then requests --stage argument for our decisions and weights. Submit
   every new merge, distinct-person decision, withdrawal or proposed split;
   reading-dependent arguments include inspected original images, not summaries.
   The checker returns objections with locators and strength; the owner responds:

   | Verdict | Owner action |
   |---|---|
   | correct | Record grounds and remaining uncertainty; acceptance applies only to the checked decision |
   | contested | Keep the version and conflict visible; explain a possible account and next test, then recompute all weights and ranks from evidence, including unknown; no protected lead or probability floor |
   | error | Withdraw the unsupported merge/distinction with reason and history, rebuild from unchanged inputs, and reopen affected questions |

   For example, three competing identities may receive 0.2, 0.45 and 0.15 with
   unknown 0.2 after an objection; the formerly leading contested identity may
   be the one at 0.2. Its visibility does not imply acceptance. If acceptance is
   withdrawn, remove the active merge and rebuild while retaining its history.
7. Compare the rebuilt graph with the previous inventory: people, aliases,
   parent links, moved facts and unresolved alternatives. Explain each count
   change and check affected card fields and source access. An unaccepted date
   stays a version, not a chosen display date. If a surface hides competing
   versions, record a display gap rather than strengthen a field to make it show.
   Report budget spent, case state and the next distinguishing record. No
   independent checker available means review pending, not a completed audit.

## Engine commands

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | current researcher rules, including anomaly and contested decisions | present |
| `familiar tree person` | one person's card, links, cases and records | present |
| `familiar research packet` | primary-first line packet and staged checker view | present |
| `familiar research vocabulary` | current weights, statuses and decision vocabulary | present |
| `familiar pack ask` | period/territory answer to RP-64 | present |
| `familiar tree build` | applies recorded decisions to a derived graph without altering the snapshot | present |
| `familiar tree stats` | counts and comparison against a saved graph | present |
| `familiar tree review` | proposed bounded generation inventory and duplicate/conflation queue; not built | planned |
| `familiar tree decide` | proposed validated decision editing, withdrawal and split support; not built | planned |

Until inventory tooling exists, enumerate the requested radius from the current
graph and record that manual scope. Persist supported decision proposals through
the host using `instance.writer.mutate`; leave unsupported forms as proposals.

## Ask the region pack

- RP-64: Which calendars, event-date conventions, age reporting and household or marital terms affect comparisons in this place and period, and which original records can distinguish the alternatives?

## Handoff

List scope, recovered primary inputs and remaining omissions, each decision and
reversal route, versions/weights, anomalies retained, checker/owner responses,
graph count changes and display gaps. End with what was wrong in the brief and
the tools, including recurrent classes of error rather than family-specific fixes.
