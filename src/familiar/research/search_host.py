# START_MODULE_CONTRACT: MOD-SEARCH-HOST
# PURPOSE: Expose explicit host access decisions while leaving sessions and shared source accounting outside Familiar.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - the standalone host requires explicit opt-in for its one family [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#LAYERS
# :END_MODULE_CONTRACT
from typing import Protocol


class SearchHost(Protocol):
    def authorize(self, family_id, source, url): ...
    def fetch(self, token, url): ...
    def report(self, token, outcome): ...


class SingleFamilyHost:
    """Explicit opt-in adapter; no shared accounting. Transport supplied by owner."""
    def __init__(self, family_id, transport, *, allow=False):
        self.family_id, self.transport, self.allow = family_id, transport, allow

    def authorize(self, family_id, source, url):
        return (family_id, source) if self.allow and family_id == self.family_id else None

    def fetch(self, token, url):
        return self.transport(url)

    def report(self, token, outcome):
        pass


class PilotGateHost:
    """Dependency-injected pilot Gate and browser transport; no pilot path or session here."""
    def __init__(self, source_gate, transport, author):
        self.gate, self.transport, self.author = source_gate, transport, author

    def authorize(self, family_id, source, url):
        return self.gate.acquire(url=url, n=1, author=self.author, kind='search')

    def fetch(self, token, url):
        return self.transport(url)

    def report(self, token, outcome):
        self.gate.record(token, outcome, author=self.author)
