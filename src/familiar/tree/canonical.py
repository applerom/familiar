# START_MODULE_CONTRACT: MOD-TREE-CANONICAL
# PURPOSE: Define the reproducible graph boundary shared by legacy comparison and engine output.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - editorial card presentation and runtime timestamps cannot change the comparison checksum; explicit clan-name decisions can [review: engine lead]
# - narrator navigation survives encoded working graph delivery [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#INSTANCE
# :END_MODULE_CONTRACT
import hashlib
import json
import re

KEYS = (
    "people",
    "edges",
    "families",
    "associations",
    "originalPeople",
    "originalEdges",
    "sources",
    "workingVersion",
    "identityAliases",
    "familyCorrections",
    "distinct",
    "root",
    "narrator",
    "defaultViewer",
)
OMIT = {"namePresentation", "cardPresentation", "published_at", "updated"}


def normalize(value):
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in sorted(value.items()) if k not in OMIT}
    if isinstance(value, list):
        return sorted(
            (normalize(v) for v in value),
            key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False),
        )
    if isinstance(value, str) and (re.match(r"^[A-Za-z]:[\\/]", value) or value.startswith("/")):
        return "<absolute-path>/" + value.replace("\\", "/").rsplit("/", 1)[-1]
    return value


def canonical(data):
    return normalize({key: data[key] for key in KEYS if key in data})


def encode(data):
    return json.dumps(canonical(data), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def stats(data):
    return {
        **{
            key: len(data.get(key, []))
            for key in ("people", "edges", "families", "sources", "identityAliases")
        },
        "removed_edges": len(
            {(e["child"], e["parent"]) for e in data.get("originalEdges", [])}
            - {(e["child"], e["parent"]) for e in data.get("edges", [])}
        ),
        "sha256": hashlib.sha256(encode(data).encode("utf-8")).hexdigest(),
    }
