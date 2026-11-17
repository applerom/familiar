<!--
START_MODULE_CONTRACT: MOD-DEMO-CONCEPT
PURPOSE: Say on one page who the invented family is, what it remembers and what it does not know, so an agent with no other family in mind can start from it.
PRD_REF: docs/PRD.md#USE-CASES
INVARIANTS:
- the family is openly invented: places, people and papers exist nowhere outside this directory [review: engine lead]
- the family is ordinary: no famous person, event or place carries the story [review: engine lead]
- the page names firm memory, hearsay, the one home paper, the one open question and its two versions [review: cold reviewer]
- no file of the family carries a mark of a real family by form: Cyrillic, pilot paths, xref ids, rule-book or service ids [review: engine lead]
- no data id carries Cyrillic [review: engine lead]
- every data file says in its own header that it was invented [review: engine lead]
CHANGES_WITH:
- MOD-DEMO-CONFIG (title and fictional flag)
- MOD-DEMO-VERSIONS (the open question)
- docs/PRD.md#INSTANCE
:END_MODULE_CONTRACT
-->
# The Ferrolho family — an invented family for the Familiar demo

**Everything in this directory is invented.** The island, the villages, the
town, the ship, the parish, the people and every paper were made up for the
demo. No archive holds these records and no person here lived. The family is
an instance like any other: the engine opens it with `--root demo`.

## Who

Three generations of an ordinary family of mill workers.

| Generation | People | Where |
|---|---|---|
| 1 | Amaro Ferrolho (about 1898 – 1968) and Rosa Calhau (about 1902 – 1981); Amaro's mother Joaquina stays behind | born on Ilha Vaqueira, an invented island in the Atlantic where records are kept in Portuguese; Amaro sails in 1921 |
| 2 | Helena Ferrolho (1925 – 1999), married Walter Pike (died 1990) | Quarry Bend, an invented mill town on a New England river; records in English |
| 3 | Daniel Pike, living — the host of this instance | only his name and kinship are recorded |

## What the family knows

- **Firm memory** (the host saw it or heard it from his mother many times):
  grandfather Amaro came from "the islands" and worked forty years in the
  cotton mill; grandmother Rosa kept a garden of kale and never learned to
  read; Helena was born in Quarry Bend; the years of death of Amaro, Rosa,
  Helena and Walter.
- **Hearsay** ("my mother used to say"): Rosa came over "to marry Amaro",
  from "somewhere near his village"; Amaro was born in 1899.
- **One home paper:** Helena's baptism certificate of 1925 from the parish of
  the Holy Ghost in Quarry Bend. It names Amaro "native of Lajedo do Vento"
  and Rosa "native of Ponta d[...]": the end of the word is lost in the fold.
- **One archive record:** line 14 of the passenger list of the SS Santa
  Ludovina, 1921: Amaro, 23, labourer, going to his cousin Manuel Tavares.
  The same Manuel Tavares is the godfather on Helena's certificate.

## The open question

Where was Rosa Calhau born? Two versions stand side by side
(`versions/rosa-birthplace.json`):

- **Ponta do Moinho**, the only "Ponta d…" parish on Ilha Vaqueira, an hour's
  walk from Amaro's village — 0.50. It fits the hearsay and the torn word.
- **Ponta das Garças** on the neighbouring Ilha Alvarinha — 0.30. It fits the
  length of the torn word better, and her surname is common there.
- Something not yet found — 0.20.

A search of the arrivals index for Rosa found nothing, with its coverage
stated (`searches/searches.jsonl`); the next test is her death certificate,
which a living relative can request.

## Map of the instance

| Path | Holds |
|---|---|
| `familiar.toml` | the family root; `fictional = true` |
| `tree/snapshot/` | people and families, every fact with its provenance |
| `family/` | the host's memory as told, privacy list |
| `records/` | the home paper and the archive record as literal readings |
| `versions/` | the open question with two weighted versions |
| `cases/` | the case of the line: claims, coverage, next test |
| `searches/` | what was searched and what it covered, including "not found" |
| `tree/evidence.json` | sources and the links they carry |
| `feeds/ferrolho/` | one feed with two chapters |

Directories of JSON carry a `CONTRACT.md` next to the data: JSON cannot hold
a comment, so the contract of the directory lives beside it.
