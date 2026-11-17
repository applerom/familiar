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

Works with Familiar **0.30 and later 0.x**. The installed engine's own role
sheets and skills are authoritative; this file only routes you to them.

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
5. Write to the family only through engine commands. Prepare inputs outside
   the family; if a required write has no command, report that gap to the host.
   Preserve literal sources, uncertainty and the distinction between a record,
   identity and kinship. Follow the installed role and skill for the actual work.

Source access and its permissions belong to the host; the wheel supplies
offline replay, not a live archive transport. Prepare messages as drafts;
the host sends them. Publication also remains the host's action. Use
`desk build` and `desk serve --port 0` for local viewing after host authorization.
