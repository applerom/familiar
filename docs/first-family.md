<!-- PURPOSE: The agent's walk from an empty directory to a family that reads its first story locally. -->
# First family: the agent's walk

This page is written for the agent. The host (the person whose family it is)
chooses the family directory, tells memories, supplies home papers and reads
the result; the agent uses the commands below and authors the explicitly named
input files. Engine-generated snapshots, originals and review marks are written
only through commands.
Every block works the same in sh and PowerShell unless two variants are shown.

Familiar works locally without AWS, a cloud account, orchestration tools or
Node. A family is a separate private directory with its own `familiar.toml`;
it never lives inside the engine repository.

### 1. Install the engine and choose a new family

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/) and an agent that
can run shell commands.

```sh
uv tool install "familiar[images] @ git+https://github.com/applerom/familiar@v0.33.0"
familiar --version
familiar instance init ./new-family --title "Invented example" --language en
familiar --root ./new-family instance check
```

Install a release tag, never `main`: `main` moves several times a day (see
[upgrading](upgrading.md)). The `images` extra adds Pillow for document
cropping; drop it for a text-only engine. To try a command without installing
anything: `uvx --from "git+https://github.com/applerom/familiar@v0.33.0" familiar --version`.
The name `familiar` on PyPI belongs to an unrelated project: install from this
repository.

A family that wants its own pinned engine keeps a private environment instead:

```sh
uv venv ./familiar-env
uv pip install --python ./familiar-env/bin/python "familiar[images] @ git+https://github.com/applerom/familiar@v0.33.0"
```

(`./familiar-env/Scripts/python.exe` on Windows; then call
`familiar-env/bin/familiar` or `familiar-env/Scripts/familiar.exe`.)

Use `--language ru --address informal` for Russian ты (`formal` for вы).
Russian and Polish packs are connected automatically. For English host text,
add `language_packs = { en = "demo-english" }` at the top of `familiar.toml`,
before the first table. Keep the generated family id and engine pin.
Save `familiar.toml` as UTF-8 without a byte-order mark (BOM).
Put the family directory under its own **private** version control and back it
up: it is the only copy of what the family told and what was found.

No `[publication]` section is needed. Its default is `target = "none"`.
Installation does not authorize an agent to choose or change a real family.

### 2. Give the agent its method and attributed inputs

The host chooses the explicit family root. The portable entry skill is
[`agent-skill/familiar/SKILL.md`](../agent-skill/familiar/SKILL.md); it routes an
outside agent to the installed method without copying it. To read the method:

```sh
familiar method list
familiar method show role researcher
familiar method show skill memory-first
familiar --root ./new-family rules for researcher
familiar research form memory.toml > memory.toml
familiar research form paper.toml > paper.toml
```

```powershell
familiar method list
familiar method show role researcher
familiar method show skill memory-first
familiar --root ./new-family rules for researcher
familiar research form memory.toml | Set-Content -Encoding utf8 memory.toml
familiar research form paper.toml | Set-Content -Encoding utf8 paper.toml
```

`method list/show` reads only bundled resources by identifier, with no family
lookup or maintenance. Family rules require the explicitly selected root.
The agent fills the forms from the host's memory and a home paper, retaining
literal words, attribution and uncertainty. The supplied forms describe an
**invented** Bea Example (1880–1955) and her spouse Ben (1878–1952): replace
their contents for real work. Both are deceased; the paper belongs to Bea,
so this practice run needs no living-person document permission. Memory names
and events cite item ids; a paper keeps its literal reading and original.
In this example the paper's `existing="bea-telling-bea-person"` identifies the person
from memory. Never identify people by a matching name alone.

The host supplies `home-paper.txt` (or a scan). For this entirely fictional
practice run, the agent first writes that file beside `memory.toml` with the
exact line `Name: Bea Example`:

```sh
printf 'Name: Bea Example\n' > home-paper.txt
```

```powershell
'Name: Bea Example' | Set-Content -Encoding utf8 home-paper.txt
```

The line is the complete invented original; the form preserves its literal
reading. For real work, never create an original to fit a form.

```sh
familiar --root ./new-family intake memory ./memory.toml
familiar --root ./new-family intake paper ./paper.toml --original ./home-paper.txt
familiar --root ./new-family instance paths
familiar --root ./new-family instance check
familiar --root ./new-family tree build
```

```powershell
familiar --root ./new-family intake memory ./memory.toml
familiar --root ./new-family intake paper ./paper.toml --original ./home-paper.txt
familiar --root ./new-family instance paths
familiar --root ./new-family instance check
familiar --root ./new-family tree build
```

Originals are copied byte for byte. An optional GEDCOM starts with
`intake gedcom ./export.ged --id relatives
--living-years 110`; unsupported tags and subfields are counted as losses.
Unknown life status is protected, not silently treated as dead.

### 3. Write and actually read the first story

