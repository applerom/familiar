---
name: game
description: Design one small child-readable chapter activity from a visible picture or supported scene, with answer support and every choice resolved.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-GAME
PURPOSE: Turn a chapter's observable detail or decision into a playable activity whose answer does not acquire invented historical authority.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- each activity separates support for its answer from what it may claim about history [review: cold reviewer]
- every offered choice has an outcome and a route to the truth note [review: cold reviewer]
- picture-dependent answers require inspection and are reopened when the picture changes [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-FEED-AUTHOR (game mode)
- MOD-FEED-TRANSLATIONS (play catalog units)
- MOD-PUBLICATION (game reader surfaces are not yet declared)
- MOD-FEED-CLI (review state)
- docs/PRD.md#FORMS (future interactive content form)
:END_MODULE_CONTRACT
-->
# Chapter game

Inputs: one chapter and its More, the actual picture and caption if relevant,
the evidence it already uses, reader age and the family's choice about games.
Output: a small design proposal with answer locators, all outcomes, a truth note
and a review record. A game is optional; stop when the page offers no fair task.

## Order

1. Choose one observation or decision the child can understand from this page.
   Respect the family's game setting and age; try the instruction aloud without
   the research dossier. A sensitive page may need a quiet observation or no
   game. Do not score a family's loss or make a wrong answer shame the reader.
2. Choose a form by what supports the answer:

   | Form | Required support | What an answer establishes |
   |---|---|---|
   | Find a detail | Inspected final picture, precise visible feature and location | The feature is in this drawing; not proof it existed in the ancestor's home |
   | Read a clue | Inspected local document crop and the chapter's explanation | What the marked field says, keeping unreadable parts unresolved |
   | Choose an action | Supported situation in the chapter and a consequence for each option | A way to explore the scene; only a cited record can establish the historical choice |

   A prompt describing a picture is not inspection. If a feature is absent or
   ambiguous, change the task or await another image; never invent a hidden
   object and declare it found.
3. Write a short title, introduction and one question at a time. Offer two or
   three distinguishable choices when using a choice game. Resolve every choice
   with understandable feedback and a route to the truth note; allow retry or
   finish, with no penalty. A reward is optional and adds no family fact.
4. Write the truth note before testing the fun. Name whether the support is a
   document, the chapter's reconstruction or the drawing. Keep source locators
   in the private design record. In the reader note distinguish the historical
   observation from imagined alternatives: trying an option does not mean the
   ancestor chose it. A question with no supported answer is redesigned.
5. Walk every path, including an unexpected answer. Read aloud at the configured
   age; a child should find the answer without another page. Have the reviewer
   inspect the picture-dependent answer and check sensitive content, truth note
   and the translated choices. A picture, text, answer or outcome change reopens
   this review and dependent translation checks.
6. Hand on the design and current dependency locators. The engine currently
   scans language rows in `play.json` for translation freshness, but has no game
   form, game path validator or declared game reader projection. Do not treat a
   clean feed build or --stage connect acceptance as a playable-game verdict.
   Keep the proposal private until the supported writer and reader path exists.

## Design specimen

This is a fictional review aid, not an executable game schema:

```text
{
  "kind": "choose-action",
  "question": "How could the traveller carry the address?",
  "support": {"kind": "document", "locator": "record:arrival#destination", "observed": "An address is written in the destination field"},
  "choices": [
    {"id": "paper", "label": "Carry a note", "outcome": "A note can be read again.", "next": "truth"},
    {"id": "memory", "label": "Remember it", "outcome": "A remembered address can be forgotten.", "next": "truth"}
  ],
  "truth": {"id": "truth", "text": "The list gives an address. It does not say whether the traveller carried a note."}
}
```

## Engine commands

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | resolved feed-author rules and reader settings | present |
| `familiar feed status` | dependency and review state, not game playability | present |
| `familiar feed check` | feed findings, not traversal of game paths | present |
| `familiar feed game` | proposed typed game authoring, path check and reader hookup; not built | planned |

## Handoff

Name form, age, answer basis, inspected image if any, all paths tried, reviewer,
translation dependencies and the implementation gap. Include what was wrong in
the brief and the tools. No game acceptance is claimed for a design proposal.
