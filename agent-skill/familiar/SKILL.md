---
name: familiar
description: Research and tell a family's history through an installed Familiar engine, using its role sheets, skills, rules and checked family commands.
---
<!--
START_MODULE_CONTRACT: MOD-AGENT-SKILL
PURPOSE: Route an outside agent into the installed Familiar method without copying it or choosing a family.
PRD_REF: docs/PRD.md#ROLES
INVARIANTS:
- the host chooses the family and retains source access, outgoing communication and publication [review: cold reviewer]
CHANGES_WITH:
- MOD-METHOD-CLI (installed method commands)
:END_MODULE_CONTRACT
-->
# Familiar

Checked with Familiar **0.30 to 0.32**. Commands may change in any later
0.x release: with another version, read the entry skill shipped beside that
release. The installed engine's own role sheets and skills are authoritative;
this file only routes you to them.

1. Run `familiar --version`. If the engine is absent, install a tagged release
   (`docs/first-family.md` in the repository). If the family's `familiar.toml`
   pins another version, report the mismatch before writing family data.
2. Obtain the explicit family root from the host. Never select a discovered
   family yourself. Use `--root <family-root>` on every family command.
3. Run `familiar method list`. Read the assigned role with
   `familiar method show role <id>` and only the needed skill with
   `familiar method show skill <id>` from this installed release.
4. Read `familiar --root <family-root> rules for <role>` (add `--feed <id>`
   for feed-specific work), then inspect `instance paths` and the task's forms.
5. Take memory, papers, tables and decisions in through engine commands.
   Inputs you author as whole files — a feed's `feed.json`, `chapters.json`
   and `documents.json`, a versions file, the desk decision, the engine pin in
   `familiar.toml` — are written where `instance paths` and the form say, and
   checked at once with `instance check`. Never edit by hand what the engine
   derives: `tree/snapshot`, `.state/`, builds and exports. If a write has
   neither a command nor a form, report that gap to the host.
   Preserve literal sources, uncertainty and the distinction between a record,
   identity and kinship. Follow the installed role and skill for the actual work.

Source access and its permissions belong to the host; the wheel supplies
offline replay, not a live archive transport. Prepare messages as drafts;
the host sends them. Publication also remains the host's action. Use
`desk build` and `desk serve --port 0` for local viewing after host authorization.