The agent reads role `feed-author`, the relevant story skill, and resolved
rules. `feed new bea-city` creates the skeleton. The agent then **writes files**:
`feed.json`, `chapters.json` (an array) and `documents.json` (an object keyed by
document id) under `./new-family/feeds/bea-city/`. There is no command for
authoring their contents. The commands below save the bundled forms to those
exact input paths; they are complete and mutually consistent for this invented
practice family. For real work the agent authors their contents from evidence,
matching person aliases to intake ids and record references to saved papers.
Singular `chapter.json` and `document.json` forms emit one entry, not the complete
file containers. See [forms](PRD.md#forms).

```sh
familiar method show role feed-author
familiar method show skill story-text
familiar --root ./new-family rules for feed-author --feed bea-city
familiar --root ./new-family feed new bea-city
familiar research form feed.json > ./new-family/feeds/bea-city/feed.json
familiar research form chapters.json > ./new-family/feeds/bea-city/chapters.json
familiar research form documents.json > ./new-family/feeds/bea-city/documents.json
familiar --root ./new-family instance check
familiar --root ./new-family feed build bea-city
familiar --root ./new-family feed review bea-city --kind reader --out ./private-review
familiar --root ./new-family family summary
familiar --root ./new-family family next
```

```powershell
familiar method show role feed-author
familiar method show skill story-text
familiar --root ./new-family rules for feed-author --feed bea-city
familiar --root ./new-family feed new bea-city
[IO.File]::WriteAllLines("$PWD/new-family/feeds/bea-city/feed.json", (familiar research form feed.json), [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllLines("$PWD/new-family/feeds/bea-city/chapters.json", (familiar research form chapters.json), [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllLines("$PWD/new-family/feeds/bea-city/documents.json", (familiar research form documents.json), [Text.UTF8Encoding]::new($false))
familiar --root ./new-family instance check
familiar --root ./new-family feed build bea-city
familiar --root ./new-family feed review bea-city --kind reader --out ./private-review
familiar --root ./new-family family summary
familiar --root ./new-family family next
```

`instance check` checks the authored inputs; `feed build` checks mechanical trust
before writing output. The review command writes the material for reading and
`./private-review/review-ticket.json`. Stop here until someone has actually read
it; the summary and next step may still name pending reading.
The PowerShell file writes use UTF-8 without BOM on both Windows PowerShell 5
and PowerShell 7; `Set-Content -Encoding utf8` adds a BOM on version 5 and must
not be used for these JSON inputs.

Identifiers such as `bea-city`, `bea-first` and `bea-paper` deliberately include
the example's name and a hyphen. Ordinary words such as `city`, `first` and
`paper` remain ordinary prose even if they also name a research item. Explicit
working references are hidden with a notice; the remaining text stays visible.

**One subscription is enough:** the agent writes; the host or another person
reads the exact review material, including tree, documents and every language,
and records the verdict. Two invented agent ids are not independent reading.
Only after that reading, substitute actual author and reader ids:

```sh
familiar --root ./new-family feed accept bea-city --stage reading --kind reader --reviewer actual-reader --author actual-author --ticket ./private-review/review-ticket.json
familiar --root ./new-family reader export --output ./first-reader
familiar --root ./new-family reader verify --output ./first-reader
familiar --root ./new-family reader serve --output ./first-reader --port 0
```

```powershell
familiar --root ./new-family feed accept bea-city --stage reading --kind reader --reviewer actual-reader --author actual-author --ticket ./private-review/review-ticket.json
familiar --root ./new-family reader export --output ./first-reader
familiar --root ./new-family reader verify --output ./first-reader
familiar --root ./new-family reader serve --output ./first-reader --port 0
```

Open the printed loopback address. `--port 0` chooses a free port; **Ctrl+C**
stops the server. The wheel supplies the rendered reader shell; Node is not
needed. A pending/stale review stays a labelled preview and ordinary export
refuses it. Living-person prose needs review and its public fields/permissions;
a local personal view has a separate scope:

```sh
familiar --root ./new-family reader export --host-private --output ./private-reader
familiar --root ./new-family reader verify --output ./private-reader
familiar --root ./new-family reader serve --host-private --output ./private-reader --port 0
```

```powershell
familiar --root ./new-family reader export --host-private --output ./private-reader
familiar --root ./new-family reader verify --output ./private-reader
familiar --root ./new-family reader serve --host-private --output ./private-reader --port 0
```

Verification detects the private scope itself: it has **no `--host-private`
flag**. Use a separate export directory. Personal viewing is not a public
release; see [reader delivery](reader-export.md) and [the gate](gate.md).

### 4. Open the local narrator desk

After the host makes the dataset decision, the agent **writes**
`./new-family/family/desk-access.json` using the JSON form in the
[local desk instructions](family-desk.md#только-на-этом-компьютере), with
`family.id` from `./new-family/familiar.toml` and the host's actual decision.
There is no authoring command for this file. Run `instance check` below, then
`desk build` to check the decision and build the permitted personal view.
Build/serve need this decision and valid family inputs, with no publication
configuration, credentials or AWS CLI:

```sh
familiar --root ./new-family instance check
familiar --root ./new-family desk build
familiar --root ./new-family desk serve --port 0
# Or: familiar --root ./new-family desk serve --build --port 0
```

```powershell
familiar --root ./new-family instance check
familiar --root ./new-family desk build
familiar --root ./new-family desk serve --port 0
# Or: familiar --root ./new-family desk serve --build --port 0
```

Open the printed address; stop with **Ctrl+C**. Local feedback goes straight to
the family's inbox and never automatically becomes accepted memory.
[Optional AWS publication](family-desk.md#публикация-в-aws-по-выбору-хозяина)
is a separate host action, enabled only by explicit `target = "aws"`.

## Search and host responsibilities

The installed wheel can replay a **saved capture** with explicit opt-in:

```sh
familiar research form search-request > request.json
familiar research form capture > capture.json
familiar --root ./new-family research replay --request request.json --capture capture.json --allow-replay
```

These are complete fictional examples for Geneteka; declare
`region_packs = ["belarus-podlasie"]` at the top level of `familiar.toml`.
A language pack supplies wording, not search recipes. In PowerShell, save JSON
without BOM as above, for example
`[IO.File]::WriteAllLines("$PWD/request.json", (familiar research form search-request), [Text.UTF8Encoding]::new($false))`
(and the same for `capture.json` using form `capture`).
Before replay, set `request.question` to a saved versions-file id, not prose
or a letter id. `research form version` gives the matching `bea-birthplace` example;
save it as `versions/bea-birthplace.json` after matching its people and sources.
The engine does not supply a live archive transport. The host environment supplies live
access, sessions, permissions and source limits. A challenge or refusal stops
that source; an unread response is never negative evidence. See
[bounded source search](PRD.md#bounded-source-search-and-host-access).
Mail stays a draft for the host to send. The host also controls publication.

After `feed accept --kind reader`, text pages and `family summary` explicitly
show confirmed reader pages alongside the separate feed view's pending reading.
Different projections need their own confirmation; changing the reader's shown
bytes or safety inputs invalidates that confirmation.

Mechanical checks protect references, privacy, acceptance and output bytes;
historical truth, prose and pictures still require real reading. Addresses,
living-person documents and generated pictures of living people/children are
excluded from reader delivery. See [error routes](gate-error-routes.md).

## Installed working slice

Install `familiar[images]` for document cropping (the `images` extra installs
Pillow). The base engine works without image processing.
Run `familiar research form memory.toml` or `paper.toml` for intake templates;
`familiar research form NAME.json` prints memory, request, search, version, case,
feed, chapter or document forms. The forms describe the invented Bea and Ben Example family
and are exercised together from a wheel outside the checkout.
The `.json` suffix may be omitted; TOML forms keep their explicit suffix.

Ordinary `feed build` refuses blocking mechanical trust findings before writing
output. Human historical, prose subject-completeness and visual review remain
necessary. `published_fields` declares the subjects and fields actually shown;
name and kinship need no consent, additional living fields need recorded consent.
Permissions and restricted-vocabulary bytes invalidate previous review marks.
A build produces JSON catalogues, not a rendered reader page or a publication.

## Text for the family

For a story author's source discovery, `familiar --root ./family research person
"Bea Example"` gathers a bounded private card with relatives, candidate records,
competing versions and local copies. Declare scattered collections in
`familiar.toml`; trial them read-only with `--catalog FILE`. Coverage, privacy
closures and reading-budget omissions are explicit. See
[the person-card contract](PRD.md#person-card).

From the checkout, try the invented family:

```powershell
uv run familiar --root demo family requests --text
uv run familiar --root demo feed pages ferrolho --text --page amaro-1921
uv run familiar --root demo family confirmation
uv run familiar --root demo family next
uv run familiar --root demo family summary
```

These commands read the family through the gate and print plain text without
changing its data. A request is ready for the host to forward; the engine does
not send it. A story's first line says whether an independent reader confirmed
the current page. Living-subject story prose is withheld on this minimal surface.
The next step uses the recorded request, answer and case state; an unchanged
wait stays a wait. The summary keeps papers, testimony and open questions apart.

Host wording comes from the family's source-language pack. Bundled
`demo-english` and `pl` supply it; declare, for example,
`language_packs = { en = "demo-english" }` before `[family]` in an English
family's configuration. Missing templates are reported as a language-pack gap,
without guessing a translation. Family prose and names stay as recorded.

A Russian family starts with `familiar instance init ./family --language ru --address informal`
(ты; use `formal` for вы). The shipped language pack is connected automatically.
The second openly fictional family and repeatable first-week walk are in
[demo-russian/README.md](../demo-russian/README.md).

A family sent a table: run `familiar intake table relatives.xlsx --id relatives --told-by host --date YYYY-MM-DD --language ru`.
Review `.state/intake/table-relatives/memory.toml` beside `reading.json` (Kin Sheet 1).
Then run `familiar intake memory .state/intake/table-relatives/memory.toml --original .state/intake/table-relatives/original.xlsx`.
Check labelled cards and questions before sharing; disable unsupported kin proposals
with `enabled=false`. Obtain research permission using
`research form research-permission.json`; save it at `family/research-permission.json`.
