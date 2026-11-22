<!--
START_MODULE_CONTRACT: MOD-DEMO-MEMORY
PURPOSE: Keep what the host told at the start as separate statements, each marked firm or hearsay, so research can tell a fact from a lead.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- every memory item is either firm or hearsay and says how the teller knows it [review: engine lead]
CHANGES_WITH:
- MOD-DEMO-TREE (memory ids are provenance there)
- docs/PRD.md#INSTANCE (answers and privacy path keys)
:END_MODULE_CONTRACT
-->
# Contract of `family/`

- `memory/memory-<date>.json`: one telling by the host. `id`, `kind` = memory,
  `told_by`, `date`, `items[]` with `id`, `text`, `strength` (firm, hearsay) and
  `witness` (how the teller could know it: saw it, heard it, holds the paper).
- `privacy.json`: `closed_topics[]`, `living[]` (objects with id, allowed[] and consent {by, at}; null consent and empty allowed mean name and kinship only), `living_rule`.
  Named by the setting `privacy.closed_topics_file` in `familiar.toml`.
- `horizons.json`: `lines{}` keyed by line name — a line nobody in the family can be asked
  about any more: `since`, `by`, optional `known` (what is known indirectly) and `reopen_when`.
  Written by `family horizon close|open`; the demo closes Rosa's own line, Calhau.
