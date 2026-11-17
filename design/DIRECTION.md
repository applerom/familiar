# Familiar — design direction

13 November 2026. Tokens: `tokens.css`. Mockups (invented families, open as files): `mockups/index.html`. Rollout: `IMPLEMENTATION.md`.

## The idea

**A family book with paste-ins.** In the first ten seconds a stranger should feel: *this is a family's book, someone made it with care, and I can simply start reading.* Not an app, not a database, not a case file.

Three layers follow from it:
- **The book** — typography, pace and paper of a good printed book. The story is the product.
- **Paste-ins** — documents and old photos sit on the page as physical inserts: a cut-out with its reading, a print with a white border. They are evidence, so they are never cropped or "aged".
- **Marginalia** — the Familiar's own voice lives in the margins, small and in italics: how we know this, what is still being searched. Technique is present but quiet, so readers see the evidence without engine terminology (`../docs/PRD.md`).

Rejected, one line each:
- *Family album* — photos lead, but most families have few; the story shrinks to captions.
- *Investigator's office* (boards, red threads) — turns living history into a trial; the living-history direction above excludes that framing.
- *Fantasy companion* (a creature, game chrome) — cute for children, wrong for grandparents and for hard history.
- *Museum/archive* (parchment, ornaments, sepia) — reads as dead history.
- *Today's look* (pills, initials in circles, toasts) — reads as a CRM.

## System

**Type.** Literata for everything one *reads*: story, titles, names of people and places (a book face built for long screen reading, variable optical size, full Cyrillic, Polish and Latin Extended, OFL). Manrope for everything one *operates*: buttons, labels, years in UI, counts (already in the shell). Prata retires: one display weight, no italic, reads as a wedding card. Scale: 12 · 13 · 15 · 17 · 19 · 23 · 30 · 40 · 56. Story body 19 / 20 / 21 px at phone / tablet / wide, line height 1.62–1.65, column 680 px (about 66 characters). Drop cap in ember on the first paragraph of a chapter only.

**Colour roles** (never raw hex in components):
- paper `#f6f1e7`, sheet, ink `#1f2a26`, ink-soft, ink-mute, rule — the page.
- act `#2f5b48` bottle green — links, primary buttons, focus.
- ember `#c8741c` (as text `#9a5512`) — the Familiar's light: "you are here", current chapter, reading progress, the mark. Never a button colour.
- version `#5f6490` slate violet — dotted lines and margin notes for what is not firm yet. No yellow "?" badges, no red.
- document paper / ink / highlight — a document stays paper even in the evening theme.
- six muted family-line hues; a line colour is data, never brand.

**Grid and shape.** 4 px base; page gutters 20 / 32 / 48. Wide reading: contents 240 · story 680 · margin 260, gaps 56. Radii: 4 inserts (paper is nearly square), 8 chips, 12 cards and buttons, 20 sheets. Two shadows only: lift-1 (cards, inserts), lift-2 (sheets, floating bars).

**Motion.** 140 ms press/hover, 220 ms sheets, 320 ms chapter turn and tree camera; one easing. Chapter turn: new page rises 16 px and fades in. No fade-in of whole screens on load (today's tree spends a second half-transparent: the first impression is a blank). Reduced motion: none.

**Mark and name.** A thin ink ring with an ember dot — a lit window seen from the road. Wordmark *Familiar* in Literata 500; "Фамильяр" only in prose. The family's name leads the header; the mark sits small beside it and in the footer colophon. The family owns the book; Familiar signs it.

**Evening theme: yes.** Reading aloud happens at bedtime. Same structure, swapped roles; documents stay paper. Follows the device, switchable in "Аа".

## Behaviour

**Reading a chapter.** A chapter is a page read top to bottom. At its end: a large "next chapter" card (year, title, picture, one line) and a small link back. Phone: no invisible side tap zones and no swipe to turn — both fight scrolling, selecting and zooming documents. A floating turn bar `‹ ☰ 3 из 6 ›` appears when the reader scrolls up or reaches the end. Wide: sticky contents on the left, margin notes level with their paragraph on the right; `←`/`→` turn chapters, `Space`/`PageDown` scroll and never turn, `Esc` returns to where the book was opened. Progress: a 2 px ember line under the bar for the chapter, "3 из 6" in words. Every chapter has a URL; reload keeps the place; "Продолжить" on the home page remembers chapter and scroll.

**Chapter picture on any screen.** Shown whole by default. Width = column (full bleed on phone), height ≤ 70svh on phone; on wide ≤ 640 px and short enough that the first lines of the story stay above the fold (≤ 100svh − 420 px); the slack goes to a mat in `paper-deep`, never to a crop. Wide: the picture spans story + margin and is centred on its mat. Cropping is allowed only for a drawing whose record declares `crop: allowed` with a focal point, and only in covers and thumbnails. Documents and old photos are never cropped, tinted, filtered or rotated; old photos sit as prints with a white border. A document cut-out runs the full column with its reading beneath; tapping it opens the whole sheet with the cut highlighted and pinch-zoom.

**A person anywhere.** A name in text, a chip, a tree card, a dot on the generations graph, a search result: one tap goes to the person — the tree recentres and the card opens. No intermediate "go to person" button. Instead an undo chip "← к Ирине" for six seconds, plus the browser Back. Dots get 44 px invisible hit areas; on wide screens hover shows the name.

**Back.** Every state has a URL. Back returns to the exact scroll position and open card; closing a book returns to where it was opened.

**First day.** Sections that are empty are not shown; the navigation grows with the family. A new family's home is a cover: the family name, a one-line promise, the people already known as a small sprout of the tree, what the Familiar is doing now, and — for the host only — one question with "не знаю" as a valid answer. Never "появятся здесь, когда будут записаны".

**Words.** No engine words in reader text: "оператор", "рассказчик", "наша версия", "ждут подтверждения", "?" badges. A person known only by relation is shown by that relation in italics ("мама Сергея"), with the host able to name her.

**Controls.** "Аа" holds language, text size (three steps), Детям / Всем, evening. Tree depth is a labelled segment "Поколений 2 3 4 Все" and a "К себе" button, not `− 3↑ + ⌖`. Hints are a single line that disappears after the first action, never a toast over the cards. The private state is a small chip "Только для семьи", not a brown banner.

**Floor.** Text contrast ≥ 4.5:1, targets ≥ 44 px, focus ring in `act`, OS text size respected, a chapter readable without JavaScript.
