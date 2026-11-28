# Changelog

## 0.67.2 — 28 November 2026

- We keep questions and games tied to their papers. The public packet scan
  catches dates in digits and words and distinctive words from withheld labels.
  An independent reading still covers an author's free retelling.
- We show described frames on the signed-in family desk while the pictures are
  being drawn. Public feeds and reader exports still require finished frames.

## 0.67.1 — 28 November 2026

- We keep diagnostics, input paths and review records out of public packets.
  The gate scans the delivered files for wording from withheld papers.
- The reader shows placed cuts in both modes by default. The children's
  setting can hide papers and the crop limit covers the whole chapter.
- Data: Upgrade names incomplete studio sets. Installed chapter IDs and
  expected counts protect the catalogue. Compare with `feed chapters --out DIR`
  before confirming a removal with `--allow-remove-chapters`.
- Data: Upgrade names citations to temporary files. Use `instance keep-citations
  --dry-run` and then `instance keep-citations` to keep the files. Missing
  paths and archive locators keep their original wording.

## 0.67.0 — 28 November 2026

- We import the numbered chapters the studio holds. The storyboard uses the
  studio plan, highlights words in paper readings and accepts a host path map
  for original photographs kept outside the family.
- Data: The studio counts numbered files. In 0.67.1, we check existing
  expected counts and installed chapter IDs before replacing the catalogue.
- A desk built from a separate Git checkout names the feed and other authored
  inputs it excludes. A chapter import points out very wide paper cuts.
- We identify temporary paths cited in records and search journals.
  `instance keep-citations` keeps the bytes in the family captures directory
  and updates their locators.
- Data: The transfer is explicit and leaves missing files in place. In 0.67.1,
  it also preserves archive locators.
- Instance checks share the host media projection across feeds. Each public
  feed still goes through its own projection and media checks.

## 0.66.1 — 28 November 2026

- A feed is made in the order its first whole use showed. After the fact
  check, a reader goes through the whole feed as the family will and says
  which chapters live, which are dead and which sentences to keep word for
  word; then one writer mends the whole around what lives, and a short check
  covers only what the mending added. The check had passed a dead chapter in
  every feed. The family first sees a rough whole feed, with described frames
  where pictures are wanted; nothing is drawn before it reads.
- A person without a paper is still told, but in a chapter he holds. A
  chapter filled by a neighbour's memory, the place or the war merges into
  its neighbour or leaves the feed, and the person waits in "More" or under
  "waiting for a paper" in the plan. A feed opens and closes on people the
  family itself remembers; possible kin stand inside, named so at once.
- The cast gives each person's age at each event, the family's people left
  outside it, and cuts already cropped to their line. The table of shared
  events carries gestures too, so two feeds do not tell the same waiting.
- The scenario method answers its open questions: a namesake below 0.3 is a
  neighbour, never a hero; one "our version" a link; weights multiply along
  a chain; a hero with no choice turns on what he held on to; "ask
  grandmother" only where the family said she lives. `feed rhythm` advises
  on a chapter above 330 words instead of 200.

## 0.66.0 — 28 November 2026

- We show dated archival papers beyond the family horizon in home chapters.
  Their own participants govern access. Outside readers keep the existing
  document protections.
- Children can open the cuts placed in the story and read their captions.
  The archive references and More stay in the adult view.
- Chapter imports check the selected studio, its paper and image inputs
  and its catalogue destinations through the save.
- Data: A file on an `R:` line imports as a cut with its reading and optional
  corpus link. Existing catalogues stay readable. `instance upgrade` names
  feeds whose older file cuts are still placeholders and can be reimported.

## 0.65.0 — 28 November 2026

- We start research coverage with the books and sources still open to read from home, by line.
  `--line` shows where to read. `--family` opens the person-by-source matrix. The journal tells how
  many searches without a person document reading at a particular place.
- The plan finds ledger entries through the line's people and places as well as its surname.
  The access command shows partial reading and counts where recorded.
- Instance check puts missing document images near the top and groups repeated advice with examples.
  Research lookups and instance checks reuse work within a command.
- Data: `research document` accepts `record.place_scope` with a place and surname when there are no
  tree subjects. These readings count for that place. `instance upgrade` preserves old readings
  and points out incomplete explicit scopes.

## 0.64.3 — 28 November 2026

- The files agents read at their start are kept short by a rhythm, not by
  vigilance. Every role now changes a standing file in place instead of
  appending to it (`PROC-STATE-IN-PLACE`), and the lead runs the new
  `cleaning-pass` skill every week of work and before a broad wave
  (`PROC-CLEANING-PASS`): dead instructions are deleted, living ones are
  rewritten as state, nothing is archived.
- A host remark lands as its meaning and its reason, in the lead's own words.

## 0.64.2 — 28 November 2026

- `method/living-history.md` is shorter and speaks in one voice and one
  language: what a family asked for is retold by its meaning, without
  quotations. It gains a line for the fact checker: correct facts and
  readings, leave the writer's staging. A brief carries the meaning and the
  reason, in the lead's own words.

## 0.64.1 — 28 November 2026

- We draw the chosen reader beside their spouse, with the children below.
  Spouse labels use the person's known sex from the tree. When it is unknown,
  the label stays neutral.
- The Russian demo opens with a shorter family header. Its cover and chapter
  tell Emma's journey, with a child's question and a literal excerpt from her
  1994 rehabilitation certificate.
- Data: The Russian demo uses the existing 0.58.1 life-decision scope step.
  Older feed catalogs still build and need no conversion to chapter files.

## 0.64.0 — 28 November 2026

- We open the tree at the chosen reader, with their parents above and
  children below. The home control still takes the reader to the home couple.
- Nameless import cards that connect relatives draw as quiet knots. Search,
  the people count and the reader picker skip them.
- Data: `tree/identity-decisions.json` can record `withdraw_snapshot_cards`.
  Each entry names the marked snapshot person, the reason and sources.
  Instance check asks about outstanding marks. Removing the decision
  restores the card and its links from the frozen snapshot.
- We can manage relatives' personal logins from the loopback desk. A new
  initial password is shown on issue and expires after thirty days.

## 0.63.1 — 27 November 2026

- `method/living-history.md` explains pictures made from old photographs. A
  tinted copy of a blurred frame is the accuracy bias in images. We draw the
  place alive on a day of its time and keep the original one tap away as the
  proof. The page names what never changes: nothing impossible for the place,
  the same person in a portrait, no drawn picture captioned as a photograph.

## 0.63.0 — 27 November 2026

- The method now says what its rules are for. `method/living-history.md` is
  read first by every role that makes or judges what a family reads: what the
  family came for, the agent's bias toward accuracy named virtue by virtue
  with what each produced, the three layers that put accuracy in its place,
  and the swings of our corrections.
- A feed begins with its cast. The researcher hands the writer
  `studio/fates.md`: who the feed follows, each life by its papers, the
  turns, how it was done there and then, the neighbours, the holes. The
  place comes next, as what these people saw. Then a family-wide table gives
  each shared event of the century to one feed's side, the plan is a list of
  fates, and three chapters are shown before thirty are written.
- A person known without his paper is told by his version. A chapter of the
  place alone stands only where nobody of the family is known yet, and it is
  short. The hero's own paper stands in his chapter as the proof.
- Feed rules say what they were written against, so the next agent does not
  over-apply them. Two rules join the catalogue: `CRAFT-FATES-OF-OUR-PEOPLE`
  and `CRAFT-FEEDS-DIVIDE-THE-CENTURY`.

## 0.62.0 — 27 November 2026

- Data: Studio cuts take optional `caption=` on `R:` lines. Legacy strips
  still import. Period restorations with unidentified people may use a dated
  corpus capture to establish the frame's age.
- We can restore a picture of a place and open the original in one tap.
  Unidentified people in a period frame need a corpus capture date at
  least a century old. The frame itself retains its source and protections.
- Each family question appears once in a feed, at the first chapter naming
  its person or at the end of the relevant feed.
- A studio cut takes its caption from the chapter strip. We report a
  missing caption to the writer. The archive reference is under More.
- `feed rhythm` counts chapters that name someone from the tree in the
  opening paragraph and chapters with a placed paper cut.

## 0.61.2 — 27 November 2026

- We weigh the joints between facts. "The same surname", "next door",
  "reached", "stayed home" join two true facts into a claim; a writer looks
  up the weight of that link before the sentence stands, tells a link with no
  weight as a coincidence or cuts it, and hands in `studio/joints.md` for the
  researcher's check. A story does not claim where a person was, that they
  stayed or what they thought when the sources read whole do not name them.
- A reader's pass joins the feed method after the fact-check: one reader, the
  whole feed on a phone, six questions, a table instead of edits.
  `docs/feed-studio.md` holds the questions and the table.
- We say "our version" of a place once in a feed, where it is first needed,
  not in every chapter. Kinship counts from one seat for the whole site, the
  owner's; an in-law's line goes by first name. Before writing a decade, a
  writer reads the family's other feeds of the same years.
- `TASTE-READER-NEUTRAL` and `TASTE-NARRATOR-VOICE` follow: one seat
  instead of a household name, one bridge and one plain "we do not know".

## 0.61.1 — 27 November 2026

- We corrected the feed method after two families' feeds were written by it
  alone. A line whose village is only a version tells its region as fact,
  and its village by weight. Two rival origins are told as two true roads
  with one repeated bridge and an open end. Kin is named the way the house
  names them, the same in every feed. Hard history is told once, truthfully
  and at a child's height. A wonder told in a neighbouring feed is retold
  only from this place's side. A kept image becomes a pin by a named step,
  and a writer lists what was stated "by general history" for the checker.
