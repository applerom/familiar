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

- For GEDCOM of the family's own tree, run `familiar --root ./my-family intake gedcom ./archive.ged --id archive-tree --own`.
  `--own` says the tree is what this family itself holds: its people and kinship
  come in as the family's word, drawn with solid lines. Without `--own` the file is
  someone else's tree and every claim is a hypothesis until research supports it.
  Read the loss and candidate report under `.state/intake/`.
- For a kinship spreadsheet, run `familiar --root ./my-family intake table ./relatives.xlsx --id relatives --told-by "Previous archive" --date YYYY-MM-DD --language en`.
  Review its `reading.json` cell ledger and editable `memory.toml`. Run the
  reported `intake memory` command with its frozen `--original` sheet.
  The first nonempty row is the header. When the headers are not the bundled
  ones (the run answers `No person column`), name the columns before the first
  run in a small TOML file and pass `--mapping columns.toml`:
  `columns."Sheet1!A" = "person"`, with roles `person`, `person_kin`, `kin`,
  `birth`, `death`, `birth_place`, `death_place`, `place`, `notes`, `witness`,
  `living`. A rejected draft keeps its `--id`; give the next attempt a new one.
- For a website or structured export, map its people and family groups into the
  `people` and `families` arrays from `familiar research form memory.toml`.
  The same shape works in JSON. Cite a memory item in each claim's `provenance`.
  Keep the old stable IDs in your mapping.

**The family's own knowledge stays firm.** What the old archive holds as known
(a status such as "family", "confirmed", or no status at all) is firm family
memory: `strength: "firm"`, no `status`. The family is at home here, not in
court, and its tree must not arrive as a page of dotted lines and "possibly".
Mark `status: "hypothesis"` or `strength: "hearsay"` only where the old archive
itself doubted: a candidate, a disputed date, a question mark. Preserve such
doubts as attributed notes and keep unplaced identity candidates in the source
or a research version. Never merge two people by a matching name alone.

Map a person's summary or fact to an item with its own `id`, `person` (local
or working-tree ID), `role: "note"`, optional `label`, and literal `text`.
Set `told_by` on the telling to the relative who kept the archive, or to the
archive when no teller is known. An item can override it with `witness`. Use
`strength: "hearsay"` or `status: "possible"` only for claims the archive
itself marks as uncertain. Preserve original status and context in the source. Keep protected
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

The host declares once that the family holds its photographs. Write the
host's own words into `family/archive-rights.json` (the "Family archive
declaration" paragraph of `docs/PRD.md` has every field):

```json
{"schema_version": 1, "kind": "family-photograph",
 "holder": "The family of ...", "declared_by": "Host's name",
 "declared_at": "YYYY-MM-DD", "effective_from": "YYYY-MM-DD",
 "living_subject_consent": false,
 "permissions": {"family_app": true, "processing": false, "colourisation": false}}
```

Use the person IDs of the working tree: `familiar --root ./my-family tree stats`
and `tree person` list them. A GEDCOM pointer keeps its letters as written, so
`@I1@` imported with `--id archive-tree` is `archive-tree-I1`. Give all
identified people on each frame.

```sh
familiar --root ./my-family intake photo ./portrait.jpg --person archive-tree-I1 --caption "At the garden gate" --when "Late 1940s" --received-from "Previous archive"
familiar --root ./my-family intake photo ./photos.csv --table
```

```csv
file,people,caption,when,received_from
photos/garden.jpg,archive-tree-I1 archive-tree-I2,At the garden gate,Late 1940s,Previous archive
```

Use UTF-8 CSV or TSV. File paths may be relative to the table. Leave `when`
empty when unknown. A rejected row leaves the batch unchanged. The receipt
lists the resulting asset and original SHA-256 per row. Familiar keeps the
received file byte for byte and makes a clean display copy when needed.
The family desk shows the photograph in each identified person's Documents and
photos section and in Photos. Public views omit frames with living or unknown
subjects.

A photograph leads the card of each person on it. On a group frame, mark where
each named face is, as fractions of the picture's width and height
(`x,y,width,height`); the card and the tree then show that face. A print
re-shot by phone can show only the print with `--crop`; the original stays
whole and opens one tap further. Both can be added later by running the command
again on the original file with nothing else:

```sh
familiar --root ./my-family intake photo ./portrait.jpg --face archive-tree-I1=0.12,0.30,0.25,0.18 --face archive-tree-I2=0.58,0.33,0.25,0.18 --crop 0,0.25,1,0.5
```

In a table, use the optional columns `faces` (`ID=x,y,w,h;ID=x,y,w,h`) and `crop`.

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
