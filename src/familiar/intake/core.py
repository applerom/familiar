# START_MODULE_CONTRACT: MOD-INTAKE-CORE
# PURPOSE: Turn attributed family inputs into traceable snapshot assertions without guessing identity.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - existing person anchors resolve working research people and identity successors [review: engine lead]
# - repeated input is idempotent and names alone produce only candidates [review: engine lead]
# - missing readings and escaping destinations are rejected before writing [review: engine lead]
# - imported tree claims remain hypotheses with source text through merge and undo [review: engine lead]
# - attributed union notes preserve unsupported GEDCOM phrases in the snapshot [review: engine lead]
# - memory narrator references and per-component name inferences stay attached through canonical intake [review: engine lead]
# - person-bound archive notes retain literal text, testimony and uncertainty without inventing events [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (the shared family boundary contract)
# - docs/PRD.md#FORMS
# - MOD-TREE-BUILDER (canonical snapshot display fields)
# - MOD-INTAKE-NAMES (cross-script candidate comparison)
# - MOD-INTAKE-GEDCOM (literal phrase notes)
# :END_MODULE_CONTRACT
import hashlib
import json
import re


def read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def safe(instance, key, suffix=""):
    path = (instance.path(key) / suffix).resolve()
    if not path.is_relative_to(instance.root):
        raise ValueError("intake writes must remain inside the family")
    return path


