"""Rebuild HEAD from an archive with family paths denied, then deliver its wheel."""
# START_MODULE_CONTRACT: MOD-ENGINE-RELEASE-CHECK
# PURPOSE: Verify a committed wheel and its required files without opening a family checkout.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - required packaged files match the archived delivery manifest [review: engine lead]
# - denied roots fail explicit Python read probes during the build [review: engine lead]
# CHANGES_WITH:
# - MOD-READER-SHELL-BUILD
# - docs/reader-export.md (release verification command)
# :END_MODULE_CONTRACT
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deny-root', action='append', required=True, type=Path)
    parser.add_argument('--wheel-dir', required=True, type=Path)
    parser.add_argument('--rebuild-shell', action='store_true', help='Optional surface reproducibility advice')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / 'src'))
    from familiar.check_policy import decision
    env = {k: v for k, v in os.environ.items() if k not in {
        'PYTHONPATH', 'NODE_OPTIONS', 'VIRTUAL_ENV', 'FAMILIAR_ROOT',
        'FAMILIAR_HOST_PATHS', 'FAMILIAR_HOST_PACKS', 'FAMILIAR_READER_URL'}}

    def require(check, condition, message):
        if not condition:
            if decision(check) == 'block':
                raise ValueError(message)
            print(f'ADVICE [{check}]: {message}')

    def run(*command, cwd=repo, capture=False, check='release.archive'):
        result = subprocess.run(command, cwd=cwd, env=env, check=False, text=True,
                                encoding='utf-8', stdout=subprocess.PIPE if capture else None,
                                timeout=600)
        require(check, result.returncode == 0, f'Command failed ({result.returncode}): {command[0]}')
        return result.stdout

    require('release.archive', not run('git', 'status', '--porcelain', capture=True).strip(),
            'Commit engine changes before checking the release archive')
    commit = run('git', 'rev-parse', 'HEAD', capture=True).strip()
    with tempfile.TemporaryDirectory(prefix='familiar-release-') as temporary:
        work = Path(temporary)
        source = work / 'source'
        source.mkdir()
        archive = work / 'source.tar'
        run('git', 'archive', 'HEAD', '--output', str(archive))
        with tarfile.open(archive) as tar:
            tar.extractall(source, filter='data')
        expected = json.loads((source / 'reader-shell/shell-manifest.json').read_bytes())
        uv = shutil.which('uv')
        if not uv:
            raise ValueError('Release check needs uv')
        if args.rebuild_shell:
            # Rebuild in a separate tree: advice must never change delivered bytes.
            surface = work / 'surface'
            shutil.copytree(source, surface)
            try:
                node, bun = shutil.which('node'), shutil.which('bun')
                if not node or not bun:
                    raise ValueError('Optional shell rebuild needs Node and Bun')
                run(bun, 'install', '--offline', '--frozen-lockfile', '--ignore-scripts', cwd=surface / 'reader-src')
                permission = [node, '--permission', f'--allow-fs-read={surface}',
                              f'--allow-fs-write={surface}', '--allow-addons', '--allow-worker']
                for denied in args.deny_root:
                    run(*permission, '-e', "try {require('fs').readFileSync(process.argv[1]);"
                        "process.exit(1)} catch(e) {if(e.code!=='ERR_ACCESS_DENIED') throw e}",
                        str(denied.resolve() / 'AGENTS.md'), cwd=surface)
                run(*permission, str(surface / 'reader-src/build.mjs'), cwd=surface)
                actual = json.loads((surface / 'reader-shell/shell-manifest.json').read_bytes())
                if actual != expected:
                    raise ValueError('Rebuilt shell differs from the committed manifest')
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                print(f'ADVICE [release.shell-rebuild]: {exc}')
        # The Python audit hook also applies to inherited build-backend processes.
        guard = work / 'guard'
        guard.mkdir()
        (guard / 'sitecustomize.py').write_text(GUARD, encoding='utf-8')
        env['PYTHONPATH'] = str(guard)
        env['FAMILIAR_DENIED_ROOTS'] = json.dumps([str(p.resolve()) for p in args.deny_root])
        for denied in args.deny_root:
            run(sys.executable, '-c', "import sys\ntry: open(sys.argv[1], 'rb')\n"
                "except PermissionError: pass\nelse: raise RuntimeError('deny hook inactive')",
                str(denied.resolve() / 'AGENTS.md'), cwd=source, check='release.denied-roots')
        run(uv, 'build', '--wheel', '--out-dir', str(work / 'dist'), str(source), cwd=source)
        wheel = next((work / 'dist').glob('*.whl'))
        with ZipFile(wheel) as package:
            includes = tomllib.loads((source / 'pyproject.toml').read_text(encoding='utf-8'))['tool']['hatch']['build']['targets']['wheel']['force-include']
            missing = []
            for relative, destination in includes.items():
                base = source / relative
                for path in [base] if base.is_file() else base.rglob('*'):
                    if not path.is_file():
                        continue
                    name = destination if base.is_file() else destination + '/' + path.relative_to(base).as_posix()
                    if name not in package.namelist():
                        missing.append(name)
            for name in ('familiar/cli.py', 'familiar/check-weights.json'):
                if name not in package.namelist():
                    missing.append(name)
            require('release.wheel', not missing, 'Required wheel files missing: ' + ', '.join(missing))
            raw = package.read('familiar/_licenses/LICENSE')
            require('release.wheel', len(raw) == expected['license']['size']
                    and hashlib.sha256(raw).hexdigest() == expected['license']['sha256'],
                    'Wheel engine licence differs')
            for name, entry in expected['files'].items():
                raw = package.read('familiar/_reader_shell/' + name)
                require('release.wheel', len(raw) == entry['size'] and hashlib.sha256(raw).hexdigest() == entry['sha256'],
                        'Wheel shell differs: ' + name)
        args.wheel_dir.mkdir(parents=True, exist_ok=True)
        target = args.wheel_dir / wheel.name
        shutil.copyfile(wheel, target)
        print(f'Engine commit: {commit}\nWheel: {target.resolve()}\n'
              f'SHA-256: {hashlib.sha256(target.read_bytes()).hexdigest()}\n'
              f'Shell: {len(expected["files"])} packaged files verified; denied roots: {len(args.deny_root)}')


GUARD = '''import json, os, sys
roots = [os.path.normcase(os.path.abspath(p)) for p in json.loads(os.environ['FAMILIAR_DENIED_ROOTS'])]
def deny(event, args):
    if event not in ('open', 'os.listdir', 'os.scandir', 'os.chdir') or not args:
        return
    p = args[0]
    if isinstance(p, (str, bytes, os.PathLike)):
        path = os.path.normcase(os.path.abspath(os.fsdecode(p)))
        if any(path == r or path.startswith(r + os.sep) for r in roots):
            raise PermissionError('Release build denied a family path: ' + path)
sys.addaudithook(deny)
'''

if __name__ == '__main__':
    main()
