<!--
START_MODULE_CONTRACT: MOD-DEMO-VERSIONS
PURPOSE: Show an open question as the method keeps it: two versions side by side, each with arguments for and against and a weight, and a share left for what nobody has thought of.
PRD_REF: docs/PRD.md#TRUST
INVARIANTS:
- weights of the versions and of the unknown sum to one, the unknown share is never zero, each version has arguments both ways and the question names its tests [review: engine lead]
CHANGES_WITH:
- MOD-DEMO-TREE (open_question on an event)
- MOD-DEMO-FEED (chapter variants point at version ids)
:END_MODULE_CONTRACT
-->
# Contract of `versions/`

One question per file, `<id>.json`: `id`, `title`, `line`, `people[]`, `status`
(open, leaning, settled, deferred), `updated`, `summary`, `unknown_weight`,
`versions[]` (`id`, `label`, `weight`, `state`: leading, alternative, weak,
refuted; `place`, `for[]` and `against[]` with `kind`, `text`, `sources[]`,
optional `reading`), `tests[]` (`text`, `where`, `would`), `advice[]`.
Optional `story_choice` names the version the story tells: `version`, `by`
(`weight`, or `interest` among versions of at least half the heaviest weight),
`basis` (one sentence), `date`. It never changes a weight.
