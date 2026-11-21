# START_MODULE_CONTRACT: MOD-TREE-IDENTITIES
# PURPOSE: Resolve recorded identity decisions while retaining the pre-merge evidence and undo history.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - a merge retains both source sets and its undo record [review: engine lead]
# - disputed decisions retain their conflict and next test [review: engine lead]
# - final edges have existing endpoints and resolved evidence [review: engine lead]
# - merged links retain their evidence and existing conflict [review: engine lead]
# - materialized aliases point only to active canonical people [review: engine lead]
# - a probable identity (from 0.3, or on the main line) hides the found card without merging facts; its parents hang on a junction with the version weight [review: engine lead]
# - a probable identity's card dates its birth by a document, never by an estimate, whichever card holds it [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#INSTANCE
# :END_MODULE_CONTRACT
"""Apply explicit, source-backed identity decisions to a derived graph only."""

import copy
import re

from familiar.tree.birth_guess import birth_date

# When two edges collapse into one, the stronger claim survives; a conflict is never overwritten.
EDGE_RANK = {"hypothesis": 1, "export": 2, "verified": 3, "conflict": 4}
# A document's own spelling of a name: shown in the card's "More" with its source, never on a tile.
DOCUMENT_NAME_TYPES = {"recorded", "as-written", "indexed"}

# An estimate, a range or a bound is not a document's date: a dated record of the other card is stronger.
_ROUGH = re.compile(r"^(ABT|EST|CAL|BEF|AFT|FROM|BET|about|circa|ca\.|около|примерно|до|после|ok\.|około)\b|^[~≈<>]|\?", re.I)
_YEAR = re.compile(r"\b(1\d{3}|20\d{2})\b")


def _birth(person):
    """The card's birth date and whether a document gives it as such (not an estimate, a range or an age)."""
    date = str(birth_date(person) or "").strip()
    event = next((e for e in person.get("events", []) if str(e.get("date", "")).strip() == date), {})
    if not _YEAR.search(date):
        return "", False
    return date, not (_ROUGH.search(date) or event.get("approximate"))


# RES-19: a disputed merge stays the leading version and must say what story may lie behind the conflict
# and what would test it, so a later pass can pick it up. A wrong merge is withdrawn, not reviewed.
def check_review(decision):
    review = decision.get("review")
    if review is None:
        return
    if review.get("verdict") not in ("accepted", "contested", "верно", "спорно"):
        raise ValueError("Identity review verdict must be верно or спорно")
    if review["verdict"] in ("contested", "спорно") and not all(
        review.get(k) for k in ("conflict", "story", "next_test")
    ):
        raise ValueError("A disputed identity must state conflict, story and next_test")


def correct_families(families, corrections, aliases=None):
    """A snapshot family that names the wrong spouse or child: corrected here, the frozen snapshot stays as it is."""
    aliases = aliases or {}
    by_id = {family.get("id"): family for family in families}
    for item in corrections:
        family = by_id.get(item["family"])
        if family is None:
            raise ValueError(f"No family to correct: {item['family']}")
        for key in ("husband", "wife"):
            if item.get(key):
                family[key] = aliases.get(item[key], item[key])
        moved = {aliases.get(x, x): to for x, to in item.get("move_children", {}).items()}
        drop = {aliases.get(x, x) for x in item.get("remove_children", [])} | set(moved)
        family["children"] = [x for x in family.get("children", []) if x not in drop]
        for child, to in moved.items():
            if to not in by_id:
                raise ValueError(f"No family to move a child to: {to}")
            by_id[to]["children"] = list(dict.fromkeys(by_id[to].get("children", []) + [child]))


