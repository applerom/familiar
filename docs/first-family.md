<!-- PURPOSE: The agent's walk from an empty directory to a family that reads its first story locally. -->
# First family: the agent's walk

This page is written for the agent. The host (the person whose family it is)
chooses the family directory, tells memories, supplies home papers and reads
the result; the agent does everything else through the commands below.
Every block works the same in sh and PowerShell unless two variants are shown.

Familiar works locally without AWS, a cloud account, orchestration tools or
Node. A family is a separate private directory with its own `familiar.toml`;
it never lives inside the engine repository.

### 1. Install the engine and choose a new family

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/) and an agent that
can run shell commands.

```sh
uv tool install "familiar[images] @ git+https://github.com/applerom/familiar@v0.30.0"
familiar --version
familiar instance init ./new-family --title "Invented example" --language en
familiar --root ./new-family instance check
```

Install a release tag, never `main`: `main` moves several times a day (see
[upgrading](upgrading.md)). The `images` extra adds Pillow for document
cropping; drop it for a text-only engine. To try a command without installing
anything: `uvx --from "git+https://github.com/applerom/familiar@v0.30.0" familiar --version`.
The name `familiar` on PyPI belongs to an unrelated project: install from this
repository.

A family that wants its own pinned engine keeps a private environment instead:

```sh
uv venv ./familiar-env
uv pip install --python ./familiar-env/bin/python "familiar[images] @ git+https://github.com/applerom/familiar@v0.30.0"
```

(`./familiar-env/Scripts/python.exe` on Windows; then call
`familiar-env/bin/familiar` or `familiar-env/Scripts/familiar.exe`.)

Use `--language ru --address informal` for Russian ты (`formal` for вы).
Russian and Polish packs are connected automatically. For English host text,
add `language_packs = { en = "demo-english" }` at the top of `familiar.toml`,
before the first table. Keep the generated family id and engine pin.
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
**invented** Bea Example: replace their contents for real work. Memory names
and events cite item ids; a paper keeps its literal reading and original.
In this example the paper's `existing="telling-bea"` identifies the person
from memory. Never identify people by a matching name alone.

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

The host supplies `home-paper.txt` (or a scan); for a practice run create an
explicitly fictional original matching the form. Originals are copied byte for
byte. An optional GEDCOM starts with `intake gedcom ./export.ged --id relatives
--living-years 110`; unsupported tags and subfields are counted as losses.
Unknown life status is protected, not silently treated as dead.

### 3. Write and actually read the first story

The agent reads role `feed-author`, the relevant story skill, and resolved
rules. It prepares `feed.json`, `chapters.json` (an array of chapter forms)
and `documents.json` (an object keyed by document id) from `research form
feed.json`, `chapters.json` and `documents.json` (the last two are complete file
containers; singular forms emit one entry). These are inputs the agent
must author, not automatically generated history. Match person aliases to the
intake ids, records to saved papers, and every claim to evidence. Use
`feed new <id>` for the skeleton; the host or family agent may edit family
inputs. The portable skill itself uses engine commands for writes and reports
any missing write command to the host. See [forms](PRD.md#forms).

```sh
familiar method show role feed-author
familiar method show skill story-text
familiar --root ./new-family rules for feed-author --feed city
familiar --root ./new-family feed new city
# Author the feed inputs, then:
familiar --root ./new-family feed build city
familiar --root ./new-family feed review city --kind reader --out ./private-review
```

```powershell
familiar method show role feed-author
familiar method show skill story-text
familiar --root ./new-family rules for feed-author --feed city
familiar --root ./new-family feed new city
# Author the feed inputs, then:
familiar --root ./new-family feed build city
familiar --root ./new-family feed review city --kind reader --out ./private-review
```

**One subscription is enough:** the agent writes; the host or another person
reads the exact review material, including tree, documents and every language,
and records the verdict. Two invented agent ids are not independent reading.
Only after that reading, substitute actual author and reader ids:

```sh
familiar --root ./new-family feed accept city --stage reading --kind reader --reviewer actual-reader --author actual-author --ticket ./private-review/review-ticket.json
familiar --root ./new-family reader export --output ./first-reader
familiar --root ./new-family reader verify --output ./first-reader
familiar --root ./new-family reader serve --output ./first-reader --port 0
```

```powershell
familiar --root ./new-family feed accept city --stage reading --kind reader --reviewer actual-reader --author actual-author --ticket ./private-review/review-ticket.json
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

Record the host's dataset decision in `family/desk-access.json` using the
[local desk instructions](family-desk.md#только-на-этом-компьютере).
Build/serve need this decision and valid family inputs, with no publication
configuration, credentials or AWS CLI:

```sh
familiar --root ./new-family desk build
familiar --root ./new-family desk serve --port 0
# Or: familiar --root ./new-family desk serve --build --port 0
```

```powershell
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
A language pack supplies wording, not search recipes. In PowerShell, use
`| Set-Content -Encoding utf8 request.json` (and `capture.json`) to save UTF-8.
Before replay, set `request.question` to a saved versions-file id, not prose
or a letter id. `research form version` gives the matching `birthplace` example;
save it as `versions/birthplace.json` after matching its people and sources.
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
feed, chapter or document forms. The forms describe an invented city family
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
