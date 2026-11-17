<!--
START_MODULE_CONTRACT: MOD-DEMO-TREE
PURPOSE: Hold the invented people, families and the links between them in the normalised shape a real family's intake will produce, so engine code can be tested on them.
PRD_REF: docs/PRD.md#INSTANCE
INVARIANTS:
- ids are opaque lowercase ASCII and every family member and evidence edge resolves to a person [review: engine lead]
- every name, event and note names its ground: a memory item, a document or the host [review: engine lead]
- a fact under an open question keeps its place empty and points at the question [review: engine lead]
- a living person carries only a name and kinship [review: engine lead]
CHANGES_WITH:
- MOD-DEMO-RECORDS (document ids used as provenance)
- MOD-DEMO-MEMORY (memory ids used as provenance)
- docs/PRD.md#INSTANCE (tree_snapshot and evidence path keys)
:END_MODULE_CONTRACT
-->
# Contract of `tree/`

JSON cannot carry a comment, so the contract of this directory lives here.

- `snapshot/people.json`: `{"_about", "fictional", "people": [person]}`. A person is
  `id`, `sex`, `living`, `names[]` (`given`, `surname`, `type`: birth, married,
  as-written; `provenance[]`), `events[]` (`type`, `date` as text, `place` or null,
  `provenance[]`, optional `note`, optional `open_question`), `notes[]` (`text`,
  `provenance[]`).
- `snapshot/families.json`: `{"families": [family]}`; a family is `id`, `husband`,
  `wife` (person id or null), `children[]`, `events[]`, `provenance[]`.
- `evidence.json`: `sources[]` (`id`, `kind`, `record` path from the family root),
  `edges[]` (`type`, `from`, `to`, `sources[]`, `confidence`: same, probable,
  possible), `remove_edges[]`, `research[]`.
- Provenance values: a record id, a memory item id, or `host` for what the host
  says about themselves.