def correct_family_edges(edges, families, corrections, aliases=None, labels=None):
    """The parent links a snapshot family gave follow its correction: a moved or dropped child leaves the old
    parents, a corrected spouse becomes the parent. Only the family's own ('export') links change; a link a
    document or a contribution backs is a separate claim and stays."""
    aliases = aliases or {}
    labels = labels or {}
    by_id = {family.get("id"): family for family in families}
    for item in corrections:
        fid = item["family"]
        moved = {aliases.get(x, x): to for x, to in item.get("move_children", {}).items()}
        drop = {aliases.get(x, x) for x in item.get("remove_children", [])} | set(moved)
        spouse = {
            labels.get("father", "father"): item.get("husband"),
            labels.get("mother", "mother"): item.get("wife"),
        }
        kept = []
        for e in edges:
            if e.get("family") == fid and e.get("status") == "export":
                if e["child"] in drop:
                    continue
                new = spouse.get(e.get("role"))
                if new:
                    e["parent"] = aliases.get(new, new)
                    e["sources"] = list(dict.fromkeys(e.get("sources", []) + item["sources"]))
            kept.append(e)
        edges[:] = kept
        pairs = {(e["child"], e["parent"]) for e in edges}
        for child, to in moved.items():
            family = by_id[to]
            for role, key in (
                (labels.get("father", "father"), "husband"),
                (labels.get("mother", "mother"), "wife"),
            ):
                parent = family.get(key)
                if parent and (child, parent) not in pairs:
                    edges.append(
                        {
                            "child": child,
                            "parent": parent,
                            "status": "export",
                            "role": role,
                            "sources": list(item["sources"]),
                            "family": to,
                            "text": item.get("public")
                            or labels.get(
                                "corrected_link", "Family memory corrected from dates and names."
                            ),
                        }
                    )
                    pairs.add((child, parent))
        # A corrected spouse may already be this child's parent by another claim: one link stays.
        seen = {}
        for e in edges:
            seen.setdefault((e["child"], e["parent"]), []).append(e)
        edges[:] = [
            e
            for e in edges
            if not (
                e.get("family") == fid
                and e.get("status") == "export"
                and len(seen[(e["child"], e["parent"])]) > 1
            )
        ]


def _probable_identity(data, decision, aliases):
    """A probable identity (from 0.3, or below it on the family's main line): the found person's card leaves the tree and the found parents hang above
    the family's person on a junction carrying the version's weight. Facts are not merged; the found card stays
    in its contribution and is named in `probableIdentities`. Below 0.3 the two cards stay apart unless the decision
    is on the family's `main_line`. From 0.5 it may stay probable: the researcher keeps the facts apart. Returns True
    when the alias was applied."""
    target, alias = decision["canonical"], decision["alias"]
    weight = decision.get("weight")
    if not isinstance(weight, (int, float)) or not decision.get("basis") or not decision.get("sources"):
        raise ValueError("A probable identity must state weight, basis and sources")
    if any(s not in data["sources"] for s in decision["sources"]):
        raise ValueError("Unresolved identity source")
    main = decision.get("main_line") is True
    if weight < 0.3 and not main:
        return False
    people, edges = data["people"], data.get("edges", [])
    other = people[target]
    has = {e["child"] for e in edges if e["parent"] == target}
    kept = []
    for e in edges:
        if e["child"] == alias:
            # The junction: the found parents become this person's parents with the weight of the version.
            e.update(status="hypothesis", weight=weight, identity=alias, **({"main_line": True} if main else {}),
                     sources=list(dict.fromkeys(e.get("sources", []) + decision["sources"])))
        elif e["parent"] == alias:
            if e["child"] in has:
                continue
            w = e.get("weight")
            e["weight"] = min(w, weight) if isinstance(w, (int, float)) else weight
            e["status"] = "hypothesis"
        kept.append(e)
    edges[:] = kept
    found = people.pop(alias)
    # The tile dates the person by the document: a recorded birth beats an empty or estimated one of the family's
    # card, so the child stands in the row by the year the record gives. The found card's other facts stay apart.
    (dated, exact), (own, own_exact) = _birth(found), _birth(other)
    if dated and not own_exact and (exact or not own):
        event = {"type": "birth", "date": dated if exact or _ROUGH.search(dated) else "ABT " + dated,
                 "identity": alias, "sources": list(decision["sources"])}
        other["events"] = [event] + [e for e in other.get("events", [])]
        if "birth" in (other.get("cardPresentation") or {}):
            other["cardPresentation"].update(birth=event["date"], birthKind="source" if exact else "inferred")
    other.setdefault("probableIdentities", []).append(
        {"alias": alias, "weight": weight, "basis": decision["basis"], "name": found.get("name", ""),
         "sources": list(decision["sources"])})
    aliases[alias] = target
    return True


