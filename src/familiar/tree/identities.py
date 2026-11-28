# START_MODULE_CONTRACT: MOD-TREE-IDENTITIES
# PURPOSE: Resolve recorded identity decisions while retaining the pre-merge evidence and undo history.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - a merge retains both source sets and its undo record [review: engine lead]
# - disputed decisions retain their conflict and next test [review: engine lead]
# - final edges have existing endpoints and resolved evidence [review: engine lead]
# - merged links retain their evidence and existing conflict [review: engine lead]
# - materialized aliases point only to active canonical people [review: engine lead]
# - a probable identity keeps independent people and adds only hypothetical parent links [review: engine lead]
# - an identity accepted by evidence below 0.9 caps only the links a line crosses between the two cards; links within one card and the family's own confirmation stay whole [review: engine lead]
# - only accepted identities enter the alias index or transfer attributed facts [test: tests/gate/test_data_guarantees.py::test_only_recorded_events_open_a_card]
# - withdrawing a marked snapshot card requires a reason and leaves a reversible source [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#INSTANCE
# :END_MODULE_CONTRACT
"""Apply explicit, source-backed identity decisions to a derived graph only."""

import copy
import re

# When two edges collapse into one, the stronger claim survives; a conflict is never overwritten.
EDGE_RANK = {"hypothesis": 1, "export": 2, "verified": 3, "conflict": 4}
FIRM_IDENTITY = 0.9
DRAWN_LINK = 0.30
# A document's own spelling of a name: shown in the card's "More" with its source, never on a tile.
DOCUMENT_NAME_TYPES = {"recorded", "as-written", "indexed"}
DELETION_MARK = re.compile(r"[\s\-–—]*(?:удалить|delete|usunąć)[\s.!]*", re.IGNORECASE)


def marked_for_deletion(person):
    return bool(DELETION_MARK.fullmatch(person.get("name") or ""))


def _withdraw_snapshot_cards(data, decisions):
    """Remove only a marked import card whose links are covered by the decision."""
    people = data["people"]
    withdrawn = set()
    for item in decisions:
        pid, sources = item["person"], set(item.get("sources", []))
        person = people.get(pid, {})
        if (pid not in data.get("_snapshotPeople", ()) or not marked_for_deletion(person)
                or not item.get("reason") or not sources or not sources <= data["sources"].keys()
                or pid == data.get("root") or pid in data["identityAliases"].values()
                or any(pid in (pair["a"], pair["b"]) for pair in data["distinct"])):
            raise ValueError(f"Cannot withdraw snapshot card {pid}: review the deletion mark, references and sources")
        links = [e for e in data["edges"] if pid in (e["child"], e["parent"])]
        if (person.get("facts") or person.get("events") or person.get("notes") or person.get("probableIdentities")
                or any(e.get("status") != "export" or not set(e.get("sources", [])) <= sources for e in links)
                or any(pid in (a.get("from"), a.get("to")) for a in data.get("associations", []))):
            raise ValueError(f"Cannot withdraw snapshot card {pid}: review its evidence first")
        withdrawn.add(pid)
    if not withdrawn:
        return
    data["_withdrawnSnapshotCards"] = sorted(withdrawn)
    data["edges"] = [e for e in data["edges"] if not withdrawn.intersection((e["child"], e["parent"]))]
    for family in data.get("families", []):
        for key in ("husband", "wife"):
            if family.get(key) in withdrawn:
                family.pop(key)
        family["children"] = [pid for pid in family["children"] if pid not in withdrawn]
    for pid in withdrawn:
        del people[pid]
        data.get("cardStatuses", {}).pop(pid, None)
        data.get("gallerySelection", {}).pop(pid, None)

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


