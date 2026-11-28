# Feed studio: carrying chapter files into a feed

The writer's method is `method/skills/story-scenario/SKILL.md`; it states the
chapter file layout. This page holds the mechanics around it.

## Commands

`familiar feed chapters <id>` imports the studio strips into the feed's
catalogs; `familiar feed storyboard <id> --out <file.html>` renders a private
phone-width reading page with the strips. Run from the family root or pass
`--root FAMILY`. Both read `feeds/<id>/studio/chapters/`.

- `--studio PATH` chooses another studio inside the family.
- `--source-ref REF` reads the chapter files, import settings and image lists
  from a family commit.
- `feed chapters --out DIR` writes draft catalogs to a separate directory for
  inspection; without `--out` it updates the feed.
- `feed storyboard` renders the chapters already written while the rest are
  still coming.

## The chapter file

Write `T`, `L`, `R` and `D` lines in screen order; one `picture:` opens the
chapter. Fields split on " | ", paths start at the family root, and each
answer follows its option's position. An open choice can finish with what
the family still seeks. An `R:` line with `file=`, `caption=` and `reading=`
makes an openable cut. Add `record=` to tie it to its corpus record, or use
the linkage already held in the media registry. Each file can carry its own
caption and reading, even for cuts of the same record. A cut without a corpus
record stays in the home projection and needs historical subject attribution.
Its file may be a registered export or a local PNG, JPEG or WebP. The archive
locator goes under More. Legacy strips
without a caption import with a file-and-line note and an empty caption.
Keep `id:` when changing a file's slug so
facts, places and stored translations keep their chapter; without it the
identifier comes from the slug.

## `studio/import.json`

The feed's `feed.json` supplies the title and lead. Optional
`studio/import.json` sets:

- `parts`: start chapter number to part title;
- `chapter_count`: when the full sequence is expected;
- `cuts`: corpus record id to registered media export (the researcher adds
  it when a kept frame becomes a cut);
- `exports`: studio file to registered media export;
- `mentions`: person id to `[chapter numbers or ids, pattern]`. A matching
  passage puts the person's chip under the chapter, and the reader's
  "For whom?" choice shows the kinship of that person to whoever reads.

Existing image lists and per-feed credits can be read there. The storyboard
accepts available chapters even when the planned sequence is incomplete.

## The reader's pass

Step 9 of the method. One reader who wrote none of the feed opens
`feed storyboard` at 390 px, reads it whole in "Adults" and "Kids" as the
owner would read aloud to a seven-year-old, then chapter by chapter, and
asks of each:

1. **True?** A sentence a sceptical adult stops at: a link too neat, a
   coincidence told as a link, a number without a ground, a general fact of
   the epoch dressed as this village's. The facts were checked; the reader
   looks for a true fact used to suggest an untrue thing.
2. **About us?** Swap in the neighbouring surname or village: does the title,
   game or paragraph still fit? And the opposite: a chapter with no family in
   it, a lecture on the place.
3. **Who is speaking?** Weights, "version", "we are still looking" beyond what
   the story bears; a sheet or a scribe as the subject; a warning or a verdict
   where the house should speak as a home.
4. **Bored?** Three abstractions in a row, a paragraph that only connects, a
   game that quizzes the paragraph just read, a picture that repeats it.
5. **Kin and names.** One person named two ways across the feeds, a word from
   the wrong seat, a living person told beyond name and kinship, anything in
   an in-law's line that reads as a question to that family.
6. **The whole.** A wonder or a war repeated across the family's feeds; the
   one chapter the child would ask for twice and the one skipped.

The reader hands in a table and changes no chapter:

| Chapter | Sentence or beat, quoted | Question | What to do, a line | How sure |
|---|---|---|---|---|

"How sure" is *certainly* (the owner stops here), *probably* or *taste*. The
writer carries out *certainly*, carries out *probably* unless one line says
why not, decides *taste*, and keeps a ledger: the line, done or not and why.