def token(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("ids must use ASCII letters, digits, hyphens or underscores")
    return value


from familiar.instance.gate import boundary


@boundary('writer')
def ingest(instance, data, kind, original=None, accepted_by=None, own=False):
    # A GEDCOM is another tree's claim unless the host says it is the family's own tree: then it is the family's word.
    foreign = kind == 'gedcom' and not own
    from html import unescape

    from familiar.instance.subjects import normalized
    def decoded(value):
        if isinstance(value, str):
            for _ in range(10):
                after = unescape(value)
                if after == value:
                    break
                value = after
            return value
        if isinstance(value, list):
            return [decoded(v) for v in value]
        if isinstance(value, dict):
            return {decoded(k): decoded(v) for k, v in value.items()}
        return value
    if not isinstance(data, dict) or any(not isinstance(data.get(k, []), list) for k in ('people', 'families', 'items')):
        raise ValueError('intake must be an object with people, families and items arrays')
    literal_items = [dict(item) for item in data.get('items', [])] if kind == 'memory' else None
    data = normalized(decoded(data))
    original_bytes = original.read_bytes() if original is not None else None
    original_digest = hashlib.sha256(original_bytes).hexdigest() if original_bytes is not None else None
    if data.get('table_sha256') and original_digest != data['table_sha256']:
        raise ValueError('Table memory requires --original matching table_sha256')
    if literal_items is not None:
        data['items'] = literal_items
    # One editable enabled flag removes a proposed family and both participant facts.
    for proposal in data.get('relationship_hypotheses', []):
        if proposal.get('enabled') is not True:
            continue
        data.setdefault('families', []).append(proposal['family'])
        for pid, note in proposal['notes'].items():
            next(p for p in data['people'] if p['id'] == pid).setdefault('notes', []).append(note)
    from familiar.instance.gate import require_assertions
    require_assertions(data)
    visibility = data.get('visibility', 'family')
    if kind == 'memory':
        from .feedback import ask_private
        for item in data.get('items', []):
            locator = item.get('original', '')
            if re.fullmatch(r'family/feedback/inbox/[0-9a-f-]{36}\.json', locator):
                if ask_private(instance, read(instance._inside(locator), {})):
                    visibility = 'search-only'
        if visibility not in ('family', 'search-only'):
            raise ValueError('Memory visibility must be family or search-only')
    search_only = kind == 'memory' and visibility == 'search-only'
    tree_people = [] if search_only else data.get('people', [])
    tree_families = [] if search_only else data.get('families', [])
    ident = token(data["id"])
    digest = hashlib.sha256((json.dumps(data, sort_keys=True) + ('|own' if own else '')).encode()).hexdigest()
    if original_digest:
        digest = hashlib.sha256((digest + original_digest).encode()).hexdigest()
    report_path = safe(instance, "state", f"intake/{ident}.json")
    prior = read(report_path, {})
    if prior:
        if prior["digest"] != digest:
            raise ValueError("intake id already used with different content; use a new id")
        return prior
    snapshot = safe(instance, "tree_snapshot")
    changes_tree = bool(tree_people or tree_families)
    people = read(snapshot / "people.json", {"people": []})["people"] if changes_tree else []
    families = read(snapshot / "families.json", {"families": []})["families"] if changes_tree else []
    known = {p["id"]: p for p in people}
    from familiar.checks.engine import _known_people
    refs, candidates = {}, []
    items = data.get("items", [])
    note_items = [item for item in items if item.get('role') == 'note'] if kind == 'memory' and not search_only else []
    working = _known_people(instance) if changes_tree or note_items else {}
    grounds = {ident}
    if kind == "memory":
        used_items = set()
        for file in safe(instance, "memory").glob("*.json"):
            try:
                previous = read(file, {})
            except (ValueError, OSError):
                continue  # Family validation reports this unrelated malformed telling.
            prior_items = previous.get('items', []) if isinstance(previous, dict) else []
            if isinstance(prior_items, list):
                used_items.update(item['id'] for item in prior_items if isinstance(item, dict) and 'id' in item)
        for key in ("told_by", "date"):
            if not data.get(key):
                raise ValueError(f"memory requires {key}")
        grounds = set()
        for item in items:
            token(item["id"])
            if item["id"] in grounds or item["id"] in used_items:
                raise ValueError("memory item ids must be unique across tellings")
            text = item.get('text')
            if not isinstance(text, str) or not text.strip() or item.get("strength") not in (
                "firm",
                "hearsay",
            ):
                raise ValueError("each memory item needs text and firm/hearsay strength")
            if 'witness' in item and (not isinstance(item['witness'], str) or not item['witness'].strip()):
                raise ValueError('memory witness must be nonempty text')
            grounds.add(item["id"])

    def basis(row):
        result = row.get("provenance", [ident] if kind != "memory" else [])
        if not result or not set(result) <= grounds:
            raise ValueError("every assertion must cite this intake or one of its memory items")
        return result

    for row in tree_people:
        local = token(row["id"])
        if local in refs:
            raise ValueError("duplicate local person id")
        if row.get("living") is not None and type(row["living"]) is not bool:
            raise ValueError("living must be boolean")
        pid = row.get("existing", f"{ident}-{local}")
        if row.get("existing"):
            if pid not in working:
                raise ValueError(f"unknown existing person: {pid}; inspect ids with tree build --view working")
            pid = working[pid]['id']
        refs[local] = pid
        if row.get('existing') and pid not in known:
            if any(row.get(key) for key in ('names', 'events', 'notes')) or row.get('living') is not None:
                raise ValueError('Use research contribute for claims about a research person; intake existing may anchor kinship only')
            known[pid] = dict(working[pid], names=working[pid].get('names', []))
            continue
        names = []
        for name in row.get("names", []):
            names.append(
                dict(
                    name,
                    provenance=basis(name),
                    display=" ".join(filter(None, [name.get("given"), name.get("patronymic"), name.get("surname")])),
                    **({'status': 'hypothesis'} if foreign else {}),
                )
            )
        events = [
            dict(
                e,
                provenance=basis(e),
                # Whose tree it is never settles whether a person has died: a death read from a
                # GEDCOM stays an imported claim, so life-status protection is the same in both modes.
                **({'status': 'hypothesis'} if foreign or kind == 'gedcom' and e.get('type') == 'death' else {}),
                tag=e.get(
                    "tag", {"birth": "BIRT", "death": "DEAT"}.get(e["type"], e["type"].upper())
                ),
            )
            for e in row.get("events", [])
        ]
        notes = [dict(n, provenance=basis(n), plain=n["text"]) for n in row.get("notes", [])]
        if pid in known:
            person = known[pid]
            for key, values in [("names", names), ("events", events), ("notes", notes)]:
                person[key].extend(v for v in values if v not in person[key])
            if names and kind != 'gedcom':
                # A bridge label stands in for an unnamed person; a told name replaces it.
                person.pop('placeholder', None)
            for old in people:
                if old['id'] == pid:
                    continue
                if any(n.get('display') and n['display'].casefold() == o.get('display', '').casefold()
                       for n in person['names'] for o in old['names']):
                    candidates.append({'canonical': old['id'], 'alias': pid, 'status': 'candidate',
                        'sources': sorted(grounds), 'evidence': 'Name overlap only; identity unaccepted',
                        'next_test': 'Compare a paper naming relatives and dates.'})
        else:
            for old in people:
                if any(
                    n["display"]
                    and n["display"].casefold()
                    == o.get("display", " ".join([o.get("given", ""), o.get("surname", "")]))
                    .strip()
                    .casefold()
                    for n in names
                    for o in old["names"]
                ):
                    candidates.append(
                        {
                            "canonical": old["id"],
                            "alias": pid,
                            "status": "candidate",
                            "sources": sorted(grounds),
                            "evidence": "Name overlap only; identity unaccepted",
                            "next_test": "Compare a paper naming relatives and dates.",
                        }
                    )
            person = {
                "id": pid,
                **({"placeholder": row["placeholder"]} if row.get("placeholder") else {}),
                "sex": row.get("sex"),
                "living": row.get("living"),
                "life_origin": kind,
                "names": names,
                "events": events,
                "notes": notes,
            }
            people.append(person)
            known[pid] = person
    from .names import _overlap
    for pid in refs.values():
        for old in people:
            if old['id'] == pid or any(c['canonical'] == old['id'] and c['alias'] == pid for c in candidates):
                continue
            evidence = _overlap(known[pid]['names'], old['names'])
            if evidence:
                candidates.append({'canonical': old['id'], 'alias': pid, 'status': 'candidate',
                                   'sources': sorted(grounds), 'evidence': evidence,
                                   'next_test': 'Compare dated records and relatives; never merge by name alone.'})
    for row in tree_families:
        family = {
            "id": f"{ident}-{token(row['id'])}",
            "husband": refs.get(row.get("husband")),
            "wife": refs.get(row.get("wife")),
            "children": [refs[x] for x in row.get("children", [])],
            "events": [],
            "provenance": basis(row),
            **({'notes': [dict(n, provenance=basis(n)) for n in row['notes']]} if row.get('notes') else {}),
            **({k: row[k] for k in ("derived", "basis")} if row.get("derived") is True else {}),
            "status": 'hypothesis' if foreign or row.get('status') == 'hypothesis' or any(
                item.get('strength') == 'hearsay' and item['id'] in basis(row) for item in items) else 'export',
        }
        for key in ("husband", "wife"):
            if row.get(key) and row[key] not in refs:
                raise ValueError("unknown family member")
        family["events"] = [dict(e, provenance=basis(e), tag=e.get("tag", "MARR"),
                                **({'status': 'hypothesis'} if foreign else {}))
                            for e in row.get("events", [])]
        same = next(
            (
                f
                for f in families
                if all(f.get(k) == family[k] for k in ("husband", "wife", "children"))
            ),
            None,
        )
        if same:
            same["provenance"] = sorted(set(same["provenance"] + family["provenance"]))
            same["events"].extend(e for e in family["events"] if e not in same["events"])
            if family.get('notes'):
                same.setdefault('notes', []).extend(n for n in family['notes'] if n not in same['notes'])
        else:
            families.append(family)
    files = {}
    binary = None
    facts = {}
    if kind == "memory":
        memory = {k: data[k] for k in ("id", "told_by", "date", "items")}
        memory['visibility'] = visibility
        if search_only:
            memory.update({k: data[k] for k in ('people', 'families', 'narrator') if k in data and data[k]})
        if data.get('narrator') in refs:
            memory['narrator'] = refs[data['narrator']]
        for item in memory["items"]:
            item.setdefault('witness', data['told_by'])
            pid = item.get('person')
            if pid in refs:
                item['person'] = refs[pid]
            if item.get('role') == 'note' and not search_only:
                pid = item.get('person')
                if pid not in refs.values():
                    if pid not in working:
                        raise ValueError(f'memory note {item["id"]} needs a local or working-tree person ID')
                    pid = working[pid]['id']
                item['person'] = pid
                if item.get('status', 'reported') not in {'reported', 'possible'}:
                    raise ValueError(f'memory note {item["id"]} status must be reported or possible')
                label = item.get('label', 'notes')
                if not isinstance(label, str) or not label.strip():
                    raise ValueError(f'memory note {item["id"]} label must be nonempty text')
                facts.setdefault(pid, []).append({'label': label, 'text': item['text'], 'sources': [item['id']],
                    'status': 'hypothesis' if item['strength'] == 'hearsay' or item.get('status') == 'possible' else 'export'})
        if original:
            binary = safe(instance, "originals", f"{ident}/{original.name}")
            memory['original'] = binary.relative_to(instance.root).as_posix()
            memory['original_sha256'] = original_digest
        files[safe(instance, "memory", f"{ident}.json")] = memory
    elif kind == "paper":
        record = data["record"]
        if (record.get("reading") is not None and not isinstance(record['reading'], str)) or not (
            record.get("reading") or record.get("fields")
        ):
            raise ValueError("paper requires a literal reading or nonempty literal fields")
        for key in ("title", "source", "language"):
            if not record.get(key):
                raise ValueError(f"paper requires {key}")
        dest = safe(instance, "originals", f"{ident}/{original.name}")
        record = dict(
            record,
            id=ident,
            kind="home-paper",
            source=dict(record["source"], image=dest.relative_to(instance.root).as_posix()),
            people={name: refs[pid] for name, pid in record.get("people", {}).items()},
        )
        files[safe(instance, "records", f"{ident}.json")] = record
        binary = dest
    else:
        binary = safe(instance, "imports", f"{ident}/{original.name}")
        files[safe(instance, "imports", f"{ident}.json")] = {
            "id": ident,
            "kind": "gedcom",
            "original": binary.relative_to(instance.root).as_posix(),
            "living_rule": data["living_rule"],
        }
    # The current graph adapter reads sources/facts from contribution packages.
    # Keep provenance there as well as in the normalized snapshot.
    strengths = {item["id"]: item["strength"] for item in items}
    for row in tree_people:
        pid = refs[row["id"]]
        for field in ("names", "events", "notes"):
            for claim in row.get(field, []):
                if data.get("table_sha256") and field == "names":
                    continue  # The name already heads the card; the literal stays in memory.
                sources = basis(claim)
                claim_text = claim.get("text") or json.dumps(claim, ensure_ascii=False)
                if data.get("table_sha256") and field == "events":
                    claim_text = next((i["display_text"] for i in items if i["id"] in sources and i.get("display_text")), claim_text)
                if foreign:
                    claim_text = 'Recorded in another tree (unverified): ' + claim_text
                    if row.get('source_text'):
                        claim_text += '; ' + '; '.join(row['source_text'])
                facts.setdefault(pid, []).append(
                    {
                        **({k: claim[k] for k in ("derived", "basis")} if claim.get("derived") is True else {}),
                        "label": field,
                        **({'eventType': claim.get('type')} if field == 'events' else {}),
                        "text": claim_text,
                        "status": "hypothesis"
                        if foreign or claim.get('status') in {'hypothesis', 'possible'} or any(strengths.get(s) == "hearsay" for s in sources)
                        else "export",
                        "sources": sources,
                    }
                )
    contribution = {
        "update": {
            "person": next(iter(refs.values()), next(iter(known), None)),
            "title": "Family intake",
            "date": data.get("date", "unknown"),
            "text": "Attributed intake; identity remains to be researched",
            "status": "hypothesis" if foreign else "export",
            "sources": sorted(grounds),
        },
        "schema": 1,
        "author": "intake",
        "facts": facts,
        "sources": {sid: {"kind": kind, "intake": ident} for sid in grounds},
    }
    if not changes_tree:
        contribution.pop('update', None)
    if not search_only:
        files[safe(instance, 'contributions', f'intake/{ident}.json')] = contribution
    for path in [*files, *([binary] if binary else [])]:
        if path.exists():
            raise ValueError(f"refusing to replace existing source: {path}")
    report = {
        "id": ident,
        "kind": kind,
        "digest": digest,
        "people": len(refs),
        "families": len(data.get("families", [])),
        **({'items': len(items), 'notes': len(note_items)} if kind == 'memory' else {}),
        "candidates": candidates,
        "losses": data.get("losses", {}),
        "next_step": "researcher: memory-first; name one bridge paper before searching indexes",
    }
    from familiar.instance.writer import mutate
    if changes_tree:
        files[snapshot / 'people.json'] = {'people': people}
        files[snapshot / 'families.json'] = {'families': families}
    narrator = data.get('narrator') or (data.get('told_by') if data.get('told_by') in refs else None)
    if narrator and not search_only:
        if narrator not in refs:
            raise ValueError('narrator must name a local person id')
        metadata_path = safe(instance, 'tree_metadata')
        metadata = read(metadata_path, {})
        metadata['root'] = refs[narrator]
        metadata['narrator'] = refs[narrator]
        files[metadata_path] = metadata
    if kind == "memory":
        from datetime import UTC, datetime
        from getpass import getuser
        from uuid import UUID
        for item in items:
            match = re.fullmatch(r"family/feedback/inbox/([0-9a-f-]{36})\.json", item.get("original", ""))
            if not match:
                continue
            try:
                identity = str(UUID(match.group(1)))
            except ValueError:
                continue
            if identity != match.group(1) or not instance._inside(item["original"]).is_file():
                continue
            mark = instance._inside(f"family/feedback/read/{identity}.json")
            if not mark.exists():
                files[mark] = {"read_at": datetime.now(UTC).isoformat(), "intake": ident, "by": accepted_by or getuser()}
    files[report_path] = report
    if binary:
        files[binary] = original_bytes
    mutate(instance, files, exclusive=[p for p in files if p not in {snapshot / 'people.json', snapshot / 'families.json', safe(instance, 'tree_metadata')}])
    return report
