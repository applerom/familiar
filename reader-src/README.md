# Shared reader source

This is the engine's data-free reader, not a family application. It loads the
checked reader profile and graph at runtime. Only general components, styles,
fonts and world geometry belong here; never add family data or a public directory.

Use Node >=22.13 and Bun 1.3.10:

```powershell
bun install --frozen-lockfile --ignore-scripts
bun run reader:shell
```

The output is `../reader-shell/`, including the generated integrity manifest.
The lockfile and explicit transformer overrides make the shell reproducible.
Storage keys use neutral names, scoped by the reader profile's family id.
No migration from historical key spellings is provided. The build copies
`../THIRD_PARTY_NOTICES.txt` beside the shell and seals it in the manifest;
keep it with every copy of the shell, fonts, or a generated desk site.
