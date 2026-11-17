---
name: drawing
description: Draw one picture from a finished shot card: clear every reference before it reaches the generator, generate within a fixed number of attempts, check the result against the card in full-size crops, and store it as a reconstruction ready for a blind check.
---
<!--
START_MODULE_CONTRACT: MOD-SKILL-DRAWING
PURPOSE: Let an artist of any family turn a shot card into a picture with a host's image model, so that nothing private reaches the model and nothing drawn passes for a portrait or a record.
PRD_REF: docs/PRD.md#PIPELINE
INVARIANTS:
- every image bound for the generator is cleared against the tree before the first generation, and a photograph of a living person or a child is removed [review: cold reviewer]
- attempts are bounded, and a gross error that repeats sends the card back instead of another attempt [review: cold reviewer]
- the stored picture carries the fields the engine's reconstruction and living checks read, and never a portrait or document role [review: cold reviewer]
- the drawing reaches a mark only after a blind check by another hand [review: cold reviewer]
- the skill states what it needs from the host environment and names no generator, model or service [review: cold reviewer]
CHANGES_WITH:
- MOD-ROLES-ARTIST (names this skill as its work)
- MOD-SKILL-SHOT-CARD (the card is this skill's only brief)
- MOD-SKILL-BLIND-CHECK (receives the drawing)
- MOD-CHECKS-ENGINE (checks generated-not-portrait and living-protected read the stored fields)
- MOD-CHECKS-PRIVACY (subjects of a generated picture)
- docs/gate.md (image metadata refused at publication)
:END_MODULE_CONTRACT
-->
# Drawing

A drawing invents or reconstructs a scene; a `photo-treatment` processes the same real frame, with its original and explicit disclosure (`forms/photo-treatment.json`).
For treatments, preserve subjects and dimensions; a living subject stays in the family display, never public output. This does not authorize sending a living photograph to a generator.
Never transplant or blend faces; the author and reader verify unchanged features, which pixel dimensions alone cannot prove.

## Восстановление снимка

Когда человек умер и настоящий снимок есть, мы можем восстановить живую,
резкую цветную фотографию генератором: `photo-restoration`, а не `photo-treatment`
и не новый документ. Сначала подтвердить смерть всех людей кадра и права на
оригинал. Живой или неизвестный статус запрещает генерацию и любой показ,
включая местный кабинет хозяина, без исключений по согласию.

Сделать до трёх попыток. Каждую уменьшить до размера оригинала и размыть
для сопоставимой резкости; сравнить позу, контур лица, расстояния между
чертами, причёску, одежду и фон. Записать число попыток, выбранную попытку,
ширину сравнения, радиус размытия и среднюю абсолютную разницу интенсивности
0–255. Числа помогают повторить сверку, но не доказывают сходство лица.
Выбрать ближайшую к кадру, а не самую красивую. Спорное направление взгляда
или другую неразрешимую деталь сохранить отдельными вариантами.
Не предлагать бледную раскраску размытого кадра как готовый результат.

Нельзя пересаживать или смешивать лица, добавлять улыбку, знаки отличия,
форму или детали, которых нет на кадре, выдавать генерацию за оригинал.
Сохранять позу, одежду и фон; цвета и достроенные черты назвать в `invented`
и в подписи. Оригинал всегда рядом одним нажатием. Подпись под оттиском
исключить через `recipe.crop`, сам оригинал не менять.

Форма — `forms/photo-restoration.json`; `ours.kind: photo-restoration`, `id`,
`primary` и `versions`. У каждой версии свой файл, подпись, раскрытие и рецепт:
исходный кадр, SHA-256 обоих файлов, модель с ревизией, дата, точный запрос
или постоянная местная ссылка на него, список додуманного, числа сверки и
номер версии. Необязательное `label` версии (по языкам, как подпись) — человеческое
название варианта для переключателя, например "Смотрит в сторону"; без него
читатель видит "Вариант 1". Старые файлы и версии не перезаписывать. Все варианты доступны
читателю; основной открывается первым. Список для будущей пересборки:
`familiar --root FAMILY feed restorations`. Генерирует среда хозяина, не движок.

The card is the authority on what the picture shows; you are the authority on
whether the picture shows it. You do not invent the scene again and you do not
fix the card in silence. Found an error in the card: record it, change in the
prompt only what does not contradict a fact, and send it to the director.

**Inputs:** the shot card whole, the feed's character sheet, one finished
drawing of the feed as a style sample; for a correction, the old file and the
recorded findings.

**Output:** the picture in the feed's media under a new version name, its
picture record, and a generation log.

## What the host environment provides

- An image model that accepts a text prompt and sample images, and returns a
  picture. Without one, this role cannot be held: say so and stop.
- A way to crop and resize an image and to strip its metadata.
- A reviewer who has not seen the card, for the blind check.

Which model, at what price and through which account is the host's choice; it
is not part of the method.

## Engine commands

Commands marked *planned* are not in the engine yet. Until they are, do the
same by hand from the files named in the brief, or with the host's tool for
it, and say which in your report.

| Command | Gives | State |
|---|---|---|
| `familiar rules for` | the resolved rules and settings of this feed, for the role `artist` with `--feed <id>` | present |
| `familiar tree person` | a person's dates and life status, to clear a photograph | present |
| `familiar feed refs` | every image of a generation log checked against the tree and the photo rights: living, child, unknown | planned |
| `familiar feed check` | mechanical findings, among them reconstruction and living-person checks of pictures | present |
| `familiar feed accept` | the stage `drawing` marked passed for current chapters | present |

## Order

1. **Plan from above.** Read the card and draw the plan in words: who stands
   where, who moves where, who looks at what. A plan that does not close
   (groups collide, a gaze target behind the head) goes back to the director
   before any generation: that is cheaper than three attempts.
2. **Clear the references.** List every image you mean to give the model: the
   style sample, the card's samples, sheets of characters, an old version.
   For each image that shows a person, run `familiar tree person` and write
   their current life status and age shown in the photograph. A living person, a child, or a
   person of unknown status: the image does not go. A photograph of a dead
   person goes only when the card names it as the face source. Write the
   cleared list into the log first.
3. **Choose the way.** New shot or new staging: draw anew from the prompt; an
   old file serves only as a sample of style and place. A local error (a cap,
   teeth, an envelope): edit the old file, saying what changes and what stays.
4. **Tell each sample its job.** "style, not scene"; "cut of the coat, not the
   coat". Keep the feed's style; do not pick a new one.
5. **Generate and look.** At most three generations per shot. Each time look
   at the whole, then at full-size crops. The same gross error twice means the
   card is wrong, not the luck: stop and return the card with the error named.
6. **Self-check against the card and the plan:** meaning readable in two
   seconds; one direction per group; each gaze lands, in space and not only on
   the flat picture; one light of the card's colour; only listed objects,
   whole, on the right side, in the right state; counts by crops; no letters
   or digits; the caption says what is visible. An edit redraws more than it
   was asked to: check the whole frame again after every edit.
7. **Store.** A new version name; old versions are never overwritten. Strip
   all metadata the model wrote into the file: publication refuses it. Write
   the picture record:
   - `kind`: `generated-reconstruction`, `reconstruction`: `true`;
   - `caption`: the card's caption, in every language of the feed;
   - `subjects`: the feed symbols of the people drawn, `[]` for none;
   - `ours` and `orig` when the card names an original;
   - never a `role` of portrait or document, never in the feed's documents.
8. **Log honestly:** file, scene, chapter, prompt, the cleared references,
   attempts, what was checked, what did not work, what could not be counted
   (a limb behind a body). Small remains are no reason for a fourth attempt;
   they go in the log.
9. **Hand over.** Run `familiar feed check <feed>`; then give the picture and
   the page title, nothing else, to the reviewer for a blind check. After a
   verdict of keep or fix caption, `familiar feed accept <feed> --stage
   drawing`. You never check your own drawing blind.

## Known failures

- **A one-detail fix is not local.** "Turn only the boy" moved the boy and
  redrew the crowd into a collision. Look at the movement of the whole group.
- **A ban that empties a thing.** "Blank clock face" gives a clock with no
  face; ask for "tick marks, two hands, a pendulum, no numerals".
- **Props for comfort.** A candle by day, a vase on a clerk's desk, a pen of
  the wrong century. Closed by the card's "nothing else"; check it.
- **Golden light at night; a face "in shadow" as a black hole.** Name colour
  and strength; ask for "the edge of the cheek in cold light".
- **Counted on a thumbnail.** A foal with five legs is invisible at that size.
- **Twins in a crowd.** All differ in face, age, height, clothes; no more than
  two in one pose.
- **The caption promises more** than the picture shows: fix one of them.
- **Conservative photo-treatment:** a generator repaints faces and letters;
  use a separate non-generative tool. For a generated photo-restoration, follow
  the deceased-only procedure above and disclose every inferred detail.

## Forks

- **No original exists.** The drawing stands alone; its sources say so.
- **The card asks for a face the references cannot give** without a living
  person's photo: draw the person turned away, and tell the director.

## In the report

Pictures drawn and attempts; the cleared references; what the card got wrong;
a section "What was wrong in the brief and the tools".
