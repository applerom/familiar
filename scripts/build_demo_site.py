"""Build the fictional public desk through the installed engine commands."""
import argparse
import html
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def language_link(out, href, label, *, investigation_only=False):
    """Keep language navigation outside the accepted reader's data and shell."""
    for path in out.rglob('*.html'):
        if investigation_only and path.relative_to(out).as_posix() not in {
                'desk/progress.html', 'desk/questions.html'}:
            continue
        text = path.read_text(encoding='utf-8')
        link = ('<a class="demo-language" href="' + html.escape(href, quote=True)
                + '" style="display:inline-flex;align-items:center;min-height:44px;'
                + 'font-size:13px;color:var(--act);white-space:nowrap">'
                + html.escape(label) + '</a>')
        text = text.replace('<span id="desk-feedback-entry"></span>',
                            '<span id="desk-feedback-entry">' + link + '</span>')
        # A phone's lower row holds only its places: the same link opens the quieter list there.
        text = text.replace('<nav id="desk-more" hidden>', '<nav id="desk-more" hidden><a href="'
                            + html.escape(href, quote=True) + '"><span>' + html.escape(label) + '</span></a>')
        path.write_text(text, encoding='utf-8', newline='')


def build_family(root, family, out, environment, *, public_reader=False):
    command = [shutil.which('familiar') or 'familiar', '--root', str(family)]
    # The public-reader demo needs its committed independent reading. The
    # fictional writing demo uses the desk to show frames still in progress.
    subprocess.run(command + ['desk', 'export-demo', '--output', str(out)]
                   + (['--public-reader'] if public_reader else []), cwd=root,
                   check=True, timeout=600, env=environment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='Empty site destination')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    environment = dict(os.environ, PYTHONUTF8='1')
    # Build disposable copies, leaving the independently read source families alone.
    with tempfile.TemporaryDirectory(prefix='familiar-demo-families-') as directory:
        temporary = Path(directory)
        for name, source, destination in (
                ('en', root / 'demo', out),
                ('ru', root / 'demo-russian' / 'family', out / 'ru')):
            family = temporary / name
            shutil.copytree(source, family, ignore=shutil.ignore_patterns(
                '.secrets', '.build', 'build-cache', 'snapshots', 'export', '__pycache__'))
            build_family(root, family, destination, environment, public_reader=name == 'ru')
    # The English demo's reciprocal link belongs in the investigation.
    language_link(out, 'ru/', 'По-русски', investigation_only=True)
    language_link(out / 'ru', '../', 'English')


if __name__ == '__main__':
    main()
