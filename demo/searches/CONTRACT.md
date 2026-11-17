<!--
START_MODULE_CONTRACT: MOD-DEMO-SEARCHES
PURPOSE: Record what was searched and what it covered, so that "not found" always says how much it is worth.
PRD_REF: docs/PRD.md#TRUST
INVARIANTS:
- an empty search states years, forms, the indexed share and a control found by the same index, and says what the absence means [review: engine lead]
CHANGES_WITH:
- MOD-DEMO-CASE (coverage table)
- docs/PRD.md#INSTANCE (searches path key)
:END_MODULE_CONTRACT
-->
# Contract of `searches/`

`searches.jsonl`, one search per line: `id`, `fictional`, `at`, `by` ({agent, model, effort}), `people[]` (tree ids searched
for), `source` (a catalogue id), `question`, `query`, `strict` (exact, contains, unknown), `control` (id of a
search that proved the index finds a known person, or null for the control
itself), `hits`, `saved[]` (record ids), `coverage` (`years`, `lists_indexed`,
`lists_total`, `forms[]`, `read`, `note`); for an empty search also `result` and
`meaning`.