- The studio's flags, `import.json` and `mentions` move from `story-scenario`
  to `docs/feed-studio.md`, so the skill keeps its length.
  `TASTE-READER-NEUTRAL` and `TASTE-NARRATOR-VOICE` name the household
  name and the bridge sentence as allowed.

## 0.61.0 — 27 November 2026

- Data: `studio/chapters/` files and `studio/import.json` are optional authoring
  inputs. Existing feed catalogs remain readable.
- We carry the writer's chapter files into a feed with `familiar feed chapters`
  and read the whole draft on a phone with `familiar feed storyboard`. Its
  strips and rhythm notes help plan the next pass.
- A writer keeps a chapter's id when the filename changes. An open choice
  gives each option its own reply and brings them together in a closing line.
  We can show a kept cut with its reading in the studio while it waits for
  a corpus record. A reader's paper caption shows the archive reference
  and leaves file paths in the research.
- The invented family's writing demo now follows Amaro's route and Rosa's
  lantern in three chapter files. The fictional desk can show its draft
  frames, and ordinary reader releases keep their finished-view check.
- The desk consumes the checked private reader and correspondence directly,
  saving repeated input checks during the build.

## 0.60.1 — 27 November 2026

- We write a feed in the order that worked at home: the place, the family's
  river and the wonders of the place by decade, then the plan of the whole,
  every chapter as a strip in a plain file, the whole read as one, facts
  checked, and only then pictures and translations. `story-scenario` is
  rewritten whole and states the chapter file that writers and scripts share.
- A paper is a pin, at most one in a chapter, never its turn or title. A time
  with no family paper yet is told through its place as an honest version.
  What any family of the kind shares is an aside, not a feature. The rhythm
  measures stay a guide. `CRAFT-COMMON-NOT-FEATURE` is new; five story rules,
  `story-text` and the feed author's sheet are restated to match.

## 0.60.0 — 27 November 2026

- Data: An optional `route` on a `play.json` game places labelled points on a
  chapter image. Existing games still work.
- We can read a short paragraph with a child, look at a picture or play, then
  keep reading in the writer's order. Draft frames speak quietly, and the
  phone leaves the reader, mode, chest and language one tap away.
- A child can trace a route across a chapter picture or tap its stops.
  A question with one answer opens it in place, including while a map is a draft.
- We check the same letters once per desk build and use the checked list in
  every reader language. A desk without letters skips that snapshot.

## 0.59.0 — 27 November 2026

- Data: Optional `flow` entries in `chapters.json` place draft frames and
  activities after paragraphs. Existing chapter text and placements still work.
- We can read a rough chapter at home with grey frames at their intended
  positions and play a chapter's game between its paragraphs. The investigation
  shows each feed as a strip, and `familiar feed rhythm` measures the spacing.
  Rhythm advice leaves the family check valid. Draft frames keep the feed home.
- A tentative family link cannot use the shorter age horizon to open a card.
  Photographs with unnamed faces stay home. A delivered portrait uses the
  marked face's own image bytes. At home, a tap still opens the whole photograph.

## 0.58.1 — 26 November 2026

- We keep a life event on the family card even when its source mentions an
  inventory. The family can find a likely second card by its written name.
  Its own account stays under the likely match, with papers and dates limited
  to what the two cards can show.
- We keep age judgements made for the family inside its view. Public reader ids
  for protected people and closed papers are local to the bundle. We require
  complete participant lists on public census and annex papers.
- We point the author to passages that may need paragraph-level people. An
  attributed public alternative can tell names and kinship in the same place.
- Data: `instance check` and `instance upgrade` locate decisions whose author
  must confirm `home` or `everywhere`. Existing unscoped death decisions continue
  to serve the family view.

## 0.58.0 — 26 November 2026

- A face leads the card. Where the reader may see a family photograph of the
  person, the card's head shows the face instead of a letter, in the gold ring
  of the tree's couples; one tap opens the photograph whole with its caption, and
  the original is one tap further. A restored portrait stands with its original.
  Photos come before papers on the card. Without a photograph the letter stays.
- The host marks each named face on a group photograph and can show only the
  print of a photograph re-shot by phone: `intake photo --face ID=x,y,w,h` and
  `--crop x,y,w,h`, as fractions of the picture, also later on the attached
  original. The received bytes are never changed.
- Near tiles of the tree carry the face of a person who has one. A small tile
  in a crowded row shows the given name where the row leaves room for it.
- An in-law is named in the family's words from the kinship table: "прабабушка
  жены", "жена двоюродного брата", "wife's grandfather"; the long explanation
  stays one tap away.
- Relatives: each person we would ask is one card with the face or the letter,
  the first question large and the others under "ещё 8".
- Stories: a book without a cover opens with its first picture or document or
  a calm paper page; "What's new" says each thing once; a long line of stories
  shows four and the rest one tap away. A person's own papers come before papers
  that only mention them.
- Data: photo entries may carry optional `faces` and `crop`; existing entries
  need no carry-over.

## 0.57.4 — 26 November 2026

- We show one family card when a likely double reaches the tree's drawing
  threshold. The second card's visible dates and papers remain a possibility
  alongside the family's own account. Life assessment still uses each card separately.
- We hide empty letter and weight-change sections, show a preview of PDF papers,
  put archive checks in the card's details and use kinship words for questions on a relative's own card.
- We give a paper intake example and let the host record why a photo was sent
  and choose whether it goes in the gallery, on a card or in the archive.
- Data: existing photo entries keep their gallery placement. The display choice,
  purpose and sheet/unnamed-face marks are optional, so no carry-over is needed.

## 0.57.3 — 25 November 2026

- We transfer a paper's participants and dates only through accepted identities.
  A possible namesake keeps their own card and evidence. Their suggested kinship
  remains a hypothesis, with the identity explanation on the family's desk.
- We keep written family feedback out of document delivery, including when it
  has been copied into a home paper. The family account can still tell the kinship.
- We label a chapter's original text when its translation is missing.
- Data: no migration.

## 0.57.2 — 25 November 2026

- We use a paper's date only for the participants recorded on the paper. A
  citation from another person's event, claim or family link leaves that
  person's age unchanged. An attributed parent link can still carry the
  child's own recorded event.
- Data: no migration. Record established participants on the corpus record
  when its date supplies their age bound.

## 0.57.1 — 25 November 2026

- We use dated participation and recorded events on family relationships to
  set a latest possible birth year. An import precaution or a merged card with
  missing evidence uses the ordinary 100-year public and 75-year family rules.
  The family's declaration and a relative's refusal survive a merge.
- We keep separately attributed literal fields readable when a full sheet is
  withheld. A shortened public story still shows its surviving papers.
- Data: no migration. A date in free text needs an attributed event to bound
  the age of a participant whose status is unknown.

## 0.57.0 — 25 November 2026

