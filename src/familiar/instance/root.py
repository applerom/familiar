"""Find the family root an engine command works for."""
# START_MODULE_CONTRACT: MOD-INSTANCE-ROOT
# PURPOSE: One place that decides which family a command runs against, so no code holds a path to family data.
# PRD_REF: docs/PRD.md#ARCH
# INVARIANTS:
# - order is explicit root, then FAMILIAR_ROOT, then nearest familiar.toml upward [review: engine lead]
# - a directory without familiar.toml is never accepted as a root [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#ARCH (the lookup order is stated there)
# :END_MODULE_CONTRACT
from __future__ import annotations

import os
import tomllib
from pathlib import Path

CONFIG = "familiar.toml"


class RootNotFound(Exception):
    pass


def find_root(
    explicit: str | os.PathLike | None = None,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> Path:
    env = os.environ if env is None else env
    if explicit:
        return _accept(Path(explicit), "--root")
    if env.get("FAMILIAR_ROOT"):
        return _accept(Path(env["FAMILIAR_ROOT"]), "FAMILIAR_ROOT")
    start = (cwd or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / CONFIG).is_file():
            return candidate
    raise RootNotFound(f"no {CONFIG} found from {start} upward; pass --root or set FAMILIAR_ROOT")


def load_config(root: Path) -> dict:
    with (root / CONFIG).open("rb") as handle:
        return tomllib.load(handle)


def _accept(path: Path, source: str) -> Path:
    path = path.resolve()
    if not (path / CONFIG).is_file():
        raise RootNotFound(f"{source} points at {path}, which has no {CONFIG}")
    return path