def _apply_identities(data, decisions, labels=None):
    labels = labels or {}
    aliases = dict(data.get('identityAliases', {}))
    if any(alias in data['people'] or target not in data['people'] for alias, target in aliases.items()):
        raise ValueError('Imported identity aliases must target an active canonical person')
    people = data["people"]
    probable = set()
    for decision in decisions.get("merges", []):
        target, alias = decision["canonical"], decision["alias"]
        if target == alias or target not in people or alias not in people:
            raise ValueError("Identity endpoints must be distinct existing people")
        if target in aliases or alias in aliases:
            raise ValueError("Chained identity decisions require an explicit review")
        if decision.get("status") == "probable":
            if _probable_identity(data, decision, aliases):
                probable.add(alias)
            continue
        # Two ways to accept an identity (author, 28.10.2026): family confirmation where the family has its
        # own knowledge (roughly the XX century after ~1926), or the research decision by the weight of the
        # documents ('accepted_evidence', with the argument in 'evidence') — the default for anything older.
        status = decision.get("status")
        if status not in ("accepted_family_confirmation", "accepted_evidence") or not decision.get(
            "sources"
        ):
            raise ValueError("Identity decision must have explicit acceptance and sources")
        if status == "accepted_evidence" and not decision.get("evidence"):
            raise ValueError(
                'Evidence-based identity decision must state its argument in "evidence"'
            )
        if any(s not in data["sources"] for s in decision["sources"]):
            raise ValueError("Unresolved identity source")
        check_review(decision)
        p, other = people[target], people[alias]
        for field in ('name', 'summary', 'birth'):
            if not isinstance(decision.get(field), str) or not decision[field]:
                raise ValueError(f'Identity decision requires {field}; use research form identity.json')
        # A person may absorb several cards (one per decision): each step keeps its own undo record.
        history = p.pop("identityHistory", [])
        history.append(
            {
                "decision": copy.deepcopy(decision),
                "priorCanonical": copy.deepcopy(p),
                "priorAlias": copy.deepcopy(other),
                "priorEdges": copy.deepcopy(
                    [
                        e
                        for e in data.get("edges", [])
                        if e["child"] in (target, alias) or e["parent"] in (target, alias)
                    ]
                ),
            }
        )
        p["identityHistory"] = history
        # Old readings remain in immutable inputs/history; active facts distinguish them.
        facts = copy.deepcopy(p.get("facts", [])) + copy.deepcopy(other.get("facts", []))
        rejected = decision.get("reject_export_birth")
        for f in facts:
            if (
                rejected
                and f.get("status") == "export"
                and f.get("label") == labels.get("birth", "Birth")
                and rejected["year"] in f.get("text", "")
            ):
                f.update(status="conflict", public_fact=rejected["public_fact"])
        p["facts"] = []
        for f in facts:
            comparable = {k: v for k, v in f.items() if k != "_contribution_file"}
            if not any(
                {k: v for k, v in prior.items() if k != "_contribution_file"} == comparable
                for prior in p["facts"]
            ):
                p["facts"].append(f)
        for field in ('names', 'events', 'notes', 'media'):
            for value in copy.deepcopy(other.get(field, [])):
                if value not in p.setdefault(field, []):
                    p[field].append(value)
        # Life assessment uses the independent participants retained in history;
        # a copied flag cannot counter a death in the combined event list.
        p["name"] = decision["name"]
        p["summary"] = decision["summary"]
        p["identityAliases"] = p.get("identityAliases", []) + [alias]
        if other.get("confirmation") and not p.get("confirmation"):
            p["confirmation"] = copy.deepcopy(other["confirmation"])
        np = p.setdefault("namePresentation", {})
        np.update(display=decision["name"], full=decision["name"], surnameUnknown=False, note="")
        if decision.get("maiden_surname"):
            np.update(
                maidenSurname=decision["maiden_surname"],
                isWoman=True,
                isWife=True,
                maidenSources=decision["sources"],
                maidenStatus="verified",
            )
        cp = p.setdefault("cardPresentation", {})
        cp.update(
            birth=decision["birth"],
            birthKind="inferred" if decision["birth"].startswith("ABT ") else "source",
            dateBasis="",
        )
        cp["dateReference"] = {}
        if decision.get("place"):
            cp.update(place=decision["place"], placeRole="birth")
        if decision.get("date_reference"):
            cp["dateReference"] = decision["date_reference"]
        aliases[alias] = target
        del people[alias]
        withdrawn = set(decision.get("withdraw_parent_placeholders", []))
        data["edges"][:] = [
            e
            for e in data.get("edges", [])
            if not (e["child"] == target and e["parent"] in withdrawn)
        ]
    resolve = lambda pid: aliases.get(pid, pid)
    for e in data.get("edges", []):
        e["child"], e["parent"] = resolve(e["child"]), resolve(e["parent"])
        for key in ('from', 'to'):
            if key in e:
                e[key] = resolve(e[key])
        if e["child"] == e["parent"]:
            raise ValueError(f"edges: identity decision introduced a self-parent {e['child']}")
    if data.get("root") is not None:
        data["root"] = resolve(data["root"])
    unique = {}
    for e in data.get("edges", []):
        key = (e["child"], e["parent"], e.get("role"))
        if key not in unique:
            unique[key] = e
        else:
            prior = unique[key]
            prior["sources"] = list(dict.fromkeys(prior.get("sources", []) + e.get("sources", [])))
            if EDGE_RANK.get(e.get("status"), 0) > EDGE_RANK.get(prior.get("status"), 9):
                prior["status"] = e["status"]
    data["edges"] = list(unique.values())
    for a in data.get("associations", []):
        for key in ("from", "to"):
            if key in a:
                a[key] = resolve(a[key])
    for f in data.get("families", []):
        for key in ("husband", "wife"):
            if key in f:
                f[key] = resolve(f[key])
        f["children"] = list(dict.fromkeys(resolve(x) for x in f.get("children", [])))
    corrections = decisions.get("family_corrections", [])
    for item in corrections:
        if (
            not item.get("evidence")
            or not item.get("sources")
            or any(x not in data["sources"] for x in item["sources"])
        ):
            raise ValueError("A family correction must state its argument and sources")
        if any(
            item.get(key) and aliases.get(item[key], item[key]) not in people
            for key in ("husband", "wife")
        ):
            raise ValueError("A family correction must name existing people")
    correct_families(data.get("families", []), corrections, aliases)
    correct_family_edges(
        data["edges"], data.get("families", []), corrections, aliases, labels=labels
    )
    data["familyCorrections"] = corrections
    selection = data.get("gallerySelection", {})
    for alias, target in aliases.items():
        if alias in probable:
            continue
        for item in selection.pop(alias, []):
            if item not in selection.setdefault(target, []):
                selection[target].append(item)
        statuses = data.get("cardStatuses", {})
        moved = statuses.pop(alias, None) or {}
        if moved.get("review") and target in statuses and not statuses[target].get("review"):
            statuses[target]["review"] = moved["review"]
    # A fact a decision makes stale ("identity still open") leaves the card, not the record: it stays in
    # the contribution it came from and in retiredFacts here. Removing the entry restores it.
    for item in decisions.get("retire_facts", []):
        pid = aliases.get(item["person"], item["person"])
        if not item.get("reason"):
            raise ValueError("Retiring a fact must state the reason")
        p = people[pid]
        for label in item["labels"]:
            hit = [f for f in p.get("facts", []) if f.get("label") == label]
            if not hit:
                raise ValueError(f"No fact to retire: {pid} / {label}")
            p["facts"] = [f for f in p["facts"] if f.get("label") != label]
            p.setdefault("retiredFacts", []).extend(
                dict(f, retiredBecause=item["reason"]) for f in hit
            )
    # A name form someone wrote in a reader language (`names[].lang`, not a document's spelling) is that
    # language's tile name; a saved decision below wins over it.
    for p in people.values():
        for n in p.get("names", []):
            if n.get("lang") and n.get("type") not in DOCUMENT_NAME_TYPES and n.get("display"):
                p.setdefault("namePresentation", {}).setdefault("byLanguage", {}).setdefault(n["lang"], n["display"])
    # RES-18: the best reading of a name is decided here with its argument; the form as entered stays in sourceName.
    # `display` is the form in the family's main language, `by_language` the form for another reader language.
    for item in decisions.get("name_forms", []):
        if (
            not item.get("evidence")
            or not item.get("sources")
            or any(s not in data["sources"] for s in item["sources"])
            or not (item.get("display") or item.get("by_language"))
        ):
            raise ValueError("A name form must state its argument, resolved sources and a form")
        if aliases.get(item["person"], item["person"]) not in people:
            continue  # the person left the tree (renamed or merged by research); instance check hints
        p = people[aliases.get(item["person"], item["person"])]
        np = p.setdefault("namePresentation", {})
        if item.get("display"):
            p["name"] = item["display"]
            np.update(display=item["display"], full=item["display"], decided=True)
        if item.get("by_language"):
            np.setdefault("byLanguage", {}).update(item["by_language"])
    resolved_distinct = []
    for item in decisions.get("distinct", []):
        a, b = resolve(item.get("a")), resolve(item.get("b"))
        if not a or not b or a not in people or b not in people or a == b:
            raise ValueError(
                "Distinct identity endpoints must resolve to different existing people"
            )
        if (
            not item.get("evidence")
            or not item.get("sources")
            or any(x not in data["sources"] for x in item["sources"])
        ):
            raise ValueError(
                "Distinct identity decision must state its argument and resolved sources"
            )
        resolved_distinct.append({**item, "a": a, "b": b})
    data["distinct"] = resolved_distinct
    data["identityAliases"] = aliases
    validate_graph(data)
    return data


