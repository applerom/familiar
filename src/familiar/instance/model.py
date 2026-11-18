# START_MODULE_CONTRACT: MOD-INSTANCE-MODEL
# PURPOSE: Validate family metadata and confine declared data locations before capabilities use them.
# PRD_REF: docs/PRD.md#INSTANCE
# INVARIANTS:
# - an empty initialized family loads without data directories [test: tests/journeys/test_installed_engine.py::test_installed_engine]
# - sibling families never share default paths [review: engine lead]
# - escaping paths require an explicit host mapping [review: engine lead]
# - unsupported schemas and malformed metadata are rejected [review: engine lead]
# - a declared engine pin is an exact 0.MINOR.PATCH release [review: engine lead]
# - registered media resolve identically for feed checks and delivery [review: engine lead]
# - family photo registrations coexist with legacy and manifest media [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#INSTANCE
# - docs/reader-export.md (permanent media manifest)
# :END_MODULE_CONTRACT
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .gate import boundary
from .root import find_root, load_config

DEFAULTS = {
    "world_map": "world/places.json",
    "feed_graph": "export/graph.json", "media_archive": "media-archive",
    "working_version": "tree/working-version.json", "associations": "tree/associations.json",
    "card_reviews": "tree/card-reviews.json", "tree_metadata": "tree/metadata.json",
    "tree_snapshot": "tree/snapshot", "imports": "imports",
    "evidence": "tree/evidence.json", "contributions": "tree/contributions",
    "identity_decisions": "tree/identity-decisions.json", "cases": "cases",
    "versions": "versions", "asks": "family/asks", "questions": "family/questions", "answers": "family/answers",
    "correspondence": "family/correspondence",
    "memory": "family/memory", "research_permission": "family/research-permission.json",
    "privacy": "family/privacy.json", "archive_rights": "family/archive-rights.json", "variant_overrides": "family/variants.json",
    "feeds": "feeds", "edition": "edition/cards.json", "gallery": "edition/gallery.json",
    "records": "records", "originals": "originals", "captures": "captures", "media": "media",
    "searches": "searches", "state": ".state", "build": ".build", "export": "export",
}


class InstanceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InstanceError(message)


