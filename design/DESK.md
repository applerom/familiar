# Family desk: the investigation as a show

The desk is a branch map of recorded work, giving the narrator confidence that
the investigation moves. Stories stay in the feed. Research agents use versions
and logs as evidence; this page is a disposable derived display.

## Investigation

Its first screen is for a relative: three plain sentences (here one sees how the search goes; what we look
for and what we found; you can help) and this family's own titles under "Looking for now", "Found lately"
and "How relatives can help". A heading without titles is not drawn. Everything below "In detail, step by
step" is the workshop and may look like one. The page is never in the lower row.

1. **What moved.** Up to four recent questions with a substantive recorded
   weight/status change. The question title, alternative label and weights come
   from the instance; ordinary UI templates supply the connective words. Within
   one research step prefer its strongest resulting alternative. No story conclusions.
2. **The whole exploration.** Counts of questions, alternatives explored,
   ruled-out alternatives, versions confirmed in the tree, and alternatives still
   in progress. Each question retains every alternative found in its selected git
   history and current file. A ruled-out alternative stays legible but muted,
   with the first safe short literal `against[].text`, when recorded. Never invent
   its reason. Accepted personal-reader people are the selection boundary;
   unaccepted people stay out, living-person labels stay generic unless they have
   a narrator-safe headline.
3. **Volume.** Total checks, distinct sources, saved records, documents in the
   reader and documents read. Read documents are saved archive/home records with
   literal reading or extracted fields, not index hits or pages. Nested records
   count too. Sheets appear only when explicitly recorded. Horizontal bars count
   checks by declared source kind; unknown kinds have their own honest label.
   Zero results and access gaps both count as work, and have separate totals.
4. **Work log.** Newest first, 24 rows per prepared portion; turning pages uses
   only the delivered data. Every fork, substantive weight/status change and
   saved record remains. Checks coalesce in recorded order by question and source
   kind, up to 60 checks per row. No hourly/day grouping. Search and git dates are
   internal ordering inputs and are discarded before delivery. No clocks, dates,
   last-visit bookmarks, speeds, deltas or time-based sparklines.
5. **Know something?** Every open question has one entry into the existing
   remark sheet with its original safe question ID, human title and page context.
   Explicit witness questions keep their answer chips and immutable inbox.

The wide page has a log and a question rail. On phones the questions precede the
log. Existing paper, ink, ember, version and act variables define the visual
language. Text wraps; alternatives and arguments never truncate.

| weight/status | word |
|---|---|
| rejected/refuted/discarded/dropped/ruled-out, or < .05 | отпала |
| .05–.2 | ослабла after a real fall ≥ .05; otherwise маловероятно |
| .2–.5 | возможно |
| .5–.9 | окрепла after a real rise; otherwise скорее всего так |
| ≥ .9 | почти наверняка |
| firm/accepted/established and supporting source in checked tree | ✓ подтвердилась |
| confirmed without a recorded source link to the checked tree | подтвердилась, связь с деревом не записана |

Colour maps a version's weight between version slate and ember; confirmed tree
versions use act green. Muted alternatives keep their labels and reasons.

## The lower row

One fixed row, static in every HTML page: at most four places with an icon and a
word (tree, relatives, stories, papers), only those the family has; `desk build`
stops at a fifth. On a phone it is 72 px plus the safe inset and holds nothing
else. On wide screens the private notice and engine version stand at its left and
Remark at its right. The quieter places (surnames, map, how the search goes, the
host's search map and letters), the remark, the notice and the version are one
static list, `#desk-more`, which the page top opens as "More". Without JavaScript
the notice stays visible above the row.

## Asks inside the show

At most three explicit witness asks are pinned above the work log until a literal
answer is saved. Each has 2–4 options plus Ask relatives and I do not know. They
use the existing sender, `kind: answer`, `ask_id` and `question`. A question's
general Know something entry sends `kind: remark`, its stable `question` and
`subject`, plus its literal title as `finding`. No graph mutation happens here.

## Building the family in the tree

- Builder mode is a quiet toggle beside the tree's own controls. Its state is
  session-only. In ordinary viewing there are no ghost relatives. The mode has
  a short hint with Done; the phone retains its reader tabs.
- Ghost places around the person in focus: son or daughter, brother or sister,
  husband or wife (always, a second marriage is possible) and father or mother
  if fewer than two. Brother/sister and spouse sit at the ends of the person's
  row, never between the person and an existing spouse; a full row moves them to
  the nearest free spot. Labels are family words, never "your" or a bare
  "parent". Long press/context menu opens the same sheet in any mode.
- The sheet "Add a relative" says one person per form and asks whose relative it
  is: any person of the tree, preselected from the entry. Far kin is that person
  plus a near relation (grandfather + brother or sister) or "other relation" in
  the narrator's own words (`kin_words`).
  It offers relations (father, mother, sibling, child, spouse, other) and plain
  fields with examples as placeholders: surname, name, patronymic, maiden name,
  birth year/place, living or died (death year/place), how it is known, a note.
  Only a name or a relation is required. After sending: received, "add another"
  with the same anchor, and a line that many people can come as a table.
- After sending, a dashed card waits for the researcher and says it appears in
  the next publication. `add_person` carries accepted `anchor`, `relation`, `new_person` and
  literal `text`. Unprocessed cards survive reload/build through `pending`;
  `reviewed_pending` clears browser copies. Neither creates an accepted person.
- An empty family starts in builder mode with seven places and the same sheet.

## `show.json` built by `familiar desk build`

```
counters: {queries, sources, sheets|null, grains, finds, documents_read}
summary: {questions, versions, dropped, firm, open}
source_counts: {archive?, index?, database?, home-paper?, website?, memory?, unknown?}
outcomes: {zero?, gap?, results?}
lanes: [{id, title, kind: tree|question, question?, open?}]
versions: [{id, lane, label, w, state: open|dropped|confirmed|firm,
            series: [numeric_weight], reason}]
shifts: [{lane, label, w_from, w_to, state, line}]
event_pages: [[{lane, kind, line, versions?, w_from?, w_to?,
                source_kind?, count?, zero?, gap?}]]
asks: [{id, lane, text, why, options: [str]}]
pending: [{id, anchor, relation, text, place}]
reviewed_pending: [id]
```

No timestamp field crosses this projection. One Git log lists relevant blob
identities and changes; one `cat-file --batch` reads the selected version blobs.
The existing writer owns output and the existing publication boundary supplies
the accepted graph. Absent git history produces current versions and recorded
volume, without fictional shifts. No agent/model call during assembly.
