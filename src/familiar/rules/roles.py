# START_MODULE_CONTRACT: MOD-RULES-ROLES
# PURPOSE: Declare the role vocabulary once for rule delivery and sheet validation.
# PRD_REF: docs/PRD.md#ROLES
# INVARIANTS:
# - registered roles and shipped sheets match exactly [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#ROLES (sheet stems must match registry ids)
# - pyproject.toml (method resource destination)
# :END_MODULE_CONTRACT
from importlib.resources import files
from pathlib import Path

ROLES = dict.fromkeys((
    "lead", "researcher", "second-look", "recipe-searcher", "feed-author",
    "shot-director", "artist", "reviewer", "translator",
))
ROLES = {role: role for role in ROLES}


def method_root():
    """Wheel resources first; source checkout uses the same method layout."""
    bundled = files("familiar").joinpath("_method")
    if bundled.is_dir():
        return Path(str(bundled))
    return Path(__file__).resolve().parents[3] / "method"


def validate_sheets(root=None):
    sheets = {p.stem for p in (root or method_root()).joinpath("roles").glob("*.md")}
    if sheets != set(ROLES):
        raise ValueError(f"role sheets differ: missing={sorted(set(ROLES) - sheets)}, "
                         f"unregistered={sorted(sheets - set(ROLES))}")
