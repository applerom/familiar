# Data guarantees: retained error and control

The contract is [gate.md](gate.md). The author narrowed the suite on 12 November
2026: one representative honest error and its control per data guarantee, plus
one installed memory-to-reader journey. This is not exhaustive route coverage.
All data are fictional. The checks below live in
`tests/gate/test_data_guarantees.py` and run in both levels.

| Guarantee | Honest error -> result | Control | Function |
|---|---|---|---|
| F1 exact local reference | shown document points at an unsaved record -> TRUST-01 refusal | local record and chapter resolve | `test_f1_shown_reference_resolves` |
| F2 subject closure | record names a living child omitted by the document author -> blocked | original deceased subjects pass | `test_f2_record_subject_cannot_be_omitted` |
| F3 living projection | living details in public output -> omitted; private residence -> excluded | family story and birth remain visible privately | `test_f3_public_name_and_kinship_and_private_address_exclusion` |
| F4 acceptance | weak status and weight labelled accepted -> blocked | strong finite weight, source, basis and decision pass | `test_f4_acceptance_requires_auditable_strong_grounds` |
| F5 declared projection | undeclared author field -> omitted | declared name survives | `test_f5_undeclared_reader_fields_stay_private` |
| F6 disclosure form | generated reconstruction assigned portrait role -> blocked | labelled adult reconstruction passes | `test_f6_reconstruction_cannot_be_a_portrait` |
| F7 coverage form | zero read presented as not found -> blocked | read coverage and explicit access gap pass | `test_f7_not_found_requires_read_coverage` |
| F9 trust modes | family switches trust mode off -> blocked | default modes pass | `test_f9_trust_mode_cannot_be_changed` |
| Review binding (class F) | author self-confirms, or confirms an old ticket after a text edit -> refused | independent inspection of unchanged bytes gives clean output | `test_f8_review_binds_exact_bytes` |

`tests/journeys/test_installed_engine.py::test_installed_engine` is the only
journey and only runs with `--full`: build one wheel, install it into one clean
environment, load bundled method/forms/packs outside the checkout, ingest memory
and a paper, author a page, inspect its exact reader bytes, record independent
reading, export and verify the clean reader generation. Feed document symbols
must become canonical people on this path.

Deleted: adapter matrices and spelling/surface variants; extra generation fault,
race and corruption scenarios; semantic worklist scenarios; own-item intake
variants; source demo journeys, merge/undo, one-person and language variants;
output baseline and its fixture; integrity of rules, packs, skill/role text and
examples; static writer/adapter scans; validator self-tests. These now belong to
the declared reviewer. No equality claim remains for a stored demo baseline or
for a private family output. Before/after counts are in the engine's git history (12.11.2026).

## 13 November 2026: share generation and review setup

F8 and mechanical review binding now use the same fictional family, inspection
and clean generation. Self-confirmation and changed-ticket refusals remain;
the changed text has summary permission so it actually reaches reader bytes.
Birth permission alone is then revoked, independently of the text review state.
The installed new-family journey and F1-F9 controls remain unchanged in scope.

Removed the second review-family setup, its duplicate clean-publication check,
and the extra checked read before the outdated-state check: `refresh_output`
already consumes the checked generation. These were repeated executions, not
additional data guarantees. No engine behavior or budget limit changed.

Measured before: fast 11.35 s, full 19.57 s; test/code 290/10034 = 0.02890.
After consolidation: fast 9.49 s, final confirmation 9.70 s; test/code 285/10034 = 0.02840 (5.3% below
the 0.03 ceiling). Full end-of-task run: 18.43 s (budget 22 s).

15 November value policy: no UI/spelling assertions or second print/world/game
journey remain. F6 is retained as data source fidelity: a reconstruction cannot
stand in for a documentary original; this is not a caption-layout check.