def validate_graph(data):
    """Validate the final active graph, after every merge and family correction."""
    people, sources = data["people"], data["sources"]
    if data.get("root") is not None and data["root"] not in people:
        raise ValueError("root: unknown person " + str(data["root"]))
    parents = {}
    for i, edge in enumerate(data.get("edges", [])):
        where = f"edges[{i}] ({edge.get('child')} -> {edge.get('parent')})"
        if edge.get("child") not in people or edge.get("parent") not in people:
            raise ValueError(where + ": unknown endpoint")
        if edge.get("status") == "verified" and not edge.get("sources"):
            raise ValueError(where + ": verified link without sources")
        if any(s not in sources for s in edge.get("sources", [])):
            raise ValueError(where + ": unresolved sources")
        parents.setdefault(edge["child"], []).append(edge["parent"])
    done, active = set(), []

    def visit(pid):
        if pid in active:
            raise ValueError("Ancestor cycle: " + " -> ".join(active + [pid]))
        if pid in done:
            return
        active.append(pid)
        for parent in parents.get(pid, []):
            visit(parent)
        active.pop()
        done.add(pid)

    for pid in people:
        visit(pid)
    for family in data.get("families", []):
        for pid in [family.get("husband"), family.get("wife"), *family.get("children", [])]:
            if pid and pid not in people:
                raise ValueError(f"families[{family.get('id')}]: unknown endpoint {pid}")
