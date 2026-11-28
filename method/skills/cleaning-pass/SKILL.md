---
name: cleaning-pass
description: Cut a family's standing documents back to what an agent is sent to today - delete the dead, rewrite the living as state. Run on a rhythm, not when it hurts.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-CLEANING-PASS
PURPOSE: Keep the files agents read at their start short and true, against the agents' own habit of adding.
PRD_REF: docs/PRD.md#ROLES
INVARIANTS:
- the pass deletes and rewrites; it builds no checker, counter, index or archive [review: cold reviewer]
- nothing that guards people is lost [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-LEAD (who runs the pass and when)
- method/rules/catalog.toml (PROC-STATE-IN-PLACE, PROC-CLEANING-PASS)
:END_MODULE_CONTRACT
-->
# Cleaning pass

Agents do the work, so the standing files are the workplace. We add and do
not delete: a new note feels safe, a deletion feels like a risk. That habit
is trained in and no instruction removes it, so the files grow and dead
instructions pile up until the workplace hinders the work. The answer is a
rhythm, not vigilance: **this pass, every week of work and before a broad
wave.** Deleting is safe here: git keeps every line.

## The live chain

An agent is sent along one chain: his brief, the house's entry sheet, the
rules of his role (`familiar rules for <role>`), the family's state files the
brief names, the tools. A standing file is alive if that chain, a tool's
code, or a page the family reads leads to it. Establish this by reading the
chain and searching for the file's name, not by its date or tone.

## The pass

1. List the standing documents: instructions, plans, protocols, "current
   state" notes. Not data: reports of dated work, versions, records, captures,
   letters and the family's inputs are the record and stay.
2. Dead file: delete it. If it holds one thing that still bites and lives
   nowhere else, move that thing, in a line or two, to the living file where
   an agent would look. No archive folder, no stub saying where it went.
3. Living file: rewrite it whole as state. What is true now and what to do
   next, in the order needed. A rule is a line or two with its reason. What
   happened, when and who said it belongs to git and the reports. What the
   engine already gives the role is one line saying where. One home per thing.
4. Mend links and paths that pointed at the deleted.
5. Commit with a subject starting `Cleaning pass:` so the next lead can see
   when it was last done.

Kept in every pass: privacy of the living, the manners of the sources, what
is never done, who may publish and send. Unsure whether a rule still bites:
keep it as one line. Unsure whether a file is alive and no chain leads to it:
it is dead.

## What to tell the lead

Sizes before and after; what was deleted; what moved from the dead to the
living; and which habit of upkeep made each pile grow, so the brief or the
hand-in that feeds it can be changed.