def _probable_identity(data, decision):
    """A junction can suggest kinship, while both people retain their own evidence."""
    target, alias = decision["canonical"], decision["alias"]
    weight = decision.get("weight")
    if not isinstance(weight, (int, float)) or not decision.get("basis") or not decision.get("sources"):
        raise ValueError("A probable identity must state weight, basis and sources")
    if any(s not in data["sources"] for s in decision["sources"]):
        raise ValueError("Unresolved identity source")
    main = decision.get("main_line") is True
    if weight < DRAWN_LINK and not main:
        return
    people, edges = data["people"], data["edges"]
    people[target].setdefault("probableIdentities", []).append(
        {"alias": alias, "weight": weight, "basis": decision["basis"], "name": people[alias].get("name", ""),
         "sources": list(decision["sources"])})
    existing = {(edge["child"], edge["parent"]) for edge in edges}
    junction = []
    for edge in edges:
        if edge.get("identity") or edge.get("status") in {"rejected", "disproved", "conflict"}:
            continue
        child, parent = edge["child"], edge["parent"]
        if alias not in (child, parent):
            continue
        child, parent = (target if pid == alias else pid for pid in (child, parent))
        if child == parent or (child, parent) in existing:
            continue
        link = {**edge, "child": child, "parent": parent, "status": "hypothesis", "identity": alias}
        if "from" in link:
            link["from"] = parent
        if "to" in link:
            link["to"] = child
        own_weight = edge.get("weight")
        link["weight"] = min(own_weight, weight) if isinstance(own_weight, (int, float)) else weight
        if main:
            link["main_line"] = True
        link["sources"] = list(dict.fromkeys(edge.get("sources", []) + decision["sources"]))
        junction.append(link)
        existing.add((child, parent))
    edges.extend(junction)


def _carry_weight(data, decision, own, alias):
    """An identity accepted at 0.6 ties what one card knows above the person to what the other knows below: exactly
    the links a line crosses there weigh no more than the merge. Links within one card never depended on it, and a
    firm identity (from 0.9) is one person: a long line does not fade by its merges."""
    weight = decision.get("weight")
    if type(weight) not in (int, float) or not 0 <= weight < FIRM_IDENTITY:
        return
    edges = [e for e in data.get("edges", []) if e.get("status") not in ("conflict", "rejected", "disproved")]
    sides = (own, {alias})
    up = [[e for e in edges if e.get("child") in side] for side in sides]
    down = [[e for e in edges if e.get("parent") in side]
            + [f for f in data.get("families", []) if f.get("children")
               and f.get("status") not in ("conflict", "rejected", "disproved")
               and {f.get("husband"), f.get("wife")} & side] for side in sides]
    if bool(up[0]) == bool(up[1]):
        return  # parents on both cards or on none: nothing hangs on the merge alone
    above = 0 if up[0] else 1
    other = 1 - above
    # A recorded wedding on the other card identifies the groom or bride
    # through this junction. It does not provide children on that side.
    married = any(f.get("husband") and f.get("wife") and f.get("status") in {"verified", "export"}
                  and {f["husband"], f["wife"]} & sides[other] for f in data.get("families", []))
    if not (down[other] or married):
        return
    # The parents hang on the junction; when their own card also knows children, only the other card's children do.
    for row in down[other] if down[above] and down[other] else up[above]:
        if type(row.get("weight")) not in (int, float) or row["weight"] > weight:
            row["weight"] = row["mergeWeight"] = weight


def _apply_identities(data, decisions, labels=None):
    labels = labels or {}
    aliases = dict(data.get('identityAliases', {}))
    if any(alias in data['people'] or target not in data['people'] for alias, target in aliases.items()):
        raise ValueError('Imported identity aliases must target an active canonical person')
    people = data["people"]
    probable = []
    for decision in decisions.get("merges", []):
        target, alias = decision["canonical"], decision["alias"]
        if target == alias or target not in people or alias not in people:
            raise ValueError("Identity endpoints must be distinct existing people")
        if target in aliases or alias in aliases:
            raise ValueError("Chained identity decisions require an explicit review")
        if decision.get("status") == "probable":
            probable.append(decision)
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
        if status == "accepted_evidence":
            _carry_weight(data, decision, {target, *(a for a, t in aliases.items() if t == target)}, alias)
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
            # One link both cards know: a merge caps only what it brought, so the claim without it keeps its weight.
            for capped, whole in ((prior, e), (e, prior)):
                if "mergeWeight" in capped and "mergeWeight" not in whole:
                    own = whole.get("weight")
                    if own is None:
                        prior.pop("weight", None)
                    else:
                        prior["weight"] = max(own, capped["weight"])
                    prior.pop("mergeWeight", None)
                    break
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
    for decision in probable:
        target, alias = resolve(decision["canonical"]), resolve(decision["alias"])
        if target != alias:
            _probable_identity(data, {**decision, "canonical": target, "alias": alias})
    _withdraw_snapshot_cards(data, decisions.get("withdraw_snapshot_cards", []))
    data.pop("_snapshotPeople", None)
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
