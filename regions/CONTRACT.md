<!--
START_MODULE_CONTRACT: MOD-REGION-CONTRACT
PURPOSE: Say what any region or language pack must be able to answer, in which file and shape each answer lies, and what a pack may never hold, so that a family can take a pack without taking another family.
PRD_REF: docs/PRD.md#LAYERS
INVARIANTS:
- the question list here is driven by what roles and skills ask, not by the files the pilot happens to have [review: engine lead]
- every record shape named here is the shape the engine and the pack integrity checks read [review: pack keeper]
CHANGES_WITH:
- docs/PRD.md#ARCH (pack.toml and the region_packs list)
- docs/PRD.md#INSTANCE (what is not in the instance)
- docs/PRD.md#RULES-MODEL (pack.toml is a layer file of the cascade)
- MOD-SKILL-MEMORY-FIRST (asks RP-1 to RP-5 by id)
- MOD-ROLES-RECIPE-SEARCHER (recipes and source cards)
- MOD-ROLES-SHOT-DIRECTOR (daily-life reference by question)
:END_MODULE_CONTRACT
-->
# Region pack contract, version 1

A pack is the detachable knowledge of a place or of a language: true for any
family from there, and empty of every family. Two families from one region
share a pack; a family from elsewhere swaps it. Product scope:
`docs/PRD.md#REGION-PACK`; this file specifies the record shapes.

## 1. What a pack answers

### Reader kinship vocabulary

Language packs may declare `[reader_kinship] file = "kinship.json"`. The bundled
Russian, Polish and English tables are imported into the data-free shell at
build time; changing them requires the ordinary shell rebuild, not a network
fetch. They contain no family examples. This is bundled-shell vocabulary;
runtime replacement from a family's custom pack is not implemented.

The JSON object contains `title`, `intro`, `all`, `archaic`, `maybe`, `path`, `groups`, `terms`, `labels`,
`fallback` and `genitive`. A term has a unique stable `id`, `word`, short
`explanation`, group key, optional `archaic: true` and a `match` array of
semantic descriptors. All fields of a descriptor must match; alternatives are
OR. Most specific descriptors precede broad ones. Descriptors use `kind`,
`n1` (viewer to common ancestor), `n2` (target to common ancestor), `g`,
`viewerG`, `branchG`, `collateralG`, `viaSpouse`, `spouseOf`, `spouseG` and
`special`; genders are `m`, `f` or unknown. Empty `viaSpouse`, `spouseOf`
and `special` explicitly exclude affinity and specialised links.

