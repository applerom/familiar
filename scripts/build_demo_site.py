"""Build the fictional public desk through the installed engine commands."""
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='Empty site destination')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.out.resolve()
    command = [shutil.which('familiar') or 'familiar', '--root', str(root / 'demo')]
    environment = dict(os.environ, PYTHONUTF8='1')
    # Exercise the same public export advertised to a new user. Acceptance is
    # committed demo data; a build never invents or refreshes reader attestations.
    with tempfile.TemporaryDirectory(prefix='familiar-demo-reader-') as directory:
        subprocess.run(command + ['reader', 'export', '--output', directory], cwd=root,
                       check=True, timeout=600, env=environment)
    subprocess.run(command + ['desk', 'export-demo', '--output', str(out)], cwd=root,
                   check=True, timeout=600, env=environment)


if __name__ == '__main__':
    main()
