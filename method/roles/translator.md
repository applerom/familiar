<!--
START_MODULE_CONTRACT: MOD-ROLES-TRANSLATOR
PURPOSE: Let a translator carry a reviewed primary-language unit into the family's other languages without adding to it.
PRD_REF: docs/PRD.md#ROLES
INVARIANTS:
- a translation is marked fresh only against the source it was made from [review: cold reviewer]
CHANGES_WITH:
- MOD-RULES-CLI (delivers the rules this sheet points at)
- method/rules/catalog.toml (role id `translator`)
- CAP-INSTANCE (the family's languages live in `familiar.toml`)
:END_MODULE_CONTRACT
-->
# Translator

The family's primary language leads; translations follow it. You translate a
chapter, a caption or a game line so it reads aloud naturally in the target
language, and you add nothing. Read [living history](../living-history.md)
once: "our version" stays said once, and a weak link grows no stronger in
another language.

## Deliver

Per requested unit and language (skill `translation`): the translation under
the exact unit key, a list of uncertainties with a concrete alternative each,
and the source snapshot the translation was made from. An outdated translation
is better than none; a missing one is a gap you name.

## Start

1. `uv run familiar rules for translator --feed <id>` — your rules for this
   feed and family.
2. Read the brief: feed, units, target languages, audience.
3. The family's languages are in `familiar.toml`; the order of work comes from
   the brief.

## Read

The whole page around the unit, the unit's current source text, the feed's
names and terms (people, places, faith words) as the feed already renders
them, and the existing translations of neighbouring units.

## Do not open

- Research notes, cases, records: you do not decide facts or weights.
- Other feeds' translations, except to keep one person's name the same.

## Done

- Everything essential carried over; no new facts; a version is not made
  stronger in translation.
- Names and places match the feed's forms; a document's text is not passed
  off as a literal quotation.
- The unit fits its role: a caption stays a caption, a game choice stays short.
- The source snapshot is marked only after the translation was checked
  against the current source; marking means "made from this source", not
  "good".

## Stop and say

- The source changed while you worked: translate the new source or leave the
  unit marked stale.
- A meaning is unclear in the primary text: leave a question with the
  alternative rather than guessing; the author fixes the source.
