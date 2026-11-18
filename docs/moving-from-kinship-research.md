# Move an ex-ussr-kinship-research case into Familiar

Point Familiar at the case directory containing the five UTF-8 CSV registers.
Keep referenced files inside that directory. Use a fresh destination if you want
to inspect the result before joining it to an existing family.

```sh
familiar instance init FAMILY --title "Family archive"
familiar --root FAMILY intake kinship-case CASE --id archive
familiar --root FAMILY intake kinship-case CASE --id archive --apply
```

The first intake command is a dry run. Read `counts`, `losses` and
`archive_only` before applying. New rows get IDs such as
`kinship-archive-person-p-0001`. The same ID and original bytes can be applied
again safely. Review a previous intake before giving a changed case a new ID.

| Case input | Familiar working files |
|---|---|
| People | Separate working cards, including namesakes and candidates. Birth and death estimates and identity notes stay as-written research metadata. `deceased`, `living` and `unknown` become explicit life decisions. Blank and unrecognized classifications receive unknown-life protection. |
| Relationships and claims | Each becomes a version with supporting and contrary artifacts. Parent/child, spouse and sibling links reach the tree when their roles can be represented. Contradicted links remain conflict versions at weight 0. |
| Artifacts | Corpus records with subjects, source details and literal names, dates and places. An optional `reading` CSV column carries a verbatim transcription. Put a scan path in `source_url_or_path` or use an optional case-relative `local_file` column alongside a URL. Familiar also recognizes the upstream `snapshot=` access-note marker. A saved file is checked against `sha256` when supplied. The summary stays separate from the reading. |
| Searches | The coverage journal keeps target IDs, source, query, scope and outcome. JSON filters may supply `coverage.years`, `coverage.forms`, `coverage.read`, `coverage.note` and the original `by`. Searches without executor metadata have unknown strength. Recorded zeros are uncontrolled and CAPTCHA is an access gap. |

Confidence chooses a point within the import weight band. These are Familiar
display weights. The original status and confidence remain available as written.

| Case status | Weight from low to high |
|---|---|
| `hypothesis` | 0.30–0.42, dashed tree link |
| `unresolved` | 0.15–0.28, weak version |
| `single-source` | 0.36–0.49, dashed tree link |
| `corroborated` | 0.55–0.75, solid tree link |
| `strongly-corroborated` | 0.70–0.90, solid tree link |
| `contradicted` | 0, conflict version |

Copies sharing an `independence_group` count as one chain. Corroboration with
fewer than two supported groups or with recorded contrary artifacts becomes
unresolved. Other relationship roles and ancestry cycles remain versions and
appear in the loss report.

The complete case is available under `imports/kinship-archive/case.zip`.
The case YAML, research-state notes, reports and any GEDCOM or unattached files
are ZIP-only. A mismatched scan stays in the ZIP and is listed in `losses`.

```sh
familiar --root FAMILY instance check
familiar --root FAMILY tree build --view working
familiar --root FAMILY research coverage --person kinship-archive-person-p-0001
familiar --root FAMILY family summary
```

Use the IDs from the working tree. Compare one record and one search pass
against the original case, then review any losses before continuing research.
For a fresh English instance, put `language_packs = { en = "demo-english" }`
before `[family]` in `familiar.toml` for `family summary` and the desk.