class Instance:
    def __init__(self, root=None, *, host_paths=None, host_packs=None, legacy_rules=False):
        self._host_packs = host_packs
        self._legacy_rules = legacy_rules
        self.root = find_root(root)
        self.config = load_config(self.root)
        config = self.config
        # Historical rules-only files remain usable; versioned instances are always strict.
        legacy = legacy_rules and "schema_version" not in config and "family" not in config
        if not legacy:
            require(type(config.get("schema_version")) is int and config["schema_version"] == 1,
                    "schema_version must be supported major version 1")
            family = config.get("family")
            require(isinstance(family, dict), "family must be a table")
            require(not (family.keys() - {"id", "title", "source_language", "languages", "fictional"}),
                    "unknown family keys")
            require(type(family.get("fictional", False)) is bool, "family.fictional must be boolean")
            for key in ("id", "title", "source_language"):
                require(isinstance(family.get(key), str) and bool(family[key].strip()),
                        f"family.{key} must be nonempty text")
            require(self._strings(family.get("languages")) and bool(family["languages"]),
                    "family.languages must be a nonempty array of language tags")
        family = config.get("family", {})
        engine = config.get('engine', {})
        require(isinstance(engine, dict) and not (engine.keys() - {'version'}),
                'engine must be a table containing only version')
        if 'engine' in config:
            require(isinstance(engine.get('version'), str) and
                    re.fullmatch(r'0\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', engine['version']),
                    'engine.version must be an exact 0.MINOR.PATCH release')
        self.engine_version = engine.get('version')
        self.id = family.get("id")
        self.languages = tuple(family.get("languages", []))
        self.source_language = family.get("source_language")
        self.region_packs = config.get("region_packs", [])
        require(self._strings(self.region_packs), "region_packs must be an array of paths")
        self.overrides = config.get("paths", {})
        require(isinstance(self.overrides, dict), "paths must be a table")
        require(not (self.overrides.keys() - DEFAULTS.keys()), "unknown path keys")
        require(all(isinstance(v, str) and v.strip() for v in self.overrides.values()),
                "path values must be nonempty text")
        for key in ("settings", "modes", "feed"):
            require(isinstance(config.get(key, {}), dict), f"{key} must be a table")
        # Host mapping is out of band, scoped to this root, and never read from family data.
        if host_paths is None:
            host_paths = json.loads(os.environ.get("FAMILIAR_HOST_PATHS", "{}"))
        require(isinstance(host_paths, dict), "host paths must be an object keyed by absolute root")
        self.host_paths = host_paths.get(str(self.root), {})
        require(isinstance(self.host_paths, dict), "root host mapping must be an object")
        require(not (self.host_paths.keys() - DEFAULTS.keys()), "unknown host path keys")
        for value in self.host_paths.values():
            require(isinstance(value, str) and Path(value).is_absolute(),
                    "host paths must be absolute text paths")
        for key in DEFAULTS:
            self.path(key)
        roots = config.get('media_roots', ['media', 'media_archive'])
        require(self._strings(roots) and bool(roots) and all(key in DEFAULTS for key in roots),
                'media_roots must be nonempty declared path keys')
        self.language_packs = config.get("language_packs", {})
        require(isinstance(self.language_packs, dict) and all(
            isinstance(k, str) and re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", k) and isinstance(v, str) and v
            for k, v in self.language_packs.items()), "language_packs must map tags to pack ids")
        from .packs import load_packs
        self.packs, self.language_pack_data = load_packs(self, host_packs)


    def engine_warning(self):
        from familiar import __version__
        if self.engine_version and self.engine_version != __version__:
            return (f'engine.version: pinned {self.engine_version}; installed {__version__}. '
                    'Install the pinned wheel, or explicitly accept this release and update '
                    'familiar.toml before building and reviewing the desk.')
        return None

    @staticmethod
    def _strings(value):
        return isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value)

    def _inside(self, value):
        path = (self.root / value).resolve()
        require(path.is_relative_to(self.root), f"path leaves family root: {value}")
        return path

    def path(self, key):
        if key not in DEFAULTS:
            raise InstanceError(f"unknown path key: {key}")
        if key in self.host_paths:
            return Path(self.host_paths[key]).resolve()
        return self._inside(self.overrides.get(key, DEFAULTS[key]))

    @boundary('research')
    def collection(self, key):
        """Directory entries or decoded JSON; missing optional collections are []."""
        from .gate import require
        require(self)
        path = self.path(key)
        if not path.exists():
            return []
        if path.is_dir():
            return sorted(p for p in path.iterdir() if p.is_file() and
                          p.name != "CONTRACT.md" and not p.name.startswith("."))
        return json.loads(path.read_text(encoding="utf-8"))

    def media_file(self, asset):
        """Resolve a public asset through a permanent manifest, or legacy roots.

        A present manifest is authoritative: an unregistered file is not media.
        Reader exports additionally validate the complete manifest and its IDs.
        """
        from .writer import input_digest
        if not isinstance(asset, str) or asset.startswith('//'):
            return None
        rel = asset.removeprefix('/')
        if not rel or '\\' in rel or ':' in rel or any(p in ('', '.', '..') for p in rel.split('/')):
            return None
        from .gallery import asset_file, permits_display, photograph
        if photo := photograph(self, '/' + rel):
            return asset_file(self, rel, photo) if permits_display(self) else None
        base = self.path('media')
        manifest = base / 'manifest.json'
        if manifest.is_file():
            immutable = getattr(self, '_immutable_snapshot', False)
            data = getattr(self, '_media_catalog', None) if immutable else None
            if data is None:
                data = json.loads(manifest.read_text(encoding='utf-8'))
                if immutable:
                    self._media_catalog = data
            require(type(data.get('schema_version')) is int and data['schema_version'] == 1,
                    'unsupported media manifest version')
            row = next((r for r in data['assets'] if r.get('export') == rel), None)
            if row is None:
                return None
            path = (base / row['file']).resolve()
            require(path.is_relative_to(base), 'media path escapes its root')
            if not path.is_file():
                return None
            require(input_digest(path) == row['sha256'], 'media checksum mismatch')
            return path
        return next((p for key in self.config.get('media_roots', ['media', 'media_archive'])
                     if (p := (self.path(key) / rel).resolve()).is_relative_to(self.path(key)) and p.is_file()), None)

    def data_file(self, value):
        """Resolve a file-valued setting using the instance confinement boundary."""
        require(isinstance(value, str), "data file setting must be text")
        if not value:
            return {"status": "empty", "path": None}
        path = self._inside(value)
        if not path.exists():
            return {"status": "missing", "path": str(path)}
        try:
            path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return {"status": "unreadable", "path": str(path)}
        return {"status": "readable", "path": str(path)}

    def readiness(self):
        from .validation import check

        report = check(self)
        return {key: report[key] for key in
                ("first_chapter_missing", "full_cycle_missing", "unverified")}