Packs name parents, children, spouses, siblings, ancestors/descendants through
eight generations, cousins through sixth cousin, representative removed cousins,
uncles/aunts, nephews/nieces and their grandchildren; affinity covers a child's
spouse, spouse's parents/siblings, sibling's spouse, co-parents-in-law and
husbands of sisters. Russian distinguishes сноха (son's wife to his father)
from невестка; Polish distinguishes stryj/wuj and marks świekr/świekra historical;
English uses its own cousin numbering and “-in-law”. Polish cousin degrees here
are genealogical cousin numbering, not statutory degrees of consanguinity.

The dictionary also defines half, step and spiritual kinship. A half relation
requires both parent pairs with exactly one common parent. Explicit directed
associations `godparent` and `step_parent` run from child to adult; inverses
are godchild and stepchild. `step_sibling` and `coparent` are symmetric explicit
associations. `coparent` here means spiritual kinship (кум/кума), not a civil
parenthood assertion. Missing parentage or baptism alone supplies none of them.

No exact match retains a generation/relationship description, including unknown
gender. Historical wording keeps its explanation. Uncertainty is independent
of the chosen term. The glossary reads only the checked reader graph, offers
no example for a missing or hidden person, and never changes relationship facts.

The contract starts from the questions a researcher, a writer and a drawer
ask, not from files.

| # | Question | Kind of answer | File |
|---|---|---|---|
| Q1 | Which sources exist for this place and these years, and what does each cover? | data | `sources.toml` |
| Q2 | How do I reach a source: open, sign-in by the host, request, paid; which pace; which recipe? | data, recipe id | `sources.toml`, later `recipes/` |
| Q3 | How does a source read a zero, and how much of its catalogue is indexed? | data with text | `sources.toml` (`zero`, `coverage`) |
| Q4 | Where is a record of this class and year kept now, who may ask for it, and for how long is it closed? | data | `custody.toml` |
| Q5 | Which fields did a certificate or register entry carry in each decade? | data | `custody.toml` (`form`) |
| Q6 | Which calendar, border, administration and language of records applied in this year? | data | `chronology.toml` |
| Q7 | How were names, surnames and places written here in each alphabet and period? | data (dictionary) | `variants.toml` (queued) |
| Q8 | What did a house, a road, a uniform, a church look like here in this decade? | text for the agent, with sources and licences | `reference/` (queued) |
| Q9 | The numbered questions of engine skills (RP-1 ...) | text for the agent, every line with a status | `answers.md` |

Kinds: **data** is read by code and by agents; **text for the agent** is read
by a role by question, never whole; a **recipe** is read by a search tool and
names the readiness and zero signals of one site. A recipe without a source
record is not allowed; a source without a recipe is normal.

For coverage planning, a source's `years`, `countries` and optional `regions`
describe suitability. Optional `[[coverage.places]]` in `sources.toml` connects
`aliases = ["written place"]` to `countries = ["CC"]` and/or `regions = ["id"]`.
List every plausible country for an ambiguous historical borderland. Missing
geography stays unknown; these aliases do not establish a person's birthplace.

## 2. Files

```
<pack>/
  pack.toml        identity, kind, coverage, files, proper names, gaps; settings and modes
  sources.toml     [[source]]: Q1-Q3
  custody.toml     [[custody]] and [[form]]: Q4-Q5
  chronology.toml  [[calendar]], [[border]], [[record_language]]: Q6
  answers.md       one section per skill question id: Q9
  variants.toml    shared name and place forms (queued)
  recipes/         one file per site recipe (queued)
  reference/       daily-life reference by place and decade (queued)
```

Only `pack.toml` is required. A missing file is a gap and is declared in
`[[gap]]`; it never reads as "nothing exists".

### pack.toml

```toml
schema_version = 1

[pack]
id = "<stable id>"
kind = "region"            # region | language
title = "<for people>"
version = "<semver>"
updated = 2026-11-12
countries = ["BY"]         # ISO 3166-1 alpha-2 of the countries the territory lies in today
territory = "<the area in words>"
years = [1795, 2026]       # the span the pack speaks for
record_languages = ["ru"]  # BCP-47 tags of the records of the territory (language packs read them)
files = { sources = "sources.toml" }
answers = ["RP-1"]         # skill question ids answered in answers.md

[[gap]]                    # what the pack knows it lacks
what = "<missing piece>"
next = "<who or what fills it>"

[proper_names]             # every capitalised name the pack uses, by kind
place = []
institution = []
publication = []
term = []

[settings]                 # cascade layer: region values of declared settings
[modes]                    # cascade layer: region modes of declared rules
```

### Status of every claim

Every record of `sources.toml`, `custody.toml`, `chronology.toml` and every
bullet of `answers.md` carries one status:

| Status | Means | Needs |
|---|---|---|
| `verified` | an agent saw the page, the law text or the working search on `checked` | `checked` date and `basis`: what was seen |
| `reported` | from a secondary page, a search snippet or a note not rechecked | `basis`; `checked` if a date is known |
| `unverified` | general knowledge or a candidate | `basis`; must be checked before a letter or a "not found" rests on it |

A mixed card incorporating an outside observation is `reported`; its `basis`
lists the observations with their dates and whose observations they are.

A "verified" claim older than a year is read as "reported". In `answers.md`
the status is a tag at the end of the bullet: `[verified 2026-11-12]`,
`[reported]`, `[unverified]`, followed by references `(source: id; custody: id)`.

### sources.toml

```toml
[[source]]
id = "spachyn"                  # unique within the pack and across loaded packs
title = "Spachyn"
kind = "index"                  # index | archive | registry | library | finding-aid | reference
classes = ["cemetery"]          # vocabulary below; reviewed by the pack keeper
countries = ["BY"]
years = [1900, 2026]
holds = "<what is in it>"
domains = ["spachyn.by"]        # empty for an institution reached by letter
access = "open"                 # open | host-login | request | paid | closed
how = "<how to ask it: form, parameters, wait>"
zero = "<how a zero reads, and when a zero is not a zero>"
coverage = "<indexed share against its catalogue, when known>"
site_limits = "<what the site itself publishes about load>"
paid = "<paid routes, listed as options only>"
recipe = ""                     # id of a recipe in recipes/, empty when none
status = "verified"
checked = 2026-11-12
basis = "<what was seen>"
```

`source.years = []` means **years unknown**, never an empty collection. It
requires a `[[gap]]` in `pack.toml` naming the source id and what coverage must
be established. Source selection by year retains that candidate and labels it
«годы неизвестны»; no invented wide interval may stand in for missing years.
The pack's own `years` remains its declared territory/time scope.

Optional `source.born = [first, last]` is the inclusive birth cohort for
coverage planning. Only a known, disjoint personal birth window excludes a cell.

Optional coverage-planning fields: `search_languages` (BCP-47), `search_scripts`
(`Latn`, `Cyrl`), `search_language_eras` (`{years = [start, end], languages = [...]}`),
`parishes` and `episodes` (applicable aliases). `planning_requires = "parish"` or
`"episode"` with `planning_terms` marks new suggestions as unestablished until
the person's local context provides a relevant clue. These are planning hints,
never guarantees of indexed coverage. Unknown hints never invent an exclusion.

Optional `communities` (`jewish`, `christian`) marks a base that holds only one
community's records. The search map counts it as a hole only for a line whose
people's records name that community (a faith, a rite, a parish or a baptism);
another community makes it unfit, none recorded makes its fit unknown.

For place forms, `holder_country` names the country of the keeper. The
`countries` array still describes the territory covered by the collection.
Use `catalogue_languages` and `catalogue_scripts` when place-name lookup in
the catalogue differs from the collection's `search_languages` or `search_scripts`.

The source-class vocabulary lives here: `address-book`, `archive-guide`,
`award`, `cemetery`, `census-revision`, `civil-register`, `emigration`, `forum`,
`forced-labour`, `inventory`, `law`, `map`, `military`, `newspaper`,
`parish-register`, `personnel-file`, `place-reference`, `record-keeper`, `repression`,
`village-council`. Add a class here with a keeper-reviewed use, not in a test.

Pace is not a pack value. The pack states what the site publishes
(`site_limits`); the host's shared ledger decides the pace for all families of
one host.

### custody.toml

`[[custody]]`: `id`, `country`, `classes`, `years`, `kept_by` (source ids),
`then` (where it goes after the term), `closed` (closure in words, with the
article), `who_may_ask`, `statute`, status fields.
`[[form]]`: `id`, `country`, `document`, `years`, `carries` (fields always
present), `not_guaranteed` (fields one would expect and may not find),
status fields.

### chronology.toml

`[[calendar]]`, `[[border]]`, `[[record_language]]`: `id`, `countries`,
`years`, `text`, status fields; a record language also has `languages`
(BCP-47) and `script`.

## 3. What a pack may never hold

- a person, a family, a case, a version, a decision, a search of a family or
  the coverage of such a search;
- an id, a path or a file-level archive reference that only one family needs:
  a pack names collections and fonds, not files of one family's people;
- a village chosen because a family lived there; a pack speaks of countries,
  provinces, districts, towns and institutions;
- a ranking of sources by their value for one family's lines.

A family's correction to a pack is a proposal to the pack's keeper, never a
write into an installed pack.

`instance.packs.load_packs` resolves identities and kinds, confines referenced
file paths and rejects duplicate source ids across loaded region packs.
`question_coverage` reports exact registered answers and explicit/implicit gaps.
Loading is not a complete schema, historical, access or privacy audit.
The pack keeper reviews required fields, classes, dates, unknown-year gaps,
source/custody/recipe references, proper-name declarations, prohibited family
content, provenance and rights. This includes disguised surnames, family facts
without names and a selection that mirrors one family's research.

Own pack code and text use the repository's MIT licence. Contributions must
identify provenance and third-party rights; retained third-party notices and
licence texts travel with the detachable pack. Pack `version` uses semver:
MINOR for added answers, sources or changed meaning; PATCH for corrections
without a new answer or shape. The keeper reviews a fictional consumer before
acceptance; neither loading nor rules/instance checks attest live websites.

## 4. Region and language

Two kinds of one mechanism. A **region pack** knows a territory: sources,
custody, calendars, borders, which languages its records are written in, and
the forms of its places. A **language pack** knows a language: gendered and
case forms of surnames, transliteration tables, word lists of the voice and
plain-language checks, words of faith and daily life with their first-use
explanation. The region pack points at languages through `record_languages`;
it never carries their grammar.

A language pack may also provide a top-level `[host]` table for plain host
wording: request letters, page labels, confirmation explanation, next actions
and summary sections. Values are literal text templates; placeholders name
only the supplied fragment (such as `{paper}` or `{question}`), never an object
attribute or an index. The English, Polish and Russian tables shipped here enumerate
the keys and share their placeholder sets (pack keeper review).
These templates supply no family facts, automatic translation, regional paper
formats or linguistic-check coverage. Missing keys are reported as pack gaps;
there is no fallback language or invented courtesy formula.

`[host]` is the formal/default wording. `[host_informal]` overrides only keys
that change for `host.address = "informal"`; the merged key and placeholder
contract is identical in all three packs. `[host_format]` declares
`address_forms`, twelve `months` in date context, `plural_default`, and ordered
`[[host_format.plurals]]` rules (`category`, integer `values`, optional `modulo`
and `except_mod100`). First matching rule wins, otherwise the default category.
The `date` template takes `{day}`, `{month}`, `{year}`; `days_<category>` takes
`{days}`.
Only valid exact ISO dates are formatted; partial or approximate
dates remain verbatim. These are integer count forms, not a general grammar
engine or calendar conversion. English declares no grammatical T/V distinction;
Polish declares no inferred gendered title or automatic vocative. Request
`call_as` is supplied ready to print and is never declined by code.

Composition: `region_packs` is an ordered list (later wins on settings; source
ids must be unique across packs, a repeated id is a load error); language packs
are keyed by language tag, one per tag, and a language pack is applied only to
text in its language. Questions are answered by the region pack whose
`countries` and `years` cover the place and year asked; answers are never
merged across packs.

## Numbered questions

`questions.json` is the registry of question ids, wording and requesting skills.
Declare a question there once before adding a skill reference. Each pack must
answer registered questions or declare gaps. A registered question without an answer or a declared gap is an implicit gap, shown by the engine; adding a question never requires editing every pack. Question ids match exactly (RP-3 differs from RP-31).
`pack ask RP-n --country CC --year YYYY` prints the selected region answer
and its referenced source cards, filtered by country and known year spans.
`pack ask RP-n --language TAG` reads only the explicitly selected language
pack; a missing language is a visible gap, never a fallback. Language answers
use the same registered ids, statuses and `answers.md` shape.

Calendar conversion requires an explicit input style; pack prose is context,
not an automatic decision about a register. Church seasons need pack data.
