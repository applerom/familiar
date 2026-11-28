<!--
START_MODULE_CONTRACT: MOD-DEMO-FEED
PURPOSE: Show how three fictional chapter strips become a desk feed with draft frames, a cut, a route and an open choice.
PRD_REF: docs/PRD.md#USE-CASES
INVARIANTS:
- every person symbol, document, cut-out and flow position of a chapter resolves [review: engine lead]
- each chapter has a story text, a "More" list marking what the story supposes, and a "For children" block [review: cold reviewer]
- each cut draws on a literal field of an invented record [review: engine lead]
- the story tells scenes from the documents and "More" names what each scene stands on, judged by the reviewer role [review: reviewer]
CHANGES_WITH:
- MOD-DEMO-RECORDS (record paths in documents.json)
- MOD-DEMO-VERSIONS (variant ids)
- docs/PRD.md#PIPELINE
:END_MODULE_CONTRACT
-->
# Contract of `feeds/ferrolho/`

Edit `studio/chapters/NN-slug.md`, then run `familiar --root demo feed chapters ferrolho`.
Use `familiar --root demo feed storyboard ferrolho` for a phone-width reading with strips.
The fictional desk shows the frames that still need a picture.

- `feed.json`: `id`, `title`, `lead` (ends with the invented mark), `period`,
  `line`, `cover` (null: no pictures), `people[]` (symbols), `profile` (`anchor`,
  `readers`, `kids`, `pictures`, `depth`, `languages`, `games`, `names`), `parts[]`,
  `gens[]` (`name`, `years`, `ids[]` symbols), `persons` (symbol to person id).
- `chapters.json`: a list of chapters: `id`, `year`, `part`, `title`, `kind`,
  `people[]`, `text` (paragraphs split by a blank line), `more` ("- " lines),
  `ask` (the "For children" block), `picture`, `records[]` (`doc`, `title`,
  `pick[]` cut-out indexes), `flow[]` (`after` paragraph, `record` index),
  `facts[]`, `variants[]` (`title`, `text`, `more`, `version`: question/version),
  `places[]` (`name`, `note`, `map` or null).
- `documents.json`: document id to `fictional`, `record` (path from the family
  root), `caption` (starts with "Invented"), `full` (null), `source`, `where`,
  `snippets[]` (`asset`: null, `field`, `read`).
