# Language checks

The family gate reads shared `language.lexicon`, `text`, `writing`, and `terms`
resources through Registry for each configured text language. Literal quotations
are exempt where the pack requests it. Heuristic matches have review certainty;
they do not establish historical or linguistic errors and never block publication.
Unavailable resources appear in feed coverage under `language_unavailable`.

Families and feed tables may set `[language_settings.<tag>]` containing declared
setting ids and values. These values override the base settings for that exact
text language. Unqualified `lang.preferred_terms` applies to the source language;
without an explicit language scope the historical resolution API is preserved.
Other base settings remain language-independent defaults, with per-language overrides.
Unknown setting ids, types and disallowed layer scopes still fail at load time.

Names use the instance's configured languages, including a single arbitrary tag.
An optional `names.json` entry `_surname_forms.<tag>` selects `surname`, `gender`,
`paradigm`, and `case` (default `nom`). The builder inflects only that explicit
regular class from the selected language pack. Missing classes retain the authored
name. This does not infer gender, identity, transliteration or a widow's surname.

## Name forms by reader language

A tile and a card name a person the way the reader's language would at home; how a
document spelled the name stays in the card's "More", with the document.

- Keep every document's spelling as written in `names[]` with `type` `recorded`,
  `as-written` or `indexed` and its `provenance` (old letters, the act's case,
  Latin). These never reach a tile.
- The family's main-language form is `name_forms[].display` in
  `tree/identity-decisions.json` (with `evidence` and `sources`). A form for another
  reader language goes beside it in `by_language`, e.g.
  `{"person": "...", "display": "Фёдор Корнеев", "by_language": {"pl": "Teodor Korniejew"}}`.
  A researcher may instead write such a form as a `names[]` entry with `lang`
  (not a document type); a decision wins over it.
- Polish or Latin act → the Polish form of the act's name (Franciszek, not
  Franciscus); a Russian-only record → the accepted Polish form (Викентий → Wincenty).
  A list's diminutive (Янук, Marysia) becomes the baptismal name (Jan, Maria) on
  the tile; the diminutive stays in the record.
- Without a form in the reader's language the tile shows the family's main name.
  The engine does not transliterate. `instance check` hints (never blocks) at a
  main-language tile with old letters, another script or a probable case ending.

## Family title and card translations

`[family].title` is one text or a table by family language that includes the main one,
e.g. `title = { ru = "...", pl = "..." }`; the reader heads the page in its language.

A reader language without a translated text shows the family's main language
(`source_language`), then English, then Russian: never a third language before the family's own.

Card texts follow the main language through `tree/translations/<lang>.json`:
`{"schema_version": 1, "language": "pl", "texts": {"<exact main-language text>": "<translation>"}}`.
The reader export turns a matching card summary, fact label/text/basis, event and card place and
source title into a language row; a generated "date · place" line is matched part by part. A text
whose source changed no longer matches and shows the main language until it is translated again,
so the file needs no freshness marks. A document's reading is not a card text and stays as written.

Still incomplete: first-use state across chapters, inflected preferred terms,
lineage aliases, sentence abbreviations and full term explanation matching.
The legacy family migration inventory is not executable settings.
