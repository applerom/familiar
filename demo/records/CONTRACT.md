<!--
START_MODULE_CONTRACT: MOD-DEMO-RECORDS
PURPOSE: Give the invented home paper and archive record as literal readings, marked invented at the record itself, so no tool or reader can take them for real papers.
PRD_REF: docs/PRD.md#TRUST
INVARIANTS:
- every record is marked fictional, says it was invented and has no image [review: engine lead]
- every field is read into the reading verbatim and every torn or doubtful field has a doubt note [review: engine lead]
CHANGES_WITH:
- MOD-DEMO-FEED (documents.json points at these files)
- docs/PRD.md#INSTANCE (records path key; home papers have no key of their own yet)
:END_MODULE_CONTRACT
-->
# Contract of `records/`

One JSON per document; a subdirectory per kind (`home/`, `passenger-lists/`).

`id`, `fictional`, `kind` (home-paper, archive-record), `title`, `source` (`kind`;
`holder` and `received` for a home paper, `collection`, `archive_ref`, `fetched_at`
and `by` for an archive record; `image`: always null here; `invented`: the sentence
a reader sees), `language[]`, `fields` (field name as printed, value literally,
`[?]` for a doubtful letter, `[...]` for a lost part), `reading` (the whole text
literally), `doubt[]` (`field`, `text`), `people` or `person` / `relatives` /
`events`, `match` (`tree_id`, `confidence`, `note`), `privacy`.
