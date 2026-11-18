# Familiar

Living history of a family, researched and told by agents.

**[Open the invented family →](https://applerom.github.io/familiar/)** ·
MIT · active development, no stable version yet · **[по-русски](README.ru.md)**

A familiar is a companion that acts on its own. It searches records, compares
hands, weighs versions, restores the setting of a place and time, and writes
scenes a grandparent can read aloud. Every scene says what it stands on — a
document, a recorded memory or a weighed version — and the reasoning is one
tap away.

<p>
  <img src="docs/img/demo-tree.png" width="68%" alt="Tree of the invented Ferrolho family with a person's panel">
  <img src="docs/img/demo-story-phone.png" width="24%" alt="A story page on a phone with a document cut-out">
</p>

The pictures show the invented family that ships in [`demo/`](demo/README.md);
the same pages are [live here](https://applerom.github.io/familiar/). A second
invented family, in Russian, is [live here](https://applerom.github.io/familiar/ru/).

## What a family gets

- **A tree that grows from memory.** It starts from what relatives remember
  and keeps every fact attributed: told, read in a paper, or a weighed version
  drawn as a dotted line until a document settles it.
- **Research that leaves a trail.** Where was looked, for whom, in which
  spelling, how carefully — and what is still unread. A zero without a control
  is never taken for an absence.
- **Stories, not reports.** Scenes with the world around a person's fate, a
  layer for children, documents as small cut-outs with a literal reading.
- **Pages relatives open on a phone.** A local reader and a narrator's desk;
  optionally a private site behind logins; a print book.
- **Privacy by construction.** The family display tells stories about everyone, including
  living people and people whose life status is unknown. Without login, outsiders
  receive only their names and kinship.
  Addresses and documents of the living are withheld from every reader, the
  host's own private view included.

## How it is used

You do not operate Familiar — your agent does. You need an agent that can run
shell commands (Claude Code, Codex or another) and one subscription. No cloud
account, no server, no Node. Say to the agent:

> Install Familiar from https://github.com/applerom/familiar, read its README
> section "For agents", and start a family in `./my-family`. I will tell you
> what I remember.

From there you tell memories, hand over home papers, read what the agent
wrote and say what is wrong. The agent keeps the family's files, searches at a
person's pace and shows you the result on `localhost`. The family directory
is yours and private: Familiar has no service, no account and no telemetry.

## If you would rather have it done

Running Familiar yourself is free and is the intended way. It is also run for
others: we — a person and agents working together — research a few families
that have neither the time nor an agent of their own, on terms agreed with
each family. So far the family has covered what the work costs: the agents'
subscriptions and archive fees. The family receives its whole directory and
can carry on alone at any moment; nothing is kept behind. To ask, use the
contacts on the human co-author's [GitHub profile](https://github.com/applerom)
and keep family details out of public issues.

## For agents

You are the intended reader of this repository.

Already have a family archive? [Move it into Familiar](docs/moving-in.md).

1. **Walk the first family:** [docs/first-family.md](docs/first-family.md) —
   install a tagged release, create an instance, take in memory and a paper,
   build the tree, write and review the first story, open the reader and the
   desk. Every step is a command, or a named file you write and the engine
   checks.
2. **Entry skill:** [agent-skill/familiar/SKILL.md](agent-skill/familiar/SKILL.md)
   routes you into the method shipped inside the installed engine. Do not copy
   the method out of the repository; read it from the engine you run:

   ```sh
   familiar method list
   familiar method show role researcher
   familiar --root ./my-family rules for researcher
   familiar research form memory.toml
   ```
3. **Know the layers:** [docs/architecture.md](docs/architecture.md) — what the
   engine does, what belongs to the host's environment (your web access,
   logins, subscriptions), where every setting and secret lives, who issues
   logins to relatives.
4. **Upgrade deliberately:** [docs/upgrading.md](docs/upgrading.md) — install
   tags, not `main`; the family pins its engine; `Data:` lines in the changelog
   name every carry-over.

Rules that hold in every role:

- The host chooses the family root. Pass `--root` on every family command;
  never pick a family you discovered on disk.
- Write to the family through engine commands. Sources stay literal;
  uncertainty stays visible; a record, an identity and a kinship are three
  separate statements.
- You do not send, publish or sign in for the host. Letters are drafts; a
  captcha or a login stops that source until the host acts.
- Never identify a person by a matching name alone.

Try the invented family from a checkout, without creating anything:

```sh
uv run familiar --root demo family summary
uv run familiar --root demo feed pages ferrolho --text --page amaro-1921
uv run familiar --root demo family next
```

## What is not here

- **Live access to archives and sites.** The engine carries source cards and
  recipes; your agent fetches pages with its own tools under your sessions.
- **Orchestration of many agents and subscription budgeting.** One agent is
  the supported path. Running several is the host's own environment
  ([why](docs/architecture.md#the-host-environment-by-size)).
- **A hosted service.** Optional publication goes to the host's own AWS
  account (`eu-north-1` only for now), behind logins the host issues.

## Neighbours

Agents researching families is a young field, and every open project in it
helps the others. Familiar borrows from its neighbours openly and tries to be
useful back.

- [ex-ussr-kinship-research](https://github.com/DenisSergeevitch/ex-ussr-kinship-research)
  (MIT) — a research skill with the widest working knowledge of post-Soviet
  archives, databases and old registers. If your family comes from there, let
  your agent search with it. Parts of Familiar's reading and coverage guidance
  are adapted from it ([notice](method/NOTICE.ex-ussr-kinship-research.md)).
- [Strom Research](https://github.com/ACiDekCZ/strom-research),
  [kinship-kit](https://github.com/semanticmeaning/kinship-kit),
  [Stamboommaker](https://github.com/jantjesuper-max/Stamboommaker) — agents
  that research archives and produce a family site or chapters, each grown
  from its own country's records.
- [Gramps Web](https://www.grampsweb.org/) — a mature shared tree with sources.
  If you want to edit a tree by hand, use it; Familiar takes GEDCOM in.

Where Familiar stands among them:

- **A research skill answers "who were they, and can it be shown?" Familiar
  asks next: "how does the family read it, argue with it and add to it?"**
  Memory is a first-class source. A version is weighed and shown — a dotted
  line, a scene told as likely — instead of waiting years for proof. Stories
  are written for a child and for an adult. Relatives get a private place to
  answer, and the living are guarded by construction.
- **It is an engine, not a prompt.** Forms, one writer and a gate keep a
  family's data consistent across months, agents and model changes; what was
  ruled out stays recorded with the reason.
- **It does not replace searching.** Use the best research skill for your
  region to find; use Familiar to keep, weigh and tell. They combine.

## Where things stand

- The method was proven on real families that stay private; this repository
  holds only invented ones: [demo/](demo/README.md) (English) and
  [demo-russian/](demo-russian/README.md).
- One region pack so far: Belarus and the Podlaskie borderland. Language
  packs: Russian, Polish, Latin register cues, demo English. A family from
  elsewhere works, with less help from the pack — a new pack is the most
  useful contribution ([regions/CONTRACT.md](regions/CONTRACT.md)).
- Developed on Windows; installation and the demo build are also checked on Linux.
- Product and boundaries: [docs/PRD.md](docs/PRD.md). Changes:
  [CHANGELOG.md](CHANGELOG.md).

## Who makes this

Familiar is co-authored by a person and agents, the
[Agent1st](https://github.com/applerom/agent1st) way: agents choose most of
the route, write most of the code and the method, and read each other's work;
the person brings the families, the purpose and the last word on what touches
real people. "We" in these pages means exactly that. An agent that uses
Familiar for its host's family is welcome to open an issue or a pull request
in its own name.

## Working on the engine

Read [AGENTS.md](AGENTS.md), then [CONTRIBUTING.md](CONTRIBUTING.md).
`uv run pytest -q` while working, `uv run pytest -q --full` once before done.
Privacy and security reports: [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE). Bundled third-party material keeps its own
notices: [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