- The lower row of every page holds at most four places, each an icon and a word:
  tree, relatives, stories, papers. What a family does not have is not there; `desk
  build` stops at a fifth. On a phone the row is 72 px instead of two rows of 104,
  and nothing in it scrolls sideways. Everything else (surnames, map, how the search
  goes, the host's search map and letters, the remark, language, notice and version)
  opens from "More" in the page top, which desk pages now always have: names by
  language used to break it there, and the way home with it.
- "Show me the papers" has one answer. Papers stand in the lower row: by person, the
  nearest to the reader first, by decade, and the photographs beside them. A paper
  opens large over the page with whose it is and what it says; Back returns to the
  same place on the same page. Cards and chapters open papers the same way. The page
  shows what the delivered graph carries and asks for nothing more. The archive
  letters that were called "Documents" are called letters.
- A kinship word explains itself where it stands: a tap gives its plain meaning and
  the way to this person, name by name; lists and chapters put the meaning beside a
  rarer word. "Kinship words" is no menu entry, is reached from an explanation and
  lists only words somebody in the shown tree answers to. Meanings no longer count
  generations: "father of your grandfather or grandmother".
- The investigation starts with three plain sentences and what this family looks for
  now, found lately and can be helped with; the detail below is unchanged. "Where we
  looked" on a card says it in words.
- A phone page has a floor: body text from 18 px, targets from 48 px, contrast AA.
  Rule `CRAFT-PLAIN-PAGES` says what a family's page may carry. The shell does not
  build with a workshop word or an apology for emptiness in its strings or in a
  bundled pack's desk words (`reader-src/plain-words.json`).
- Data: nothing to carry over. `#view=photos` is now a tab of `#view=papers`; a
  language pack's `nav_kinship` and `nav_photos` are no longer read, `nav_papers`,
  `remark_write` and the `intro` lines of `desk.show` fall back to English until
  translated.

## 0.56.2 — 25 November 2026

- We use a child's recorded birth and a confirmed parent link when assessing
  the parent's age. Weak events and proposed links keep their uncertainty.
- We keep family recollections, historical names and ordinary phrases readable.
  Papers cited by a family relationship and recognizable passages from a
  protected reading follow the document's privacy through the desk and reader.
- We keep a relative's refusal when the card they answered on is merged.

## 0.56.1 — 25 November 2026

- We assess life from attributed events and explicit family decisions. Card
  estimates, identity guesses and proposed readings keep their presentation role.
- A document cited from a protected person's card stays withheld unless its
  corpus record attests complete subjects and the citation is an inference about
  someone else. The document page, scan, quotation and book use that decision.
- A visible amendment can be answered on the local desk or by a personal
  sign-in. The answer binds the offered revision and person. The owner can
  reopen a refusal. Declined and withheld proposals stay out of reader files.
- Guesses are offered only for established deceased people. Search pages and
  plan text omit protected names. A marriage without children contributes no
  downward link when weighting a merged identity.
- Data: existing records and inbox envelopes are preserved. Set
  `subjects_complete: true` only after reviewing the whole document and naming
  every subject in its corpus record. Earlier taps stay as literal testimony.
  Build the desk again to issue offers that can settle a proposal.

## 0.56.0 — 25 November 2026

- A document stays on the card of the man it is about. When its source or record lists
  its `subjects`, a fact on a living son's card that only infers from it ("his father was
  …") no longer takes it away. Without stated subjects, when the living person's own name
  or event cites it, or when its own words name that person, it stays closed as before.
  `instance check` names each paper that is off a card for such a fact alone and shows the
  line that states its subjects.
- An estimated year of birth agrees with the story on the same card. A soldier of 1915 is
  no longer "born about 1905" because his children came late: dated things the card tells
  (a wedding, a baptism, service in a fact firm or weighted from 0.3) hold the estimate
  back, "More" says why, and a parent estimated from that child moves with it. Where they
  cannot agree with the years of close relatives, `instance check` says so in one line.
  The protection of the living never uses these bounds.
- The research plan no longer says "not applicable · a place" about a line whose village
  the access ledger lists. A line has a place when the ledger, a version from 0.3 or a told
  fact gives one, a parish when the ledger's books name their church, a registrar when a
  row is answered by letter.
- One access ledger, not two. `research access --markdown --save` prints the whole ledger
  as `ACCESS.md` with the date, author and report of each verdict, prices, what is missing
  to order a copy, and the reading-room list; every later verdict renews the page.
  `research access note` keeps the words around the rows. A page kept by hand is never
  overwritten, and `instance check` says when the two differ. A copy with an `order` now
  stands in the reading-room list too.
- Data: nothing to carry over; `title`, `about`, `sections`, `room` and a place's `about`
  and `section` in `research/access.json` are optional. A family that already keeps a page
  named ACCESS.md by hand is told in one line.

## 0.55.0 — 25 November 2026

- A bare card now invites. On the family desk the card of an ancestor whom somebody
  alive may have known shows what it lacks as unfilled lines of the card: name,
  patronymic, year of birth, wife or husband, occupation, brothers and sisters. A tap
  opens the usual remark form with the person and the line already named. Where we hold
  a guess, it stands in the line and one tap says "yes, so it was". A card that already
  tells who this was stays quiet, and so does an ancestor nobody alive could have known
  or a line the family closed.
- A correction is kept beside the original. `research amend` records what was told or
  read, what we propose instead, its weight and why. From 0.5 the card tells the proposal
  and keeps the first word under "More"; a relative confirms or declines it with one tap.
- What a family tells is taken in with its layer: parents, surnames and villages hold,
  years and name forms drift, an empty cell means nobody asked. The research plan names a
  thin link, what to lean on and what to loosen, and its first step is to show the relatives
  the card; the place and the new "small lists by occupation" come before surname bases.
  `instance check` hints when a long search never did that.
- The weight of a merge reaches the tree: below 0.9 it caps exactly the links a line
  crosses between the two cards. Links read from one document stay as firm as they were.
- The access ledger knows a copy the archive sells remotely (`copy`, with a price and
  what is still missing to order it). The plan says "order a copy" or "find out" instead
  of sending anybody to the reading room.
- Data: nothing to carry over. `family/amendments/`, `guess` in a version option, `layers`
  and `blanks` in a telling and the `copy` state are optional. A family with merges weighed
  below 0.9 sees some links between the merged cards drawn with the weight of the merge.

## 0.54.0 — 25 November 2026

- "Nothing found" and "we could not open it" no longer look alike. A family now
  keeps an access ledger: for each village, which books exist, which we have read
  (so many of so many), which open from home, which lie in a reading room or are
  answered by letter, and which nobody has located yet. An agent records one
  verdict with one command, `familiar research access record`.
- The research plan shows the books of the line's villages first. Where nothing
  opens from home it says so, with the archive and call number, and the next step
  is the reading-room order or the letter rather than one more pass over name
  bases.
- `instance check` speaks up when a version or a strategy note says a line is
  exhausted while its village still has unread books, and when a long search never
  asked which books exist. It is a hint and stops nothing.
- The search map tells the family where the books lie and what we have read, and
  ends with a list a relative could take to the reading room: archive, call number,
  what to look for. The page opens in each language the family reads.
- Data: nothing to carry over; `research/access.json` is a new optional file
  (`familiar research form access`).

## 0.53.3 — 23 November 2026

- If your earlier words already arrived, your edited text stays in the box
  so you can send it too. Photos that still need to go stay in the tray and
  can be sent again with the same receipt.
- A moving upload keeps going on a slow connection. Each part has up to
  45 seconds without progress and up to 5 minutes in all.

## 0.53.2 — 23 November 2026

- The desk delivers your words first. If a picture stalls, the same receipt
  shows which files you can choose again. Each file finishes on its own and
  a retry picks up the missing parts, including on a slow phone connection.
- Signing out clears the cookies on the computer even if the file store is
  unavailable. Taking in a scan opens the original inside an operating-system
  sandbox and makes a new picture for the family.
- Data: no conversion is needed. Old messages and originals keep their paths.
  New originals are filed beside their remark as they arrive. Update the
  personal desk before publishing the new browser files.

## 0.53.1 — 23 November 2026

- A second tap or a broken connection keeps the first receipt and resumes
  with the parts the cabinet still needs. A finished remark is charged once.
  Pictures use the signed-in desk itself, and signing out closes its slots.
- The host brings the words home even when a photograph needs another fetch.
  Each failed file is named by remark and number, and a later fetch fills in
  files beside envelopes saved by an older engine.
- Taking in a photograph from a remark preserves the original in private and
  gives the family a fresh display picture. The images extra includes the
  first-page PDF renderer. Answers have one paperclip.
- Personal provision stages its full template in the owned private bucket.
  Data: run `instance upgrade` to re-render already adopted attachments from
  0.53.0. Their original bytes, gallery URLs and inbox envelopes stay in place.

## 0.53.0 — 23 November 2026

- A relative can send a scan or a photograph with a remark. Wherever a remark is
  written today — the remark sheet on a card or a feed step, a card correction,
  an answer to an ask — a quiet paperclip opens the phone's camera or gallery; on
  a computer, files or a drop. A picture alone is a whole remark. The thumbnails
  fill as each file leaves, and the receipt is the same quiet "Received".
- Only a signed-in relative (personal logins) or the host on his own computer
  can attach; the shared password sends words only. A file is taken by what it
  is, not by its name: photographs and scans (JPEG, PNG, WebP, iPhone HEIC,
  AVIF, TIFF, PDF), up to 30 MB a file, 10 files a message, 40 a day. A refused
  file says why in plain words and the text stays.
- On a personal cloud desk the phone sends the file straight to the family's
  private inbox through a short signed upload, so a 12 MB photograph fits.
  `desk fetch-feedback` brings the originals home byte for byte, beside the
  words; nothing appears on the site until the host takes it in with
  `familiar intake attachment ID` — the person, caption and sender come from the
  remark. `familiar family next` says how many files wait.
- An iPhone HEIC photograph and the first page of a PDF scan now make a display
  picture in the photo intake; the `images` extra adds `pillow-heif`.
- The personal desk's template body stays under CloudFormation's limit: comments
  are left out of the composed function code.
- Data: nothing to carry over. A cloud desk with personal logins needs
  `desk provision` once to accept files; logins and the inbox stay.

## 0.52.2 — 23 November 2026

- The way down from a couple through a generation nobody has found no longer
  reads as "son of the first child". The missing generation is one more child
  of the couple: a haze of a card's size in their children's row, hanging from
  their ring, and the family's person hangs straight below that haze, never
  from a named child. The haze stands beside the child the data name as the
  one who may stand there, with his given name in it; with nobody named, in the
  middle of the row. Further missing generations are bands of haze below it,
  and a tap on the haze goes on along the line. Seen from below, the haze hangs
  from the couple, not from the husband alone.
- A fact a decision retired no longer puts its papers on the person's card.
- Data: nothing to carry over.

## 0.52.1 — 22 November 2026

- The search map reads at a glance on a real family, not only on the demo. A
  line is one section however many chains carry its surname; the lines the
  family works on now come first and open, the others fold to one row with
  their counts. Books of one place stand on one row of the line's time axis, a
  lane each for births, marriages and deaths, and a tap opens them year by
  year. Name bases are small tiles: never opened first, then the least read;
  numbers and the forms not yet read wait behind a tap. On one family's page
  this took the phone height from about 46,000 pixels to under 5,000.
- A base that holds only one community's records (the region's Jewish indexes)
  no longer looks like a hole on a line whose records say its people were
  baptised in a parish. Where nobody's community is recorded, the map says
  "only if the line was ..." instead. The region's catalogue marks these bases
  with `communities`.
- `research map` in text is short enough to paste into a brief: one row per
  series, the bases as "opened N of M", the ones never opened and the ones with
  forms missing, and one line for each other line.
- A line with no recorded place no longer calls every base unfit; its fit is
  unknown.
- Data: nothing to carry over.

## 0.52.0 — 22 November 2026

