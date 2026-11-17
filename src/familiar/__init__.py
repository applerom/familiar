"""Familiar: the engine. A family is an instance that lives elsewhere."""
# START_MODULE_CONTRACT: MOD-ENGINE-VERSION
# PURPOSE: Expose one engine number for the CLI, the desk, the private reader and desk build records.
# PRD_REF: docs/PRD.md#ARCH
# INVARIANTS:
# - the number comes from the installed distribution, or pyproject.toml in a bare source tree [review: engine lead]
# CHANGES_WITH:
# - pyproject.toml (version)
# - CHANGELOG.md
# :END_MODULE_CONTRACT


def _version():
    """The installed distribution's number; a bare source tree reads pyproject.toml."""
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version('familiar')
    except PackageNotFoundError:
        import re
        from pathlib import Path
        pyproject = Path(__file__).resolve().parents[2] / 'pyproject.toml'
        found = re.search(r'^version = "([^"]+)"', pyproject.read_text(encoding='utf-8'), re.MULTILINE) if pyproject.is_file() else None
        return found[1] if found else '0+unknown'


__version__ = _version()
