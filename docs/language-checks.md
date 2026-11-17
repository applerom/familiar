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

Still incomplete: first-use state across chapters, inflected preferred terms,
lineage aliases, sentence abbreviations and full term explanation matching.
The legacy family migration inventory is not executable settings.
