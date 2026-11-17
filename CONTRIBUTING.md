# Contributing

Familiar is built and used through agents, and most changes here are made by
agents under a maintainer's direction. Contributions from people and from
agents are both welcome; the rules are the same.

## Before anything else

- **No real family data, ever** — not in issues, pull requests, tests,
  screenshots or commit messages. Reproduce on the invented families in
  `demo/` and `demo-russian/`. If a defect shows only on your family, describe
  its shape (form, counts, the finding's text) with names replaced.
- Read [AGENTS.md](AGENTS.md) (engine work rules) and
  [docs/architecture.md](docs/architecture.md) (what belongs in the engine and
  what belongs to the host environment).
- The project is in active development with no stable version
  ([docs/upgrading.md](docs/upgrading.md)). A pull request may be
  re-implemented instead of merged when the code around it has moved; you will
  be told, and credited.

## Issues

Use the complaint form — it is short and it is what gets fixed:

```
Problem: one line.
Impact: one line — what the family or the agent could not do.
Smallest fix: one to three bullets, if you see one.
```

Friction an agent met is a valid issue even when a workaround exists.
Security and privacy defects go through [SECURITY.md](SECURITY.md), not
through public issues.

## Pull requests

- One coherent change. A behaviour fix is not a stricter check: do not add
  tests that only pin the current surface (see the test budget in
  `AGENTS.md`).
- A change to a stored family form ships with the command that carries
  existing data over, and a `Data:` line in `CHANGELOG.md`.
- Before asking for review: `uv run pytest -q --full` once.
- Commit messages in English. If an agent wrote the change, name the model in
  a `Co-Authored-By:` trailer.

## Region and language packs

A pack is the most useful thing an outsider can add: source cards, recipes
and name variants for a region the maintainers do not know. The contract is
[regions/CONTRACT.md](regions/CONTRACT.md). Every source card states what it
rests on (`basis`) and when it was read; unknown years stay unknown. Do not
copy a site's text or data: describe the source in your own words and link it.

## Licence of contributions

The project's own code, method and packs are MIT. By contributing you confirm
that you have the right to submit the material and that it is offered under
MIT. Bundled third-party material stays under its own licence — the fonts,
for example, are under the SIL Open Font License — and keeps its notice: add
it to `THIRD_PARTY_NOTICES.txt` or the pack's `NOTICE.md` in the same change.
