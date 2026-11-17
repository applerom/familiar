<!--
START_MODULE_CONTRACT: MOD-READER-PROFILE
PURPOSE: Define the portable reader settings shared by a family export and a browser shell.
PRD_REF: docs/PRD.md#INSTANCE
INVARIANTS:
- the profile carries no implied real-family defaults [review: engine lead]
- a fictional consumer uses separate data and storage [review: engine lead]
CHANGES_WITH:
- docs/PRD.md#FORMS
:END_MODULE_CONTRACT
-->
# Reader profile v1

JSON: `schema_version: 1`, `family: {id, title, source_language,
languages: [language], fictional: boolean}`, `data: relative URL`,
`reader_names: {language: {name: form}}` (optional, default empty),
`legacy_storage: boolean` (optional, default false; host-approved pilot only),
`host: {feedback: "disabled" | "api"}` (optional). Feedback defaults to disabled;
`api` enables the host's same-origin `/api/feedback`. The legacy private pilot
with `legacy_storage: true` retains its API unless explicitly disabled. Fictional
profiles suppress feedback unless wrapped in an explicitly host-authorized desk
(including a fictional acceptance desk). The local `reader serve` has no feedback
API; `desk serve` provides the common sender and inbox for every reader screen.

Required family strings are nonempty; languages is nonempty and contains the
source language. A browser rejects unsupported UI packs before rendering.
`data` resolves relative to the profile URL. Omitted graph collections become
empty collections in the browser adapter; authored fields are never rewritten.

Storage keys are `familiar:<encoded family id>:<fictional|private>:<key>`.
Legacy import copies only absent destination keys, retains originals for rollback,
and is enabled only by the private pilot profile. Fictional profiles must not
enable legacy import. A profile switch reloads the shell before mounting children.

The complete delivery manifest and media integrity boundary are specified in
`reader-export.md`; host authentication remains outside the engine. The TypeScript
loader source remains with the pilot; its compiled output is packaged with the
engine shell, with no second browser implementation.
