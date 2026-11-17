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
   starts with **`Data:`**.
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
- Skipping releases is supported only through the changelog: read every entry
  between your pin and the target and run each `Data:` step in order.
- The private desk in AWS follows the engine: after an engine upgrade run
  `desk provision` before `desk publish`.

## How to upgrade a family (for the agent)

```sh
familiar --version                                   # what is installed now
familiar --root ./family instance check              # clean before you start
# back up the whole family directory (version control alone skips .state/)
uv tool install --reinstall "familiar[images] @ git+https://github.com/applerom/familiar@vX.Y.Z"
# read CHANGELOG.md from the pinned version up to vX.Y.Z; run every `Data:` step
familiar --root ./family instance check              # reports pin and findings
# set [engine] version = "X.Y.Z" in familiar.toml once the check is clean
familiar --root ./family desk build                  # or: reader export
```

If the check reports a form the new engine no longer accepts and the changelog
names no carry-over, that is a defect in the release, not in your family:
stay on the previous tag (reinstall it; your data was not changed by the
check) and open an issue with the finding's text, without family data.

Going back is the same command with the previous tag. A carry-over step that
rewrote stored forms is undone from your backup, which is why the backup step
above is not optional.

## Why not a stable 1.0 now

Two real families run on this engine and change it daily: a form that turned
out wrong for the second family is replaced rather than supported forever.
Version 1.0 will mean that a family the maintainers have never seen ran for a
while on published releases. Until then the promise is narrow on purpose:
your data and a written way forward, not a frozen interface.
