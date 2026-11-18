# Move a family archive into Familiar

Use a tagged release that offers `familiar intake photo --help`. Install the
`images` extra for photos that need clean browser copies. Ask the host for the
new private family directory and the files you may bring over. Keep a copy of
the old export and its assets, with their relative paths intact.

```sh
familiar instance init ./my-family --title "Our family" --language en
familiar --root ./my-family instance paths
```

## People, relationships and memory

- For GEDCOM, run `familiar --root ./my-family intake gedcom ./archive.ged --id archive-tree`.
  Read the loss and candidate report under `.state/intake/`. Imported tree claims
  remain hypotheses. Confirm an identity only with evidence beyond a name match.
- For a kinship spreadsheet, run `familiar --root ./my-family intake table ./relatives.xlsx --id relatives --told-by "Previous archive" --date YYYY-MM-DD --language en`.
  Review its `reading.json` cell ledger and editable `memory.toml`. Run the
  reported `intake memory` command with its frozen `--original` sheet.
- For a website or structured export, map its people and family groups into the
  `people` and `families` arrays from `familiar research form memory.toml`.
  The same shape works in JSON. Cite a memory item in each claim's `provenance`.
  Use `status: "hypothesis"` on tentative families. Preserve disputed dates
  as attributed notes and retain unplaced identity candidates in the source or
  a research version. Keep the old stable IDs in your mapping.

Map a person's summary or fact to an item with its own `id`, `person` (local
or working-tree ID), `role: "note"`, optional `label`, and literal `text`.
Set `told_by` on the telling to the previous archive. An item can override it
with `witness`. Use `strength: "hearsay"` or `status: "possible"` for uncertain
claims. Preserve original status and context in the source. Keep protected
documents and street addresses in private originals or search-only memory.

```sh
familiar --root ./my-family intake memory ./archive-memory.json --original ./archive-export.json
familiar --root ./my-family tree build --view working
```

Use `intake paper` for home papers with literal readings. Keep finished chapters,
feeds, places and timelines as source material for the writer, for example in
`inputs/story-sources/` inside the private family. The writer can adapt them into
Familiar feeds and run the normal evidence and review steps. For an existing
[kinship research workspace](moving-from-kinship-research.md), use its research import.

## Photographs

Record the host's [archive declaration](PRD.md#family-archive-declaration-pathsarchive_rights-default-familyarchive-rightsjson)
at `paths.archive_rights`, with effective `family_app` permission. Use the IDs
from the working tree. Give all identified people on each frame.

```sh
familiar --root ./my-family intake photo ./portrait.jpg --person archive-tree-i1 --caption "At the garden gate" --when "Late 1940s" --received-from "Previous archive"
familiar --root ./my-family intake photo ./photos.csv --table
```

```csv
file,people,caption,when,received_from
photos/garden.jpg,archive-tree-i1 archive-tree-i2,At the garden gate,Late 1940s,Previous archive
```

Use UTF-8 CSV or TSV. File paths may be relative to the table. Leave `when`
empty when unknown. A rejected row leaves the batch unchanged. The receipt
lists the resulting asset and original SHA-256 per row. Familiar keeps the
received file byte for byte and makes a clean display copy when needed.
The family desk shows the photograph in each identified person's Documents and
photos section and in Photos. Public views omit frames with living or unknown
subjects.

## Compare the result to the source

```sh
familiar --root ./my-family instance check
familiar --root ./my-family tree stats
familiar --root ./my-family family summary
familiar --root ./my-family desk serve --build --port 0
```

Record the [host's local desk decision](family-desk.md) before serving. Open one
person's card and the Photos page. Compare people, family groups, parent links,
note counts, photo receipts and identified people with the source. Log missing
files, unsupported roles, unplaced candidates and fields only in the original
as migration losses. For custom JSON mapping, put this accounting in `losses`
on the memory input so it appears in `.state/intake/<id>.json`. Check the source
file's hash against the archived file and share the loss summary with the host.
