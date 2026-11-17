# Familiar design — rollout

13 November 2026. Direction: `DIRECTION.md`. The reader shell has one source, `reader-src/app/*` (`family.css`, `feed.tsx`, `tree/*`, `i18n.ts`); `reader-shell/` here is its build. Every step lands in the shared source; run `bun run reader:shell` from `reader-src/`, then `uv build --wheel` at the root to deliver it.

Acceptance for every step: screenshots at 390×844, 768×1024, 1440×900 and 1920×1080 of the same scenes as the mockups, compared side by side with `mockups/*.html` at the same widths. Capture the fictional demo scenes at those widths; store review evidence outside the engine repository.

## Day one — no restructuring, biggest gain for the first impression

Each item is a small, separately reviewable change. An executor can do them from this list.

1. **Chapter picture whole, never cropped.** `.feed-pic`: drop `aspect-ratio:16/10` and `object-fit:cover`; image `width:auto; max-width:100%; max-height:min(70svh,640px); object-fit:contain`, centred on a `paper-deep` mat. Today at 1440×900 the frame is 1440×432 (16:10 capped at 48dvh) and the picture is cut to a 3.3:1 strip. Keep `SpotFrame` working: wrap the `<img>` in an inline-block sized to the image so spot coordinates stay relative to the picture, not the mat.
2. **Generations graph: one tap goes.** `tree/overview.tsx`, dot click → `go(id); onClose()` directly; keep the hover card on wide screens. Remove the `ov-card` button (`labels.tapAgain`). Add an undo chip "← к {prev}" for six seconds; Back also works.
3. **Keys and turning.** `feed.tsx` key handler: `Space` no longer calls `next()` (it must scroll); `←`/`→` stay; `Esc` stays. Remove the invisible `.feed-zone` side areas. At the end of `.feed-text`, a "next chapter" card with year, title and one line (data is in `feed.chapters[i+1]`).
4. **Tokens and faces.** Add `tokens.css`; map the existing names (`--paper`, `--ink`, `--muted`, `--line`, `--green`, `--amber`) onto roles. Ship Literata (subset to Latin, Latin Extended, Cyrillic; woff2 in `mockups/fonts/`), set story text, titles and names in it; retire Prata. Story size 19 / 20 / 21 px, column 680 px.
5. **The feed is paper, not night.** Remove the forced dark `.feed-viewer` (`background:#0f1a16`, white text); it becomes the evening theme later.
6. **Header.** Family name + mark. Private delivery has a small chip "Только для семьи", supplied by `src/familiar/reader/server.py`; desk framing is assembled in `src/familiar/desk/build.py`. Keep the private notice visible on every HTML screen.
7. **Empty states.** Hide tabs with nothing in them (Рассказы, Фото on a first-day family). Replace "Рассказы появятся здесь…" with what the Familiar is doing now, when the engine can say it; until then, hide.
8. **Words.** Reader-facing labels in `i18n.ts`: `version:'Наша версия'`, `hypothesisTitle`, the `?` badges on tree cards → dotted connector and margin note only. Phrases like "со слов оператора", "мать рассказчика", "ждут подтверждения" come from engine wording (reader text built from intake) — fix them in the engine's reader wording, not in the shell.

## One to two weeks — reshaping the shell

These change structure. They need the designer's own screenshot loop, not only a spec.

- **Feed as a page.** From a modal over the tree to a routed page: `#/read/{feed}/{chapter}`. Chapter = vertical page; contents rail and margin rail at ≥ 1200 px; floating turn bar on phone; reading progress line; "Продолжить" memory.
- **Margin notes.** Today's `more` / "Подробнее" become notes anchored to paragraphs (engine: the chapter needs paragraph anchors for its notes; until then, notes follow the paragraph they belong to as collapsed "На полях" on phone and in the margin on wide).
- **Home as a cover.** Default route = family cover (title, lead, continue, books, people, what the Familiar is searching), not the tree. First-day variant from `mockups/home-day1.html`.
- **Tree cards.** No initial-letter avatars; name in Literata, years and place in Manrope, line colour as a left rule; a photo, when present, as a small print. Controls relabelled ("Поколений 2 3 4 Все", "К себе"). The fade-in on load goes; the hint toast becomes a one-time line.
- **Document viewer.** Tap on a cut-out opens the full sheet with the cut outlined, pinch-zoom, reading beside it on wide and below on phone.
- **"Аа" menu and evening theme.** Language, text size, Детям / Всем, evening; persisted per reader.

## Later

- Desk: the investigation as a live branch map and adding people in the tree. Spec, data contract and a one-day first step: `DESK.md`; mockups `mockups/desk-show.html`, `mockups/tree-add.html` (`desk.html` is superseded).
- Picture metadata in the engine: `kind: drawing | photo | document`, `focal`, `crop: allowed`, mat colour sampled at export. The shell obeys; it never guesses.
- Final mark and favicon set; Polish, English and Swedish checks of every label length.

## Who does what

- **By precise spec (executor following a precise visual spec):** day-one items 1–7, the tree controls relabel, hiding empty sections. Each with before/after screenshots at four widths.
- **Designer reviewing rendered screenshots:** the feed page and margin notes, the home cover, tree card visuals, the evening theme, the mark. Judgement items: they are accepted by looking, not by a test.
- **Engine owner:** reader wording (item 8), paragraph anchors for notes, picture metadata, "what the Familiar is doing" feed for the home page.

## Risks

- One source for installed readers and desks: a regression affects both. Ship day-one items behind no flag but one at a time.
- Literata variable files are ~285 KB each after subsetting; if it matters, ship static 400 and 500 roman plus 400 italic (~150 KB total).
- Games and spots (`SpotFrame`, `play.tsx`) assume the picture fills its frame; test a chapter with spots and a panorama after item 1.
