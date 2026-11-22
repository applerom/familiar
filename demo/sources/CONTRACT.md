<!--
START_MODULE_CONTRACT: MOD-DEMO-SERIES
PURPOSE: List the invented record series of the islands, so the demo's search map shows what of the open record was read.
PRD_REF: docs/PRD.md#INSTANCE
INVARIANTS:
- every series is invented; its online copy and archive are invented names [review: engine lead]
CHANGES_WITH:
- MOD-SEARCH-MAP (series form)
- MOD-DEMO-SEARCHES (rows that name a series and depth)
:END_MODULE_CONTRACT
-->
# Contract of `sources/`

`series.json`: `{"series": [...]}`, one record series a row: `id`, `kind`, `place`, `years`, optional `title`,
`lines`, `holder`, `missing`, `online` (`source`, `years`, `access`), `note`. Form: `research form series`.
