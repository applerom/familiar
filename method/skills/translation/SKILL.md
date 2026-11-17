---
name: translation
description: Translate a chapter, caption or game unit into the family's requested languages while tracking source freshness and literal evidence boundaries.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-TRANSLATION
PURPOSE: Carry a reviewed unit across family languages without certifying an outdated or only partly checked translation row.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- advancing a shared source snapshot requires rechecking every populated target in that row [review: cold reviewer]
- literal readings and source name forms have a different translation disposition from explanatory prose [review: cold reviewer]
- source agreement, target-language judgement and pipeline acceptance are separate checks [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-TRANSLATOR (unit and language brief)
- MOD-FEED-TRANSLATIONS (unit keys and shared _source snapshot)
- MOD-FEED-CLI (translation stage acceptance)
- MOD-INSTANCE-PACKS (language-tag keyed packs)
- regions/questions.json (RP-60)
- docs/PRD.md#FORMS (translation and publication surfaces)
:END_MODULE_CONTRACT
-->
# Translation

Inputs: feed, exact unit keys, current source text and page context, existing
translations, audience, family language configuration and target-language pack.
Output: proposed target strings by key, the exact source used, uncertainties,
review results, and separate lists of missing and stale units.

## Order

1. Read the family's `source_language` and `languages`; the primary language
   leads. Take requested target order from the brief, otherwise use the family
   list order with the source removed. Do not assume a fixed number of languages
   or treat the first language in a list as the source. An unconfigured target
   is a configuration question, not permission to invent another edition.
2. Read the whole page, then capture the exact current source of each unit.
   Include titles, narrative, More, children's text, document explanations,
   picture captions and game questions/options/consequences/truth. Obtain names
   from feed data; consult the target language pack for RP-60. Keep an unresolved
   term with alternatives for the source author, rather than research new facts.
3. Classify the unit before translating:

   | Material | Disposition |
   |---|---|
   | Narrative, More, caption, game text | Translate meaning, degree of doubt and age register; read aloud in context |
   | Literal record reading, including uncertain letters | Keep the original reading unchanged; put a labelled explanatory translation beside it only on a declared surface |
   | Name in the form written by the source | Keep that form in quotations/readings; use an established target display form in narrative, never silently replace the source form |
   | Unit key, person id, document locator | Keep identifiers unchanged |

4. Compare source and target for omissions, time, kinship, negation, weights
   and reconstruction disclosure. The translator checks source agreement; a
   target-language reviewer checks natural speech, name forms and ambiguous
   terms. One person may do both checks if competent, recording that limitation.
   Return unclear meaning to the source author. A quality judgement does not
   establish historical identity or strengthen a version.
5. Save a proposal through the host's validated family writer. Chapter units
   belong in `translations.json`; picture captions and game language rows belong
   in their own catalogs. Preserve the exact engine unit key, including catalog
   JSON-pointer keys. The current engine stores one `_source` per unit row,
   shared by all targets. Advance it only after every populated target has been
   checked against that same current source. If one target is still old, keep
   the old snapshot and report the whole row stale; a fresh target may then be
   conservatively reported stale too. Do not clear another language's warning.
6. Re-read the source immediately before committing. A changed source makes the
   proposal stale until compared again. Keep a usable old translation with its
   stale mark; a missing translation stays missing, not fresh by fallback.
   Inspect status and build output. Record remaining gaps and reviewers; only
   then may the responsible role accept the translation stage. Acceptance
   records a review, while a snapshot records dependency freshness.
   A partial requested batch leaves the whole-feed stage pending until all
   required units and languages are reviewed; the current acceptance command
   has no per-unit translation scope.

## Engine commands

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | resolved translator rules for the feed | present |
| `familiar feed status` | per-language missing/stale counts and source unit keys | present |
| `familiar feed build` | checked materialized feed; not a language-quality verdict | present |
| `familiar feed accept` | records the completed translation review with --stage translation | present |
| `familiar feed translate` | proposed unit editing, per-target snapshot marking and review support; not built | planned |
| `familiar pack language` | proposed language-pack question lookup; current pack ask routes region answers | planned |

Until editing support exists, hand the proposal to the host using
`instance.writer.mutate`; do not write family files through an ad hoc serializer.
Read the configured language pack directly for RP-60; absence is a declared gap.
Per-target freshness cannot currently be represented by a shared snapshot.
The current reader export refuses stale translations; preserving an old row
does not promise that it can be delivered as a labelled stale reader edition.

## Ask the region pack

- RP-60: Which target-language name forms, transliteration choices and period or faith terms apply to a translated unit, and which meanings need a first-use explanation?

RP-60 belongs to the language pack keyed by target tag, rather than to the
departure region. Report missing answers to that pack's keeper.

## Handoff

List completed keys and targets, checked source, missing/stale targets, unresolved
alternatives, reviewer and stage state. Include what was wrong in the brief and
the tools. A trial stays a proposal and receives no stage acceptance.
