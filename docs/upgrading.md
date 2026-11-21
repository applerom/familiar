<!-- PURPOSE: Say honestly what stays stable while the engine changes several times a day, and how a family moves to a newer release. -->
# Stability and upgrading

Familiar is in active development. There is no stable version and none is
planned yet: `0.MINOR.PATCH`, where any MINOR may change commands, forms and
pages. The project chooses development speed over keeping old forms alive.
This page says what you can rely on anyway.

## What is promised

1. **Your inputs survive every release.** What the family told, the papers,
   the originals (kept byte for byte), records, search journals, versions and
   decisions are never invalidated by a release without a carry-over. When a
   release changes a stored form, the same release ships the command that
   carries existing data over, and the changelog entry says so on a line that
   starts with **`Data:`**. That carry-over is a step of `familiar instance
   upgrade`: one command, run after installing any newer release, carries
   every older form it finds over (and says what it changed) or names the
   file and what to decide. It never deletes a file.
2. **Everything derived can be rebuilt.** Reader exports, desk builds and
   caches are outputs. An upgrade may ask for a rebuild; it never asks you to
   re-enter anything. Not everything under `.state/` is derived:
   `.state/attestations.json` records who confirmed which page, and a new
   family's `.gitignore` leaves `.state/` out of version control. Back up the
   whole family directory, `.state/` and `.secrets/` included.
3. **A family is pinned to the release it was checked with.**
   `familiar.toml` carries `[engine] version = "0.MINOR.PATCH"`. A different
   installed engine is reported by `instance check` with both numbers; it is a
   warning, because different numbers alone do not prove incompatibility. An
   accepted input in a form the engine no longer reads stops the output that
   needs it, whatever the numbers say; working drafts and old search journals
   may stay as findings that block nothing.
4. **Published releases are tags.** `main` moves many times a day and may be
   between two steps of one change. A tag `vX.Y.Z` with a GitHub release is a
   state the maintainers' own families were actually running.

## What is not promised

- Old command names, flags, form fields, page addresses and file layouts under
  `.state/` are not kept for compatibility. There are no deprecation periods.
- Skipping releases needs no archaeology: `instance upgrade` runs every
  carry-over step, whatever release the family was on. Read the changelog
  for what changed in the pages, not for what to run.
- The private desk in AWS follows the engine: after an engine upgrade run
  `desk provision` before `desk publish`.

## How to upgrade a family (for the agent)

```sh
familiar --version                                   # what is installed now
familiar --root ./family instance check              # clean before you start
# back up the whole family directory (version control alone skips .state/)
uv tool install --reinstall "familiar[images] @ git+https://github.com/applerom/familiar@vX.Y.Z"
familiar --root ./family instance upgrade --dry-run  # what would be carried over
familiar --root ./family instance upgrade            # carry it over; names what needs a decision
familiar --root ./family instance check              # reports pin and findings
# set [engine] version = "X.Y.Z" in familiar.toml once the check is clean
familiar --root ./family desk build                  # or: reader export
```

A build or check that stops on old data names the files and the action. If it
stops on a form the new engine no longer accepts and `instance upgrade` does
not carry it over, that is a defect in the release, not in your family:
stay on the previous tag (reinstall it; your data was not changed by the
check) and open an issue with the finding's text, without family data.

Going back is the same command with the previous tag. A carry-over step that
rewrote stored forms is undone from your backup, which is why the backup step
above is not optional.

## From 0.41.3 to 0.50.0

0.41.3 was the previous published release. Back up the family directory, then:

```sh
uv tool install --reinstall "familiar[images] @ git+https://github.com/applerom/familiar@v0.50.0"
familiar --root ./family instance upgrade --dry-run  # one carry-over may be listed, see below
familiar --root ./family instance upgrade
familiar --root ./family instance check
familiar --root ./family desk build                  # or: reader export
```

Stored forms that changed, and who carries them:

- **Document pages (0.49.3).** The engine renders each document page itself
  (`sources/<id>.html`). Rows of `media/manifest.json` that registered such a
  page by hand would stop the reader build; `instance upgrade` removes those
  rows and keeps the files.
- **Everything else (0.42–0.49) only adds optional fields** — `[research]
  focus`, a `play` id in search journals, `[family].title` by language,
  `tree/translations/<lang>.json`, name forms by language, place `modern`,
  `parish`, `manor` and `coords`, `main_line` on a possible parent, probable
  merges. Old files stay valid; there is nothing to run for them.
- Outputs are rebuilt by `desk build` or `reader export`. A private desk in
  AWS needs `desk provision` before the next `desk publish`.

What you will notice after the upgrade:

- **Quarantine (0.49.0).** A contribution or a version that cites a person,
  source, record or search not committed yet no longer fails the check. It is
  listed as `QUARANTINE: file (author): waits for ...`, is not applied, and
  applies by itself once the reference is committed. A contribution that a
  full check of this family saw applied and that stops applying is still an
  error, so shown kinship is never lost quietly. The engine remembers what
  applied in `.state/contributions-applied.json`; the first full check after
  the upgrade writes it. Back it up with the rest of `.state/`.
- **Married women on the family tiles (0.47.0).** A wife now stands under her
  father's clan, named by her surname at birth; the male and female forms of
  one surname are one family, and a clan decision no longer renames a married
  woman. Some people therefore move between family tiles. A wife whose
  surname at birth is not recorded joins no family tile until it is.

## Why not a stable 1.0 now

Two real families run on this engine and change it daily: a form that turned
out wrong for the second family is replaced rather than supported forever.
Version 1.0 will mean that a family the maintainers have never seen ran for a
while on published releases. Until then the promise is narrow on purpose:
your data and a written way forward, not a frozen interface.