- The search map: what of the open record has been read for a line, and what
  has not. A family keeps a list of record series in `sources/series.json`
  (`research form series`): one kind of record for one place over a run of
  years, with who holds it, where it is online and which years the copy lacks.
  A journal row may say which series it read, which years and how deep: the
  whole year, only the surname column, named entries, or someone else's index.
  `research map [--line NAME]` draws every series year by year with the best
  reading reached, the field of name bases that fit the line (opened or not,
  rows returned and read, the family's forms read and missed), and the empty
  cells ranked: the years of the open question first, the place of the leading
  version, then what is online now before what needs a login or a letter.
- "Exhausted" is now a statement about the map: while online years in the
  question's window are unread, `research plan` calls no approach on that line
  exhausted, shows the open record first and, instead of a question to the
  family, sends us to read those books. Without a series list it says the open
  record is unknown.
- The host sees it in the desk: a "Search map" page with the strips by year,
  the bases as tiles and the next years to read in plain words. The page is the
  host's: the copy the family reads leaves it out. The demo family has three
  invented series, so the demo site shows the page.
- Data: nothing to carry over. The series list is a new optional file; rows
  without `coverage.series` or `coverage.depth` stay valid and show as "depth
  unknown".

## 0.51.1 — 22 November 2026

- The whole tree no longer draws a long line copied from one book as firmly as a
  grandfather the family remembers. How firmly a person holds to the family is
  now every link on the way down multiplied, not only the weak ones: a book line
  of links at 0.7 turns probable after two links and our version after four, and
  the place where it changes step is a bend you can see. A link without a weight
  counts by its status: a record 0.98 (a line of records stays firm for some
  thirty generations), an imported tree or family memory 0.95, a probable version
  0.4, an assumption 0.2. Of two ways down (father's and mother's) the better
  one counts; the family's main line is always drawn, its step is as honest as
  any other. A link's own line still shows only that link.
- When the data admit a second way up, it is shown, at most one a person: when a
  possible ancestor may be a father or a grandfather and has a son of a fitting
  age in the tree, a pale haze on the tree link carries that son's name, the whole
  tree draws a thin pale line to him, and the card says it in one quiet line
  ("A — father or grandfather; if grandfather, the father is B"). A second
  candidate recorded with its own weight from 0.1 gets the same pale line on the
  whole tree and the same line in the card. No new data form.

## 0.51.0 — 22 November 2026

- A family can tell us that on a line nobody is left to ask, or nobody will
  answer: `family horizon close LINE --by WHO [--known TEXT] [--reopen-when EVENT]`.
  From then on unanswered questions on that line leave the Relatives page, the
  cards and the feeds; the research plan marks asking relatives "nobody left to
  ask", starts from indirect signs (faith and parish, staying put, a name from
  grandfather to grandson, the parents' age, a rare set of names, godparents and
  marriages) and keeps archive letters and deep inventories as options. A new
  question on such a line needs `--despite-horizon`. `family horizon open LINE`
  brings the questions back. Weights do not change: silence is not an argument.
- A version question may name the version its story tells, chosen by weight or
  by interest. Interest chooses only among versions of at least half the weight
  of the first and never moves a weight or the 0.5 and 0.3 drawing thresholds;
  `instance check` refuses a choice that breaks this and names the versions and
  their weights. On a closed line it hints to name the leading version, and it
  says when the tree's main line hangs a person of another version.
- The method has a chapter "When the family can say no more" in
  `docs/research-coverage.md`; the demo family closes Rosa's own line, Calhau.
- Data: new optional `family/horizons.json` (path key `horizons`) and optional
  `story_choice` in `versions/*.json`. Older families have nothing to carry over.

## 0.50.2 — 22 November 2026

- On the Relatives page a question about a family line or a place, with no person
  named, shows that line and place in the reader's language like the rest of the card.

## 0.50.1 — 22 November 2026

- The whole tree gives every ancestor line a band of its own. A line with many
  brothers, sisters and cousins widens its own band and no longer lies over the
  neighbouring line, where it looked as if the two families were related.
- Opened on the whole page, the picture takes the shape of the screen: on a wide
  screen the lines stand apart instead of leaving empty margins. The corner
  picture fills its box the same way; a phone still opens on the current person.
- The picture shows how firmly each branch holds to the family, in three steps
  — from records and family memory, probably, our version. A link is drawn
  whole, dashed or dotted by its own weight; a person is a filled dot, a pale
  dot in a rim or an empty ring by the links on the way down to the family. So
  the place where a well-gathered branch hangs on a guess is visible at a glance,
  together with everything above it. A short legend sits by the lines.
- Choosing a person draws their way down to the family and marks the link on it
  that holds least; the card says in one line how they are tied to the family.
- The part of the tree on screen is now marked by one soft frame instead of a
  glow around each dot, so size and fill of a dot keep their own meaning.
- On the family desk the opened picture ends above the desk footer: its buttons
  and the card of the chosen person are no longer hidden under it.

## 0.50.0 — 21 November 2026

