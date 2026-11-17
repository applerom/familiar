/*
START_MODULE_CONTRACT: MOD-READER-SHELL-BUILD
PURPOSE: Build the data-free reader from engine-owned, locked sources and seal its bytes.
PRD_REF: docs/PRD.md#FORMS
INVARIANTS:
- no family directory is an input to the shell build [review: engine lead]
- every built shell carries the complete third-party notices under its integrity manifest [review: engine lead]
CHANGES_WITH:
- regions/CONTRACT.md (bundled kinship JSON and reader vocabulary)
- docs/reader-export.md (shell packaging procedure)
- THIRD_PARTY_NOTICES.txt (distributed runtime rights)
- LICENSE (own engine licence delivered by the runtime)
:END_MODULE_CONTRACT
*/
import {createHash} from 'node:crypto';
import {readFile, readdir, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {build} from 'vite';
import react from '@vitejs/plugin-react';

const root = fileURLToPath(new URL('./reader-shell/', import.meta.url));
const outDir = fileURLToPath(new URL('../reader-shell/', import.meta.url));
await build({configFile: false, root, publicDir: false, base: './', plugins: [react()],
  server: {fs: {allow: [fileURLToPath(new URL('./', import.meta.url))]}},
  css: {postcss: {plugins: []}},
  build: {outDir, emptyOutDir: true, sourcemap: false,
    rolldownOptions: {input: {index: `${root}/index.html`, pageTop: `${root}/page-top.tsx`,
      tokens: fileURLToPath(new URL('./app/tokens.css', import.meta.url))}}}});
await writeFile(`${outDir}/THIRD_PARTY_NOTICES.txt`, await readFile(new URL('../THIRD_PARTY_NOTICES.txt', import.meta.url)));
const files = {};
async function collect(dir, prefix = '') {
  for (const entry of (await readdir(dir, {withFileTypes: true})).sort((a,b) => a.name.localeCompare(b.name))) {
    const name = prefix + entry.name;
    if (entry.isDirectory()) await collect(`${dir}/${entry.name}`, `${name}/`);
    else {
      const data = await readFile(`${dir}/${entry.name}`);
      files[name] = {sha256: createHash('sha256').update(data).digest('hex'), size: data.length};
    }
  }
}
await collect(outDir);
const inputs = createHash('sha256');
const license = await readFile(new URL('../LICENSE', import.meta.url));
for (const name of ['package.json', 'bun.lock', 'build.mjs']) inputs.update(
  (await readFile(new URL(name, import.meta.url), 'utf8')).replaceAll('\r\n', '\n'));
await writeFile(`${outDir}/shell-manifest.json`, JSON.stringify({schema_version: 1,
  source: {repository: 'familiar', directory: 'reader-src', command: 'bun run reader:shell',
    toolchain_sha256: inputs.digest('hex')},
  contracts: {reader_profile: 1, reader_export: 1},
  license: {sha256: createHash('sha256').update(license).digest('hex'), size: license.length},
  files}, null, 2) + '\n');
