/*
START_MODULE_CONTRACT: MOD-READER-SHELL-BUILD
PURPOSE: Build the data-free reader from engine-owned, locked sources and seal its bytes.
PRD_REF: docs/PRD.md#FORMS
INVARIANTS:
- no family directory is an input to the shell build [review: engine lead]
- every built shell carries the complete third-party notices under its integrity manifest [review: engine lead]
- a workshop word or an apology for emptiness in a reader string or a bundled desk pack stops the build [review: engine lead]
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

// A page a family reads carries no workshop words and no apology for being empty: the shell is not built with them.
const plain = JSON.parse(await readFile(new URL('./plain-words.json', import.meta.url), 'utf8'));
const banned = Object.fromEntries(['ru', 'pl', 'en', 'sv'].map(lang => [lang, new RegExp(plain[lang].join('|'), 'iu')]));
const found = [];
const look = (lang, text, where) => { const hit = banned[lang].exec(text); if (hit) found.push(`${where}: "${hit[0]}" in "${text.slice(0, 90)}"`); };
const LITERAL = /\/\*[\s\S]*?\*\/|\/\/[^\n]*|'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`/g;
const literals = text => [...text.matchAll(LITERAL)].map(m => m[1] ?? m[2] ?? m[3] ?? '');
for (const entry of await readdir(new URL('./app/', import.meta.url), {recursive: true})) if (/\.tsx?$/.test(entry) && !/\.test\.ts$/.test(entry)) {
  const text = await readFile(new URL('./app/' + entry.replaceAll('\\', '/'), import.meta.url), 'utf8');
  for (const value of literals(text)) if (/[а-яё]/i.test(value)) look('ru', value, entry);
  if (entry === 'i18n.ts') for (const lang of ['pl', 'en', 'sv']) {
    const start = text.indexOf(`const ${lang}:`), next = text.slice(start + 5).search(/\n(?:export )?const /);
    for (const value of literals(text.slice(start, start + 5 + next))) look(lang, value, `${entry} ${lang}`);
  }
}
for (const [lang, folder] of [['ru', 'ru'], ['pl', 'pl'], ['en', 'demo-english']]) {
  let section = '';
  for (const line of (await readFile(new URL(`../regions/${folder}/pack.toml`, import.meta.url), 'utf8')).split(/\r?\n/)) {
    section = /^\[([^[\]]+)\]/.exec(line)?.[1] ?? section;
    const pair = /^([a-z_]+)\s*=\s*"(.*)"\s*$/.exec(line);
    if (pair && plain.sections.includes(section) && !plain.agents_only.includes(pair[1])) look(lang, pair[2], `${folder} [${section}] ${pair[1]}`);
  }
  for (const value of literals(await readFile(new URL(`../regions/${folder}/kinship.json`, import.meta.url), 'utf8'))) look(lang, value, `${folder}/kinship.json`);
}
if (found.length) throw new Error(`Plain words: a family reads these pages (CRAFT-PLAIN-PAGES, plain-words.json):\n${found.join('\n')}`);

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