If you installed 0.41.3, this is what is new for you. A family can be served
from its last commit, so a file an agent is still writing no longer blocks a
check or a build; a contribution that refers to something not committed yet
waits in quarantine and applies by itself once the reference exists. Names,
surnames and places carry their forms — male and female, Latin and Cyrillic,
the cases of old acts, the reader's language — and `research compare` weighs
whether two records are one person from all the arguments together, showing
what each gave. The tree grows as two crowns, the husband's ancestors and the
wife's, with open sky between them, and a married woman stands under the
family she was born to. `familiar instance upgrade` carries a family's stored
forms over from any older release in one run;
[docs/upgrading.md](docs/upgrading.md#from-0413-to-0500) says what to run.
The install steps now point at this release, `instance check` reports
research in progress in the family's language, and broken links in the docs
are fixed.

## 0.49.3 — 21 November 2026

- `familiar instance upgrade [--dry-run]` carries a family's stored forms over
  from any older release in one run: each release that changes a stored form
  adds a step; it says what it changed or names the file and the decision, and
  never deletes a file.
- Data: rows of `media/manifest.json` that export a document page the engine
  renders itself since 0.41.0 (`sources/<id>.html`) stop the reader build;
  `instance upgrade` removes those registry rows and keeps the files.
- A build that stops on colliding names says how many, which, and what to do.

## 0.49.2 — 21 November 2026

- Tree: a wide row of children pans sideways; near rows keep names on a phone.
- Tree: a probable identity dates the card by the found record's birth.
- Check: `instance check` names unread contribution keys (links go in `edges`).
- Fix: `tree surname set` keeps a decision's basis and people.

## 0.49.1 — 21 November 2026

- Tree: a possible child with no missing generation stands in the children
  row beside the siblings, by seniority (guessed years count), not below them
  as a grandchild; the way down through missing generations steps aside
  instead of hanging under one child.

## 0.49.0 — 21 November 2026

- A family can be served from its last commit. `instance check`, `desk build`
  and the local reader can read the family as it stands in a git commit (a
  worktree such as `.state/serve`), so a file a researcher is still writing
  never blocks a release or a build. Record files kept outside git (captures,
  originals) resolve through `FAMILIAR_HOST_PATHS`. The check of a served
  commit is paid once per commit.
- A contribution or a version that refers to something not committed yet is
  quarantined instead of vetoing the family: it is named with `QUARANTINE` in
  `instance check`, in `desk build` and before `desk publish`, and
  applies by itself once the reference exists. A contribution that used to
  apply and no longer does is still an error.
- Research lookups (`research forms`, `research compare`, `tree person`) no
  longer run the family-wide verdict: 2 s instead of 9, and an unfinished
  record does not block them. The verdict computes its derived data once.
- Tests keep only what guards family data, privacy and install: five surface
  tests are gone; the fast run takes 15 s instead of 50, the full run 28 s
  instead of 86. Every check now answers what it gives the agent of a
  research application and what that agent pays for it per day.

## 0.48.0 — 21 November 2026

- Search forms by key. `research forms` adds, with a mark, the spellings of a
  surname or a place that share its key (male and female forms, case endings
  of acts, Latin and Cyrillic, a regional sound key) and the forms a clan
  decision names. They are offered for search and are not required coverage.
  The key rules live in the region and language packs.
- `research compare` weighs whether two records are one person from
  likelihood ratios — the rarity of the name, the surname, age, place, rite,
  the family as one argument — and shows what each argument gave; candidates
  nobody has seen yet are a line of their own. It decides nothing: the agent
  does.
- `instance check` hints at surnames that share a key outside a clan decision.
- Data: a place record may carry `modern`, `parish` by rite, `manor` and
  `coords` with their source. No migration is needed.

## 0.47.0 — 21 November 2026

- The families page shows each family once. A wife stands under her father's
  clan, named by her surname at birth; the male and female forms of one
  surname are one family; a decided clan is one tile. A clan decision no
  longer renames a married woman.
- The documents and investigation pages exist in every reader language; links
  and the open page follow the chosen language. A letter to an archive keeps
  its original subject and text.
- Nested tables and lists in a document's retelling are translated cell by
  cell; a chapter year written in words is a translation unit; questions on a
  card and in a feed switch with the language.

## 0.46.0 — 21 November 2026

- The tree grows as two crowns. The ancestors of the husband and of the wife
  each converge above their own root, with open sky between them all the way
  up; only a real shared ancestor crosses it. A side that is traced deeper
  rises higher alone, so the picture shows which lines are known further.
  Clans of different colours keep a wider gap than neighbours within a clan.
- One generation is drawn at one size on both sides.
- The family map keeps the husband's and the wife's halves apart.
- On a phone the first picture is unchanged: parents and grandparents fill
  the width with names and years.

## 0.45.0 — 21 November 2026

- The whole page reads in the reader's language. The family title can be
  given per language; a text with no translation is shown in the family's
  source language, not in English.
- Card texts, document pages, research news and questions to relatives are
  translated through `tree/translations/<lang>.json` (exact text to its
  translation). A chapter's separate children's text is a translation unit.
- In Polish a clan is named by its Polish surname.
- `instance check` hints at a cited record whose image is not on disk.
- A name form for a person that research has renamed is advice, not a broken
  tree.
- Data: `[family].title` may be a table by language; optional
  `tree/translations/<lang>.json`. No migration is needed.

## 0.44.0 — 21 November 2026

- Each name is shown in the reader's language: a tile and a card take the
  name form of the language the reader chose, and otherwise the family's main
  name. A document's spelling never goes to a tile; the card lists how the
  documents wrote the name, with the document, under "More". A decided name
  is kept whole when a clan surname form is applied.
- A text that has no translation yet is shown in the family's source
  language instead of being left empty.
- `instance check` hints at a tile that would show pre-reform letters,
  another script or the grammatical case of an act.
- Data: optional `name_forms[].by_language` and `names[].lang`. No migration
  is needed.

## 0.43.2 — 20 November 2026

- A family can take one version of a person's origin as its main line. It is
  then drawn as the main branch whatever its weight: documents as a solid
  line, named assumptions as a dashed line with a light haze behind the tile,
  gaps as haze. A chain of several assumptions does not break the branch. The
  card's details say it is the family's working version, or an assumption,
  and what would confirm it; the honest weight stays there.
- Data: `main_line: true` on `possible_parent`, `possible_ancestor` and on a
  probable identity. No migration is needed.

## 0.43.1 — 20 November 2026

- When nothing stands above a person and the leading version of their origin
  is weaker than 0.3, that one branch is still drawn, in the faintest form:
  pale tiles, thick haze, a barely traced line (from 0.1). The card's details
  call it one of the possible branches.
- From the ancestor that anchors a nest the way down is visible: through the
  missing generations to the family member, and one can step there.

## 0.43.0 — 20 November 2026

- Probable branches are drawn in the main tree. When a found person is
  probably the same as a family member (weight 0.3–0.5), that person's
  parents and their line rise above the family member as a dashed branch,
  with no double beside them. When a person probably descends from a
  reconstructed nest but the links between are not found, the missing
  generations are drawn as haze and the ancestor stands on his own
  generation. The weight and the grounds stay in the card's details.
- Data: identity decisions accept `merges[].status: "probable"` with a
  weight, and associations accept `possible_ancestor` with `missing` and
  `missing_max`. Existing data stays valid without migration;
  `possible_parent` reads as before.

## 0.42.1 — 20 November 2026

- A twelfth research approach, **surname households by place**: when a line
  stops at a person known only by name, the plan no longer waits for the
  missing paper. It rebuilds every household of the surname in the place from
  the earliest list downwards and counts who could have been that person. The
  place may come from a weighted origin hypothesis; no bridge to the living
  family is required. The plan names the place, the earliest open period and
  the unattached candidates already proposed.

## 0.42.0 — 19 November 2026

- Research approaches are now part of the engine. `familiar research plan`
  lists, for every family line, eleven ordered ways of searching — who kept
  the records of the place, how the keeper spells it, a paper on the family's
  shelf, registry letters, the household fingerprint, the generation's
  behaviour, databases by surname, graves, neighbours and godparents, forums,
  inventories in depth — with a state for each: not tried, running, exhausted,
  or not applicable and what is missing. A family sets `focus` in
  `[research]` to put its lines first and may switch or reorder approaches.
- A coverage cell that gave nothing new three times is a ceiling and leaves
  the recheck queue. Forms of other lines, forms in a script the source does
  not use, and sources outside a person's epoch no longer count as gaps.
- Data: search journals accept an optional `play` id. Existing rows stay
  readable without migration.

## 0.41.3 — 19 November 2026

- The ring is back, and now it belongs to every family in the tree: the
  branches of the two parents meet in a ring above their child, the same ring
  that joins the couple in the middle. It rides above a child's stack of
  siblings; rows in the haze keep the plain fork.

## 0.41.2 — 19 November 2026

- The wheel always leads somewhere. Outwards draws one more generation; once
  all are open it goes back the way the reader came, and with no such way one
  step along the kinship towards the family's home people. Inwards over a
  person moves the tree to that person and keeps the branch above them. One
  turn of the wheel, one pinch or one press of a round button is one step.
- Branches bend again: every parent sends an own coloured branch down to the
  child, and two of them meet above the child like the fork of a tree. A
  couple whose parents are drawn stands apart, each under the own parents.
- Rows spread to use the height of the screen, so the branches have room.
- The count of generations between the two round buttons reads as a figure,
  not as a third button.
- A page opened by a link to a person starts on that person at once.
- A kin word for a man or a woman is explained by the person it names: a
  great-aunt is a sister of a grandparent, "двоюродная бабушка" is "сестра
  дедушки или бабушки" (Russian, Polish, English).
- Counted captions of the investigation agree with their number ("2 вопроса",
  "1 question").

## 0.41.1 — 18 November 2026

- A claim taken from another tree reads on the card as the claim itself: a
  name, a date and a place. The card no longer shows its stored form or the
  word "unverified"; the dotted status and the source say whose claim it is.
- What only another tree says about a person (a name, a date, a remark) stays
  in the fold of details as a version, not on the card.
- Kin phrases decline the name they lean on ("Amaro's wife", "жена Андрея"),
  "after 1941" reads in the reader's language, and counted generations agree
  with their number in Russian, Polish and English.
- Back on a paper opened in its own tab returns to the story it was opened
  from. A place only another tree gives no longer heads the card.
- The confirmed mark names only papers that name the person: a record listing
  its subjects without them no longer stands behind their card.
- The kinship words page opens without a caution about proof, and the reader
  button of a story is no longer cut off on a phone.
- The Russian demonstration keeps its recorded deaths on merged cards.
- Data: new GEDCOM intakes store a claim without the "Recorded in another
  tree" prefix; claims stored with it are read the same way, nothing to carry
  over.

## 0.41.0 — 18 November 2026

- A family that already keeps an archive can move in. `docs/moving-in.md` tells
  an agent where people, kinship, notes, photographs, papers and finished
  stories go and how to count what was lost on the way. What the family's own
  archive holds as known arrives as firm family memory; only what that archive
  itself doubted stays a version.
- `intake photo` attaches a family photograph to the people on it, one file or
  a whole table at once. The received file is kept byte for byte; the picture
  stands on each person's card and on the Photos page.
- `intake gedcom --own` takes the family's own tree as the family's word, with
  solid lines. Without it a GEDCOM stays another tree's claims.
  A death read from a GEDCOM stays an imported claim in both modes, so whose
  tree it is never opens a possibly living person's papers.
- `instance init --language en` connects the English host wording by itself.
- `intake kinship-case` carries an ex-ussr-kinship-research case into Familiar:
  people, relationships with their standing, artifacts with scans, claims and
  the search log, so coverage knows where was already looked. A dry run comes
  first; `docs/moving-from-kinship-research.md` has the mapping.
- The tree steps one generation at a time again. The wheel and the round
  buttons add or drop exactly one generation of ancestors, one step per turn
  of the wheel, and the whole drawn tree refits the screen. A crowded row gets
  narrower tiles, down to an initial, instead of running off the edge. A click
  centres the tree on that person. This replaces the map-like zoom of 0.40.0.
- The tile tells the card's name: bracketed remarks of an old import are
  dropped, and a written surname the card no longer carries stays only as the
  known maiden name or the clan's adopted spelling.
- Home, not court: notices such as "documents exist but do not confirm the
  facts" are gone from the pages a family reads. Rule `CRAFT-HOME-NOT-COURT`
  asks every role to tell the leading version and stay silent where nothing is
  known.
- An explicit unknown life decision is honoured in the family display, and a
  card no longer cites a withheld paper of a protected person.
- Data: memory intake accepts JSON with notes and an archive original; photo
  intake stores gallery bindings with original and display hashes; kinship
  intake saves the complete case ZIP and maps its registers into working
  forms. Nothing already stored changes shape.

## 0.40.1 — 18 November 2026

- A cut-out keeps its own picture on the person's card; the whole sheet stands
  only for sources without one.

## 0.40.0 — 18 November 2026

- The tree zooms like a map: the wheel and the pinch only scale the picture
  under the pointer, and who stands in the centre changes by choosing a person.
  A couple is joined by a ring and their child hangs from it. Every tile shows
  a year, estimated when no record gives one; distant tiles open into the whole
  name when zoomed. The count sits in the corner map. The rays, the generation
  switch and the large add-relative entry are gone.
- A person's card tells the leading version. Versions weaker than 0.3 and their
  papers stay in the investigation; grounds, search coverage and retired claims
  share one fold at the end. Scans a source carries are shown as pictures.
- Relatives is a conversation, not a form: the tree comes first in the
  navigation, each ask names the person it is about, hints drop into one
  answer field, and the state buttons and counters are gone. An occasion never
  states an age.
- Show preserved scans and thumbnails on local document pages.
- Use a 75-year default for uncertain life status in the family reader
  (`privacy.family_years`); the public horizon stays `privacy.living_years`.

## 0.39.1 — 18 November 2026

- We show one tree count, keep sibling stacks as a visual cue, and leave out
  unknown parent tiles. The central couple and their children fit together.

## 0.39.0 — 18 November 2026

- The family tree keeps every person on a tile. Sibling stacks open in birth
  order, older generations recede towards the horizon, and missing parents
  have a place. The count opens family lists for people outside the canvas.
  Select a tile to read the person's card, then choose when to centre their family.

## 0.38.0 — 18 November 2026

- Relatives gathers conversation prompts by living witness, adds a mode for
  grandchildren and brings open asks into the family feed and tree. Answers
  marked private, including answers to tender asks, can stay in research memory.
- Data: Run `family ask migrate` to carry `family/questions` and old `relative`
  letters to `family/asks`, preserving question IDs, replies and original
  references. Rebuild the desk and provision its stack to receive the new
  feedback kinds in a hosted desk.

## 0.37.1 — 18 November 2026

- A letter whose question has only a weak leading answer now ranks as fully
  open: we know little there, so the letter can tell us most.

## 0.37.0 — 18 November 2026

- We show Documents by family line and person, rank ready letters by what they
  can establish, and set letters aside when their linked version is settled.
- Data: Run `family correspondence migrate-relatives` to move old relative
  letters and replies to family questions. External letters without an `aim`
  stay available under No aim.

## 0.36.3 — 18 November 2026

- We skip military sources outside a person's birth cohort and accept plain-text person notes in builds.

## 0.36.2 — 18 November 2026

- We recheck the chosen main lines and ancestors' siblings first, label the
  queue by line, and count living people and those of unknown status separately
  in the line fronts.

## 0.36.1 — 18 November 2026

- We follow weighted parent links from 0.30, show the ancestry chain by
  surname, match open questions to their line, and show the family's chosen
  main lines first in coverage and the desk.

## 0.36.0 — 18 November 2026

- We see each family line's farthest known ancestor, open parent versions and
  coverage gaps in `research coverage --lines` and the family desk. Read records
  can surface hints from collateral branches. When enabled, their descendants
  and spouses have their own coverage totals and follow the main recheck queue.

## 0.35.0 — 17 November 2026

- We turn correspondence into a mailbox: compact letter rows, status and recipient
  groups, an inline phone letter and a wide reading pane. Copy the destination,
  subject and text separately; people still send and record replies themselves.
- Letters accept optional `subject`, `priority` (`first`/`later`), `cost`
  (`free`/`paid`/`unknown`), `cost_note`, recipient `kind`, `how`, `relevance`
  and state `not_needed` through `family correspondence create` and `update`.
  Planning can change after sending while the sent text and replies stay literal.
  Postal destinations are copyable text. Existing letters need no migration.

## 0.34.0 — 17 November 2026

- We tell family stories about everyone, including living people and people whose
  life status is unknown. We remove permission letters and field-by-field consent.
  Family desks and private reader/book exports retain their stories and captions;
  public output gives outsiders only names and kinship. Document, address and
  image-generation exclusions remain.
- Data: Remove `allowed` and `consent` from each `privacy.json` `living[]` object,
  keeping `id` (or use the person ID as the entry). No carry-over command is needed:
  the removed fields are ignored; no family facts change.

## 0.33.1 — 17 November 2026

- We accept sourced spouse unions through contribution `families`, including a
  spouse added in the same package. Weight and basis reach the reader's existing
  lines: weights from 0.3 to below 0.5 are dashed, including probable links;
  weights of 0.5 and above are solid. Parent links remain separate `edges`.
- We let relatives' letters omit `destination` or use `null`. The correspondence
  page keeps the text and Copy action without an invented address or send link.
  Existing contributions, unions and letters keep their stored form.

## 0.33.0 — 17 November 2026

- We preserve each participant's life protection across identity merges. Existing
  disputed merges may now hide facts, crops and prose from public reader, demo and
  book output and refuse photo restoration. `instance check` advises which cards
  and death evidence conflict: record a reasoned `privacy.life_decisions` entry
  for the canonical person or undo the merge; correct death dates before birth.
  A death decision on an absorbed card alone cannot release the merged person.
- Books use a generic family-story title and report an omission when reader
  privacy removes the feed title. Host prose also retains Roman-month dates.
- We clarify that personal reader access grants the desk's accepted private
  family dataset, including living information except documents and addresses;
  service pages and correspondence stay owner-only and public output stays limited.
- We add deceased-only `photo-restoration` pairs: generated photographs with a
  one-tap real original, disclosed inventions, reader-selectable variants and
  append-only version recipes bound to both files. `feed restorations` lists
  recipes and their age for future regeneration; photo-treatment rules stay strict.
- We show a restored or treated photograph as a face with one caption, a quiet switch between
  variants named by the new optional version `label`, and one small line that opens how it was
  made: disclosure, invented details, model and date, comparison numbers and the recipe.
- A life line keeps a date span as a span ("≈1925 – 1941/45") in cards, tree, overview and feed
  reader chips; event lists show "1941–1945" instead of the first year alone.
- We keep an explicitly attributed cut-out with its corpus subjects instead of
  adding chapter participants; conflicting subjects refuse delivery and shared
  protected scans stay private. Withheld chapter media and game evidence now
  produce advice for the host and reader displays, also in plain-text pages.
- We preserve numeric historical dates, slash years and folio fractions in host prose.
- We pair real photographs with disclosed `photo-treatment` variants, binding the
  original, subjects and pixel dimensions. Living treatments require picture consent
  and remain local to the host; drawings keep their existing restrictions.
- We resolve person references against the working tree, including applied research
  contributions and explicit identity successors: records, versions, questions, letters,
  document cut-outs, privacy, search coverage, feeds and research packets use the same people.
- We let a contribution name an existing unnamed person with sourced name parts, retaining
  the earlier state in working history without adding and merging another card.
- We keep word-shaped identifiers in ordinary host prose. Explicit references and working
  locators are hidden with an explanation while the remaining text stays visible.
- A family question is addressed to a role (`host`, `relative`, `narrator`) or to one person
  of the working tree; any other addressee is refused with the known ids.
- Stored forms are unchanged. Existing unlinked records, contribution death events and
  identity-merge workarounds remain valid without edits.

## 0.32.0 — 17 November 2026

- We serialize family cloud commands, recheck personal entry immediately before upload, resume interrupted
  login transitions from non-data `.state` bookkeeping, and receipt inapplicable actions without blocking feedback.
- We keep agent-prepared correspondence beside family questions: recipient, sending and reply links,
  literal letters, named senders, sending history, original replies and researcher interpretations.
  The owner has a phone-first Correspondence page with copy, sent and reply actions through feedback.
  Agents prepare; people send. Shared-login publication omits correspondence pages, navigation and data
  and refuses its feedback actions; personal logins enable owner access. Reader roles and public reader
  demos cannot access correspondence. Local loopback desks remain owner workspaces.
- We withdraw correspondence and wait for CDN invalidation before switching to shared login, normalize
  protected paths, and retain unauthorized legacy actions without blocking feedback intake.
- Family commands create and update drafts, mark sending, preserve replies and their original files, interpret and close
  conversations. Researchers receive the family setting `host.correspondence_voice`, with a neutral
  polite default. Outgoing living-person details remain limited to names and kinship.
- A letter answered to the sender's own mailbox carries no follow-up address (`follow_up: null`); the page then
  says the reply returns to where it was sent from. The card labels whom the letter is about.
- This is a new optional stored form; there are no prior correspondence records to carry over.

## 0.31.3 — 17 November 2026

- We resolve sources across contributions in the same family, including mutual references, without
  depending on filename order. Rejected packages remain atomic and never reach a working tree, desk
  build or reader export. Whole-instance and selected-file checks now report their file, claim and cause.
- Hosts whose trees already omitted a contribution will now see a blocking `instance check` finding.
  Declare the missing source in a family contribution or evidence, or repair the named claim and rerun
  the check before rebuilding. Stored data forms are unchanged.
- Unknown references list known ids, including version people and record subjects.

## 0.31.2 — 17 November 2026

- We build the independently read Russian fictional family at `/ru/` alongside the English demo in one
  Pages run. Its public reader keeps the chapter, literal document excerpt and child question while
  excluding living-person prose. We corrected unsupported story details and an unconfirmed imported
  death on the tree; the original GEDCOM remains intact. Two Russian screenshots accompany the demo.
- Static demo export accepts `--public-reader` to wrap the accepted public projection. The English
  reader shell and accepted family inputs stay unchanged; language links appear throughout the Russian
  desk and on the English investigation pages. Builds use disposable family copies and never attest.
- We order contribution updates by recorded date and source ids rather than file modification times,
  so a clean archive on Linux preserves the reader bytes inspected on Windows.

## 0.31.1 — 17 November 2026

- The first-family tutorial and installed journey use one fictional Bea and Ben Example family, with
  deceased document subjects and non-word identifiers. The bundled inputs reach reader review without
  changing their meaning; the guide names files the agent authors and the commands that check them.
- Host-text refusals name the conflicting internal identifier and its declaration file, including
  collisions in input prose that previously disappeared silently. Stored family inputs are unchanged.

## 0.31.0 — 17 November 2026

- New method skill `on-site-researcher` and a researcher mode for it: when the open sources of a place are
  read and the needed book lies in a reading room, find a person who works in that archive through the
  regional forum, order by a unit, and take the returned photograph in as a paper with a reading of its
  own. The host posts, pays and sends; a helper's "nothing found" counts only with its coverage. The forum
  card of the Belarus and Podlasie pack describes the route as reported.
- README names the neighbouring open projects and where Familiar stands among them, and says that the
  maintainers also run research for families who ask.
- Documentation corrected after an independent cold walk: reading confirmations under `.state/` are not
  derivable and belong in the backup; a lost `.secrets/` is restored from the backup, not by a new
  provision; which inputs an agent writes as files and which only through commands; the fonts' licence
  beside MIT.

## 0.30.0 — 17 November 2026

First public release. Install tags, not `main`; see `docs/upgrading.md` for what a release promises.

- The place where a dead person lived stays in the family's pages. A residence was treated as an address:
  the event was dropped and its place name was removed from every text of the delivery, birth places and
  story sentences included. Explicit address events and every residence of a living or unknown person
  remain excluded as before. No stored data changes; rebuild the reader or desk.
- `desk export-demo` writes a fictional family's desk as a portable static site: relative links, the
  fiction mark on every page, feedback and adding people switched off. It refuses a family that is not
  declared fictional or whose reader pages are not confirmed. `scripts/build_demo_site.py` builds the
  Ferrolho demo this way; the build is checked on Windows and on Linux.
- The Ferrolho demo carries a recorded reading of its reader pages, so `reader export` works on a clean
  checkout.
- Documentation for outsiders: agent-first README, `docs/first-family.md` (installation from a tagged
  release), `docs/architecture.md` (engine, family instance, host environment; where each setting and
  secret lives), `docs/upgrading.md`, `CONTRIBUTING.md`, `SECURITY.md`. A changed stored form now ships
  its carry-over command and a changelog line starting `Data:`.

## 0.29.7 — 16 November 2026

- Coverage excludes analytical comparison tables and explicitly labelled source maps from personal record visits. Accepted tree facts and identity decisions resolve record links through exact document references; contextual participants remain separate from principal candidates.
- Local reviews (`query.mode = "review"`, including legacy `query.review`) assess individual record links without adding source passes, strength, forms, findings or availability. A completed assessment leaves incomplete search coverage open; contradictory accepted links remain conflicts. Search and record forms document the distinction.

## 0.29.6 — 16 November 2026

- A display snapshot no longer fails on a search journal row whose `question` names a version. A version citing `search:<id>` adopts the journal into the snapshot, but versions themselves stay out of it, so the reference is checked on the whole instance only.

## 0.29.5 — 16 November 2026

- Coverage puts unresolved record identity and participant roles before repeat searches. Explicit people survive dictionary mismatches; contrary birth/parent data and previous other-person assessments remain visible.
- Search forms carry editorial annotations, sex, person and episode applicability separately from spelling. Catalogue writing and prefix semantics constrain missing forms; unknown writing is marked explicitly. Estimated age and dated family episodes improve source priorities.
- Latest source refusal is independent of the strongest earlier outcome; a stopped search waits for access even when a document page opens. Dubious composite or substring queries cannot become negative coverage.
- Version arguments against a hypothesis may cite a saved zero with positive control and actual read scope; uncontrolled zeros and access gaps remain unusable.

## 0.29.4 — 16 November 2026

- The private desk rebuilds the "Where we looked" block when search journals, records, versions or the family variant dictionary change. The reader cache key covered only the display snapshot, which holds no journals, so a fresh recheck kept the old strength on the desk.

## 0.29.3 — 16 November 2026

- Memory intake drops a bridge label (`placeholder`) from an existing person once a told name arrives. The reader showed the label instead of the name and treated the person as unnamed: no search hit, no chip, no kinship path.

## 0.29.2 — 16 November 2026

- Coverage distinguishes surname searches in a place and period, individual searches, result rows, read records and explicitly established identity. Existing records and corpus records count as source visits without promoting name matches to identity.
- Planning reads dated family notes, catalogue parish/episode context and source language/script constraints. Textual positive controls survive; missing forms and incomplete plans remain visible independently of executor strength.
- FamilySearch Tree, Records and Full Text have separate coverage cells; ambiguous old labels remain unclassified. Private person cards show result rows and identity separately, with a short list of missing forms and the full list in JSON.

## 0.29.1 — 16 November 2026

- Legacy search imports assign stable provenance ids, normalize explicit counts and preserve unrecorded outcomes and incomplete zeros without claiming negative evidence.
- Coverage includes pack/family surname and given-name variants and query masks; living or possibly living people leave the recheck queue and are counted separately. Source URLs resolve by catalogue domain, transport labels without a source are counted aside.
- Expanded the Belarus–Podlasie source catalogue with forums, memory, diaspora, cemetery and library resources, keeping unknown dates and access gaps explicit.

## 0.29.0 — 16 November 2026

- Host-private reader: the person panel has a "Where we looked" section (ru, pl, en, sv)
  from the search coverage matrix. A folded line ("Looked in 12 sources · found in 3 · worth another look: 2"),
  then each source with its outcome mark (found, zero with control, zero without control, no access),
  the latest pass date, strength in dots and the name forms tried; "Not looked in yet" lists only sources
  that fit the person's epoch and region. The block is declared host-private only and never reaches the
  public projection; without a journal the section is simply absent.
- `research coverage --family --json` carries each person's `distance` from the tree root, so a display can order
  rows by closeness.

## 0.28.1 — 16 November 2026

- Search migration accepts an explicit executor map, enriches previously migrated
  rows, and refines question-only people using names and variants.
- Archived SEARCHES journals are copied with source line provenance, deduplicated
  across archives and repeat runs; malformed rows are counted without changing originals.
- Coverage suggestions account for catalogue epoch and geography, counting
  unsuitable cells separately while retaining the searches actually recorded.

## 0.28.0 — 16 November 2026

- Search coverage ledger. A search journal row now names the people it was run
  for (`people`, tree ids), a source of the region catalogue (`source`) and the
  executor as `by` = `{agent, model, effort}`. `familiar research
  migrate-searches` carries old rows over once (dry run, `--apply` to write):
  people inferred from the question and the names searched, the catalogue
  source by alias, domain or the address asked, `by` parsed; the written text
  stays in `source_as_written` and `by.as_written`, uncertain matches stay empty
  and are counted.
- `familiar research coverage`: person-by-source matrix (found, zero with
  control, zero without control, access gap, never looked; forms read and
  missing; first and last pass; who and how hard), `--person ID` card,
  `--recheck [N]` queue by usefulness, `--json`, `--save` (stores
  `coverage.json` in the instance state directory for the desk and display).
- Pass strength 1-4 from model and effort: setting `research.search_strength`
  (region and family layers) and `research.recheck_strength`.
- `instance check` advises on journal rows outside the ledger form; forms
  `search` and `search-request` and the demo family show it.

## 0.27.0 — 16 November 2026

- Prepare editable memory intake drafts from desk feedback; accepted feedback gets a read receipt without replacing existing receipts.

## 0.26.3 — 16 November 2026

- Desk "Add a relative": the chosen "Relation" button now stays highlighted
  (the sheet's general chip rule outranked it); a double click on a chip no
  longer selects its text. Narrator feedback.

## 0.26.2 — 16 November 2026

- Desk logins: the first-sign-in password is now plain — the login's letters
  and the person's birth year, or the current year when no birth year is known
  (`helena1925`). The old 28-character random string with `!` and `_` broke on
  double-click selection and on typing, and a relative never got in. The user
  pool asks only for six characters with no required classes, so the new
  password chosen at first sign-in is not refused either; a temporary password
  now lasts 30 days. Hosted desks need `desk provision`, then `desk user reset`
  for logins still waiting for their first sign-in.

## 0.26.1 — 16 November 2026

- Desk builder: the place for a parent sits above the person and names the
  missing one ("Mother" when the father is known); the partner place says
  "Wife" for a man and "Husband" for a woman (also in the card's actions); a new
  child joins the end of the row of children already drawn, as a plain plus when
  the row is full. Tree cards carry their person id (`data-person`), so the desk
  no longer guesses people by the names shown.

## 0.26.0 — 16 November 2026

- Desk: a visible "Add a relative" button by the tree and "Add relatives" in a
  person's card (father, mother, brother or sister, son or daughter, husband or
  wife, other kin in own words, and "whose relative" to pick anyone in the tree)
  open a one-person form with plain fields: names, birth, living or died, how it
  is known, a note. "Add another" follows; many people at once still go as a
  table. The addition keeps the fields as `new_person` beside a readable text and
  stays pending for the researcher. Hosted desks need `desk provision` for the new
  receiver before publishing.
- A repeated research contribution no longer revives a fact the family retired;
  a malformed index answer is no longer counted as a zero (false negative), a
  counted partial answer keeps its coverage; GEDCOM PHRASE text is kept verbatim
  with its context.
- Region pack and reading method updated from the kinship research guide v1.46
  (Lithuanian metrikai path, corrected OBD fields, re-reading a narrow period
  before widening a search).

## 0.25.1 — 16 November 2026

- Zooming out always leads back to the wide tree: after all generations of a
  person are open, the wheel, pinch and minus button return the way the
  gesture came in, or, for a person chosen by a click or a link, step towards
  the family's home people one relative at a time. Clicks keep working.

## 0.25.0 — 16 November 2026

- Give every person without a recorded birth year an orientation year: the
  first known child minus the usual age of a father or mother at a first child
  in that era (setting `tree.first_child_age`, regions and families may change
  it), else a spouse, brothers and sisters, then parents. Shown in italics as
  "≈1895" with its grounds under the card's evidence; never stored, and a
  recorded year replaces it. The whole-family view places people by it too.
- Draw the father on the left and the mother on the right: parent links
  without a recorded role take it from the parent's sex.
- Zooming out past the last generation no longer swaps the tree for the
  whole-family view; that view opens from the corner miniature only.
- Show birth and death years that research recorded as typed events.

## 0.24.0 — 15 November 2026

- Return the tree to a window around one person, with the corner miniature of
  the whole family by year and generation levels; the flat map of 0.19–0.21 was
  unreadable on a phone and hid the connections. Marks and link weights stay.
- Zoom the tree in people: wheel or pinch outwards adds generations as the
  gesture goes and then opens the whole family; inwards over a person moves the
  tree to them and keeps their visible branch, with a button back.
- A two-finger pinch on tree cards no longer opens the add-relative sheet.

## 0.23.0 — 15 November 2026

- Let chapter authors select up to four document crops for children.

## 0.22.2 — 15 November 2026

- Carry relationship decision confidence and weight into the working graph.

## 0.22.1 — 15 November 2026

- Give the reader page an empty icon so the browser console stays clean.

## 0.22.0 — 15 November 2026

- Count the family's own imported tree as firm family memory: a green check with
  the grounds "from the family tree" (setting `tree.import_is_family_memory`,
  on by default; research additions still need a document or firm testimony).
- Read a document mark without a check as "documents exist, they do not confirm
  the facts": muted on the map, stated on the full card.
- Fix the desk add-person script: a duplicate `identity` name stopped it from loading.

## 0.21.0 — 15 November 2026

- Lay the tree out as one compact map of all groups (nested branches, childless
  children folded into columns, cross links drawn lighter); open on the whole
  tree or, when that is only dots, on the neighbours of whoever is looking, with
  no card until a person is chosen and a way back to the whole tree.
- Keep zoom smooth on hundreds of people; names stay readable at map scale.
- Check firm family testimony also when the family's answer is saved as a record.
- Show an unnamed connecting person's placeholder exactly as the family data has it.

## 0.20.0 — 15 November 2026

- Let the family owner issue, reset, enable, disable and remove personal desk
  logins on Access, with tree search and a one-time password handoff.
- Verify the current owner and revocable session in every administration call;
  scope Cognito/KVS rights to this desk and provision its pinned signing runtime.

## 0.19.0 — 15 November 2026

- Navigate the whole family tree as a map; selecting a person keeps the map in place.
- Mark firm family testimony or documentary confirmation with a check; explain its basis on the full card.
- Correct unnamed connector evidence and singular English generation wording.

## 0.18.0 — 15 November 2026

- Let a reader attach a correction directly to a life event in the growing tree.
- Render unnamed hypothetical connecting people compactly, using their children’s
  clan form when it can be determined and keeping the explanation on the card.

## 0.17.1 — 15 November 2026

- Keep incidental login-page requests from replacing OAuth state/PKCE; carry person IDs only in signed JSON, without HTTP-header character restrictions.

## 0.17.0 — 15 November 2026

- Show attributed family-memory and documentary origins, evidence-based confirmation,
  linked documents and a growing-tree summary in the reader.

## 0.16.0 — 15 November 2026

- Opt published AWS desks into host-created Cognito personal logins with reader
  and owner roles, managed password changes/recovery and revocable edge sessions.
- Add desk user commands and initialize reader kinship from the login's person;
  readers retain their own choice and send remarks with a verified author.
- Keep shared-login publication as the default and loopback viewing unchanged.

## 0.15.0 — 15 November 2026

- Show anonymous search coverage in the investigation: known and checked sources,
  first journal appearances, working-day bars, repeat passes and source categories.
  Normalize common aliases and domains only while counting existing journals;
  collectors and search forms acquire no new steps, fields or checks.
- Keep the remark sheet usable after scrolling an investigation past its header.

## 0.14.0 — 15 November 2026

- Compare and choose clan surname forms by birth names, excluding explicit married
  names and untyped names shared with a husband. Preserve literal source names
  and report genuine paternal spelling differences in full instance checks.
- Share the page top across reader and investigation screens, reserving space
  for unavailable controls. Combine work totals in the investigation and omit
  zero values.

## 0.13.0 — 15 November 2026

- Use one lower navigation, private label, version and remark entry across the
  reader and investigation. Open remarks on the first click without scrolling;
  dismiss and resume drafts with a visible unsent-text indicator.
- Put alternative outcomes beside research volume. Require a recorded browser
  walk at desktop and phone widths for interface acceptance; provide a reusable
  walk sheet in the reviewer method.
- Render a translated feed period as text so the stories screen remains usable
  with a language-keyed reader delivery.

## 0.12.1 — 15 November 2026

- Keep one installed journey and weighted core data, privacy and install checks.
  Drop presentation and method lint requirements; time overruns only advise.
  Core contracts remain authored with code; surface contracts are optional.
- Use safe defaults for malformed presentation preferences while keeping privacy
  configuration and trust modes strict.

## 0.12.0 — 14 November 2026

- Keep tree cards to names, life years and birthplace. Store one reversible clan
  surname decision, preserve each person's documentary spellings, derive a
  surname only for an unambiguous named father from his children, and report
  undecided paternal spelling differences without blocking the reader.

## 0.11.0 — 14 November 2026

- Keep collector record and journal form findings separate from display readiness;
  validate and watch adopted research dependencies, with strict own-path checks
  and one unknown journal numeric-field finding per file and affected-row count.

## 0.10.0

- Investigation shows recorded weight shifts, all alternatives and rejection arguments, cumulative source coverage and paginated work without dates. Question remarks retain their question ID; privacy, navigation and feedback share one lower row.

Engine numbers follow the rule in `AGENTS.md` ("Engine version"). Each desk build
records the number it was built with in the family's `.secrets/desk-build.json`.

## 0.9.0 — 14 November 2026

- Add language-pack kinship words, qualified tree paths and an offline kinship
  glossary with examples from the permitted reader graph (Russian, Polish, English).

## 0.8.0 — 14 November 2026

- Add remarks from every desk screen, precise page and reading context, persistent
  drafts, browser-owned receipts and researcher replies. Invite unnamed relatives
  to be named through the same inbox. Move the private label and engine version
  to the lower edge. Cloud receivers require `desk provision` before publishing.

## 0.7.0 — 14 November 2026

- Keep unreferenced collector captures and archive bytes outside snapshots and
  watches; retain referenced-file race checks and the full public corpus gate.
  Compile host text identifier checks once for quick summaries on large families.
- Serve pinned checked desks over persistent HTTP with conditional browser
  caching and cheap corruption checks. Both local servers accept localhost names;
  local desk feedback accepts consecutive messages without a cooldown.

## 0.6.0 — 14 November 2026

- Add `reader book`: an offline A5/A4 HTML book with one replaceable stylesheet,
  full or children's text, document crops, original readings and chapter-end
  grounds. Admission reuses current independent reader attestations and the
  chosen public or host-private privacy projection; omissions are counted.
- Private reader previews can save review tickets for the exact local bytes.
  Existing private reader delivery remains available without book acceptance.

## 0.5.0 — 14 November 2026

- Expand the Belarus–Podlasie pack to 51 sources with dated provenance and
  explicit unknown-year gaps. Pack answers retain unknown-year source candidates;
  Polish and Latin record-reading cues are available by selected language.
- License the engine, method and own pack texts under MIT; carry third-party
  notices with wheels, reader shells and desk sites. Neutralize reader storage
  keys and remove private implementation instructions.

## 0.4.0 — 14 November 2026

- `research replay` exposes offline capture replay with full request/capture
  forms and actionable recipe/permission refusals. The separate module entry
  is removed. Complete documents, chapters and evidence forms match file containers;
  malformed containers name the file and repair example.
- Text pages and family summaries report current reader confirmation separately
  from pending feed review. Duplicate source declarations name both files and
  explain intake ownership; PRD and README describe actual search and language defaults.

## 0.3.0 — 14 November 2026

- Publication is optional: absent `[publication]` or `target = "none"` keeps work
  local. Desk build/serve ignore cloud settings; cloud commands require explicit
  `aws` before any disk mutation or external process, including publish --build.
- AWS failures explain missing CLI/profile and deployment state recovery;
  an unbuilt local desk points to build or serve --build.
- `method list` and `method show role/skill <id>` read bundled method resources
  without family discovery or startup maintenance. A thin portable Agent Skill
  and local-first documentation describe the installed path.

## 0.2.2 — 14 November 2026

- Person edits reuse build-local input reference indexes and resolve each distinct
  dependency path once per check. Publication validates restricted-term forms
  once; semantic text findings, privacy, gate and review checks remain in place.
- Person normalization, prose/date adaptation and card serialization run in
  memory instead of reading thousands of cache files. Feeds, documents and media
  keep checked reuse; privacy and full graph validation remain authoritative.

## 0.2.1 — 14 November 2026

- Desk builds reuse their checked private reader and unchanged media. Person
  projections and feed materialization are cached by content; shell and desk
  wording changes do not export family data again. Privacy and gate checks remain
  authoritative; the engine release number is recorded without clearing the cache.

## 0.2.0 — 14 November 2026

- Engine-owned reader sources and a locked Bun build reproduce the packaged shell
  without a pilot checkout; all six existing delivery files retain their exact bytes.
- Instances pin `[engine] version`; checks and desk builds warn on a mismatch.
  `instance record-release` records the installed wheel's SHA-256 and engine commit.

## 0.1.0 — 14 November 2026

First numbered state of the engine: everything before it shipped as 0.0.1.

- Number visible: `familiar --version`, `instance check`, a small mark in the desk
  notice bar and in the private reader's notice; desk builds record `engine_version`
  and `built_at`.
- Desk tree: ghost places are a builder mode. Ordinary viewing shows none; a quiet
  toggle beside the tree controls turns it on (automatic for a family under three
  people); long-press or right-click on a person still adds a relative. Ghost words
  fit any person: "Сын или дочь", "Муж или жена", "Родитель".
- Version heat by meaning: отпала, ослабла / маловероятно, возможно, окрепла /
  скорее всего так, почти наверняка, подтвердилась; "ослабла" and "окрепла" only
  after a real fall or rise. Log events: ослабла, отпала, окрепла, подтвердилась;
  versions born together on one branch are one row ("Новые версии: 6").
- Large families: desk listings compare names in one order (case broke the check
  on Windows); private display snapshots bind research originals that are only
  tested for existence by name, size and time (pilot: 3.1 GiB became 262 MiB);
  desk history reads one git log instead of one process per commit.
- Desk journal dates in family words; one-row phone menu.
