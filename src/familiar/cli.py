"""Entry point of the `familiar` command."""
# START_MODULE_CONTRACT: MOD-CLI
# PURPOSE: One command for every capability; each capability registers its own subcommands.
# PRD_REF: docs/PRD.md#ARCH
# INVARIANTS:
# - method reads and cloud desk commands bypass family startup maintenance [review: engine lead]
# - other CLI startup reaps only expired, leased family snapshots before dispatch [review: engine lead]
# CHANGES_WITH:
# - MOD-HOST-CLI (family text command registration)
# - pyproject.toml (installed capability and method packaging)
# - docs/PRD.md#ARCH (how an instance is found)
# - MOD-RULES-CLI (capability command registration)
# - MOD-METHOD-CLI (family-independent resource reads)
# :END_MODULE_CONTRACT
from __future__ import annotations

import argparse
import importlib
import sys

CAPABILITIES = ("familiar.research.cli", "familiar.rules.cli", "familiar.instance.cli", "familiar.tree.cli", "familiar.checks.cli", "familiar.intake.cli", "familiar.feeds.cli", "familiar.reader.cli", "familiar.instance.host_cli", "familiar.desk.cli", "familiar.method_cli")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    from familiar import __version__
    parser = argparse.ArgumentParser(prog="familiar")
    parser.add_argument("--version", action="version", version=f"Familiar {__version__}")
    parser.add_argument("--root", help="family root; default: nearest familiar.toml upward, or FAMILIAR_ROOT")
    commands = parser.add_subparsers(dest="capability", required=True)
    for name in CAPABILITIES:
        try:
            importlib.import_module(name).register(commands)
        except ModuleNotFoundError as error:
            if error.name and (name == error.name or name.startswith(error.name + ".")):
                continue
            print(f"capability {name} failed to import: {error}", file=sys.stderr)
            return 1
    args = parser.parse_args(argv)
    if args.capability == 'method' or (args.capability == 'desk'
                                      and args.desk_action not in ('build', 'serve')):
        return args.run(args)
    from familiar.instance.model import Instance
    from familiar.instance.root import RootNotFound
    from familiar.instance.writer import reap_snapshots
    try:
        reap_snapshots(Instance(args.root))
    except (RootNotFound, ValueError, OSError):
        pass  # Initialization/global forms need no family; the command owns config diagnostics.
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
