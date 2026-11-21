# START_MODULE_CONTRACT: MOD-TREE-CONTRIBUTIONS
# PURPOSE: Accept researcher findings and explicit revisions atomically with provenance and resolved evidence.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - invalid packages leave the graph unchanged [review: engine lead]
# - contributed spouse unions retain weight, basis and sources with existing or newly contributed people [review: engine lead]
# - sources-only packages publish no reader update [review: engine lead]
# - duplicate source declarations name both owners and keep intake ownership explicit [review: engine lead]
# - replayed claims cannot reactivate a fact retained in retiredFacts [review: engine lead]
# - source references resolve across family packages, including mutual dependencies, without publishing rejected packages [review: engine lead]
# - displayed update order follows recorded dates and sources, never checkout file times [review: engine lead]
# - people may fill an unnamed existing card with sourced name parts while retaining its earlier name [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (the shared family boundary contract)
# - docs/PRD.md#INSTANCE
# - MOD-TREE-BUILDER (configured evidence path)
# :END_MODULE_CONTRACT
"""Merge independent researchers' additive findings without shared-file writes."""

import pickle
import hashlib
import json
import re
from datetime import UTC, datetime


def _read_package(path, project):
    from familiar.instance.gate import require_assertions

    pack = json.loads(path.read_text(encoding="utf-8-sig"))
    require_assertions(pack)
    author = pack["author"]
    if (not isinstance(author, str) or author != path.parent.name
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", author)):
        raise ValueError("Автор не совпадает с собственной папкой")
    if pack.get("schema") != 1:
        raise ValueError("Ожидается schema: 1")
    for sid, source in pack.get("sources", {}).items():
        if not isinstance(source, dict):
            raise ValueError("Ожидается объект источника: " + sid)
        if source.get("local"):
            target = (project / source["local"]).resolve()
            if not target.is_relative_to(project.resolve()) or not target.is_file():
                raise ValueError("Источник недоступен: " + sid)
    return pack


# Every top-level key the merge reads, and the ones a contribution may carry for people. A key outside this set is
# never read: its claims silently stay out of the tree, so the check names it (a wave once wrote links as `relations`).
READ_KEYS = {'_about', 'id', 'schema', 'author', 'title', 'status', 'notes', 'sources', 'people', 'facts',
             'confirmations', 'edges', 'families', 'relationship_decisions', 'fact_replacements', 'events', 'media',
             'update'}
_LINKS = {'relations', 'relationships', 'links', 'parents', 'children', 'kinship'}
_UNIONS = {'unions', 'marriages', 'couples', 'spouses'}


def unread_keys(pack):
    """The top-level keys of a contribution the engine does not read, each with the hint the check prints."""
    hint = lambda key: ('этот ключ не читается; связи — в `edges`' if key in _LINKS else
                        'этот ключ не читается; браки — в `families`' if key in _UNIONS else
                        'этот ключ не читается; его содержимое не попадает в дерево (форма: forms/contribution.json)')
    return [(key, hint(key)) for key in pack if key not in READ_KEYS] if isinstance(pack, dict) else []


def _clone(value):
    """deepcopy of JSON-shaped data at C speed: every package is applied on private copies."""
    return pickle.loads(pickle.dumps(value, pickle.HIGHEST_PROTOCOL))


class Waiting(ValueError):
    """A reference to what another wave has not committed yet: the package waits and applies once it appears."""

    def __init__(self, message, waits):
        super().__init__(message)
        self.waits = sorted({str(w) for w in waits})


def _author(pack, path):
    author = pack.get("author") if isinstance(pack, dict) else None
    return author if isinstance(author, str) and author else path.parent.name


def _merge_contributions(
    directory,
    people,
    edges,
    sources,
    research,
    project,
    associations=None,
    decisions=None,
    root_person=None,
    languages=("en",),
    labels=None,
    families=None,
    record_ids=(),
    evidence_path=None,
):
    labels = labels or {}
    families = families if families is not None else []
    applied, errors, revisions = [], [], []
    unused_warnings = []
    pending = sorted(directory.glob("*/*.json"))
    owners = {sid: evidence_path for sid in sources}
    packages, declared = {}, {}
    # Resolve declarations independently of claims: two otherwise valid packages
    # may cite each other's sources. Only applied packages commit their sources.
    failures = (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError)
    for path in pending:
        try:
            pack = _read_package(path, project)
            packages[path] = pack
            for sid, source in pack.get('sources', {}).items():
                declared.setdefault(sid, source)
        except failures as exc:
            packages[path] = exc
    seen = set()
    while pending:
        before = len(applied)
        retry, errors = [], []
        for path in pending:
            claim = 'package'
            try:
                pack = packages[path]
                if isinstance(pack, Exception):
                    raise pack
                if path not in seen:
                    revisions.append(pack)
                    seen.add(path)
                author = pack["author"]
                pp, ee, ss, ff = (_clone(people), _clone(edges), _clone(sources), _clone(families))
                for sid, source in pack.get("sources", {}).items():
                    claim = 'sources[' + sid + ']'
                    if sid in ss and (ss[sid] != source or owners.get(sid) == evidence_path):
                        other = str(owners[sid].relative_to(project)) if owners.get(sid) else 'ранее объявленный источник'
                        hint = ('Объявлением владеет приём; в evidence нужна только ссылка на ID источника, '
                                'без повторной записи в sources.' if source.get('intake') or ss[sid].get('intake') else
                                'Оставьте одно объявление; в evidence используйте ссылку на ID источника.')
                        raise ValueError(f'Источник {sid} объявлен дважды: {other} и {path.relative_to(project)}. {hint}')
                    ss[sid] = source

                resolved = declared | ss

                def check_fact(fact, resolved=resolved):
                    if fact.get("status") not in (
                        "verified",
                        "hypothesis",
                        "conflict",
                        "export",
                    ) or not fact.get("text"):
                        raise ValueError("Утверждение без текста / статуса")
                    refs = fact.get('sources')
                    if not isinstance(refs, list) or not refs:
                        raise ValueError("Утверждение без списка источников: " + str(fact.get('text')))
                    missing = [s for s in refs if not isinstance(s, str) or s not in resolved]
                    if missing:
                        message = (f"Утверждение {fact.get('text')!r}: неизвестные источники {missing}; "
                                   "объявите их в sources вклада этой семьи или в evidence")
                        if all(isinstance(s, str) for s in missing):
                            raise Waiting(message, missing)
                        raise ValueError(message)

                for pid, person in pack.get("people", {}).items():
                    claim = 'people[' + pid + ']'
                    if pid in pp:
                        prior = pp[pid]
                        if prior.get('name') or any(any(n.get(k) for k in ('display', 'given', 'patronymic', 'surname')) for n in prior.get('names', [])):
                            raise ValueError("Карточка уже имеет имя; используйте facts: " + pid)
                        if set(person) - {'name', 'names'} or not person.get('names'):
                            raise ValueError('Naming an unnamed card needs only name and sourced names: ' + pid)
                        names = _clone(person['names'])
                        for name in names:
                            display = ' '.join(filter(None, (name.get(k) for k in ('given', 'patronymic', 'surname'))))
                            check_fact({'text': display, 'status': 'export', 'sources': name.get('provenance')})
                            name['display'] = display
                        display = names[0]['display']
                        if person.get('name', display) != display:
                            raise ValueError('Name must match the recorded name parts: ' + pid)
                        prior.setdefault('nameHistory', []).append({'name': prior.get('name', ''),
                            'names': _clone(prior.get('names', [])), 'author': author,
                            **({'placeholder': prior['placeholder']} if 'placeholder' in prior else {}),
                            'contribution': str(path.relative_to(project))})
                        prior.update(name=display, names=names)
                        prior.pop('placeholder', None)
                        continue
                    if not person.get("name"):
                        raise ValueError("Нет имени: " + pid)
                    pp[pid] = dict(
                        _clone(person),
                        id=pid,
                        author=author,
                        origin=labels.get("contribution_origin", "Research record · ") + author,
                    )
                    pp[pid].setdefault('facts', [])
                    for n, fact in enumerate(pp[pid].get("facts", [])):
                        claim = f'people[{pid}].facts[{n}]'
                        check_fact(fact)
                        fact["author"] = author
                        fact["_contribution_file"] = str(path.relative_to(project))
                for pid, facts in pack.get("facts", {}).items():
                    claim = 'facts[' + pid + ']'
                    if pid not in pp:
                        raise Waiting("Неизвестный человек: " + pid, [pid])
                    for n, fact in enumerate(facts):
                        claim = f'facts[{pid}][{n}]'
                        check_fact(fact)
                        fact = dict(
                            fact, author=author, _contribution_file=str(path.relative_to(project))
                        )
                        # Provenance identifies the first accepted copy; it must not create duplicate facts.
                        comparable = {k: v for k, v in fact.items() if k != "_contribution_file"}
                        if not any(
                            {k: v for k, v in old.items() if k != "_contribution_file"}
                            == comparable
                            for old in pp[pid]["facts"]
                        ):
                            pp[pid]["facts"].append(fact)
                for pid, confirmation in pack.get("confirmations", {}).items():
                    claim = 'confirmations[' + pid + ']'
                    if pid not in pp:
                        raise Waiting("Подтверждение неизвестного человека: " + pid, [pid])
                    level = confirmation.get("level")
                    if level not in ("document", "family", "mention"):
                        raise ValueError("Неизвестное основание подтверждения: " + pid)
                    if not confirmation.get("sources"):
                        raise ValueError("Подтверждение без разрешимых источников: " + pid)
                    if missing := [s for s in confirmation["sources"] if s not in resolved]:
                        raise Waiting("Подтверждение без разрешимых источников: " + pid, missing)
                    if not all(confirmation.get("basis", {}).get(lang) for lang in languages):
                        raise ValueError(
                            "Confirmation missing basis for configured languages: " + pid
                        )
                    settled = level in ("document", "family")
                    if settled and confirmation.get("identityAccepted") is not True:
                        raise ValueError(
                            "Собственный документ ещё не отождествлён с человеком: " + pid
                        )
                    if confirmation.get("research") != ("settled" if settled else "open"):
                        raise ValueError("Неверное решение о дальнейшем поиске: " + pid)
                    prior = pp[pid].get("confirmation")
                    if prior and prior != confirmation:
                        raise ValueError("Конфликт подтверждения: " + pid)
                    pp[pid]["confirmation"] = _clone(confirmation)
                pairs = {(e["child"], e["parent"]) for e in ee}
                for n, edge in enumerate(pack.get("edges", [])):
                    claim = f'edges[{n}] ({edge.get("child")} → {edge.get("parent")})'
                    check_fact(edge)
                    pair = (edge["child"], edge["parent"])
                    if pair[0] not in pp or pair[1] not in pp:
                        raise Waiting("Связь с неизвестным человеком", [p for p in pair if p not in pp])
                    if pair in pairs:
                        raise ValueError("Связь уже существует; исправление обсудить на доске")
                    ee.append(dict(edge, author=author))
                    pairs.add(pair)
                union_ids = {f.get('id') for f in ff}
                union_pairs = {frozenset((f.get('husband'), f.get('wife'))) for f in ff}
                for n, union in enumerate(pack.get('families', [])):
                    claim = f'families[{n}]'
                    check_fact(union)
                    pair = (union['husband'], union['wife'])
                    if pair[0] != pair[1] and (pair[0] not in pp or pair[1] not in pp):
                        raise Waiting('Union needs two distinct known people', [p for p in pair if p not in pp])
                    if pair[0] == pair[1]:
                        raise ValueError('Union needs two distinct known people')
                    if not isinstance(union.get('id'), str) or not union['id'].strip():
                        raise ValueError('Union needs an id')
                    if union['id'] in union_ids or frozenset(pair) in union_pairs:
                        raise ValueError('Union already exists; use relationship_decisions')
                    if not isinstance(union.get('basis'), str) or not union['basis'].strip():
                        raise ValueError('Union needs a basis')
                    weight = union.get('weight')
                    if type(weight) not in (int, float) or not 0 <= weight <= 1:
                        raise ValueError('Union needs a weight between 0 and 1')
                    added = dict(_clone(union), author=author, provenance=union['sources'])
                    added.setdefault('children', [])
                    added.setdefault('events', [])
                    ff.append(added)
                    union_ids.add(union['id'])
                    union_pairs.add(frozenset(pair))
                from .revisions import apply
                for section in ('relationship_decisions', 'fact_replacements', 'events', 'media'):
                    rows = pack.get(section, {}) if section in ('events', 'media') else pack.get(section, [])
                    for key, row in (rows.items() if isinstance(rows, dict) else enumerate(rows)):
                        claim = f'{section}[{key}]'
                        selected = {key: row} if isinstance(rows, dict) else [row]
                        apply({section: selected}, pp, ee, ff, resolved, check_fact, author, record_ids)
                # Retirement belongs to the claim (literal text and evidence),
                # not the filename or author of a later copy of that claim.
                for person in pp.values():
                    retired = person.get('retiredFacts', [])
                    if retired:
                        person['facts'] = [f for f in person.get('facts', [])
                                           if not any(f.get('text') == r.get('text') and
                                                      set(f.get('sources', [])) == set(r.get('sources', []))
                                                      for r in retired)]
                parents = {}
                claim = 'ancestry'
                for edge in ee:
                    parents.setdefault(edge["child"], []).append(edge["parent"])
                done, active = set(), set()

                def visit(pid, active=active, done=done, parents=parents):
                    if pid in active:
                        raise ValueError("Цикл предковых связей")
                    if pid in done:
                        return
                    active.add(pid)
                    for parent in parents.get(pid, []):
                        visit(parent)
                    active.remove(pid)
                    done.add(pid)

                for pid in pp:
                    visit(pid)
                update = None
                if "update" in pack:
                    claim = 'update'
                    update = dict(pack["update"], author=author)
                    update["published_at"] = datetime.fromtimestamp(
                        path.stat().st_mtime, UTC
                    ).isoformat()
                    check_fact(update)
                    if (
                        update.get("person") not in pp
                        or not update.get("title")
                        or not update.get("date")
                    ):
                        raise ValueError("Обновление без человека / заголовка / даты")
                people.clear()
                people.update(pp)
                edges[:] = ee
                families[:] = ff
                sources.clear()
                sources.update(ss)
                owners.update({sid: path for sid in pack.get('sources', {})})
                unused_warnings.append(
                    (str(path.relative_to(project)), list(pack.get("sources", {})))
                )
                applied.append(
                    {"file": str(path.relative_to(project)), "author": author, "update": update}
                )
            except failures as exc:
                retry.append(path)
                errors.append({"file": str(path.relative_to(project)), "error": claim + ': ' + str(exc),
                               **({"waits": exc.waits, "author": _author(packages[path], path)}
                                  if isinstance(exc, Waiting) else {})})
        # Later packages may introduce referenced people or sources. Failed
        # packages remain atomic and are retried only while a pass adds data.
        if len(applied) == before:
            break
        pending = retry
    updates = sorted((x["update"] for x in applied if x["update"] is not None),
                     key=lambda x: ('' if x['date'] == 'unknown' else x['date'],
                                    tuple(x.get('sources', []))), reverse=True)
    research["updates"] = updates + research.get("updates", [])
    research["highlights"] = updates[:6] if updates else research.get("highlights", [])
    if updates:
        latest = max(datetime.fromisoformat(update["published_at"]) for update in updates)
        try:
            previous = datetime.fromisoformat(research.get("published_at", ""))
            if previous.tzinfo is None:
                previous = previous.replace(tzinfo=UTC)
            latest = max(latest, previous)
        except ValueError:
            pass
        research["published_at"] = latest.astimezone(UTC).isoformat()
    decisions = decisions or {}
    used = {
        sid
        for person in people.values()
        for fact in person.get("facts", [])
        for sid in fact.get("sources", [])
    }
    used.update(sid for edge in edges for sid in edge.get('sources', []))
    used.update(sid for union in families for sid in union.get('provenance', []))
    source_warnings = [
        {
            "file": filename,
            "sources": missing,
            "warning": "Источники объявлены, но ни один факт на них не ссылается",
        }
        for filename, source_ids in unused_warnings
        if (missing := sorted(set(source_ids) - used))
    ]
    warnings = source_warnings
    # A package waiting for a reference is quarantined, named and not applied; the check decides
    # whether it was applied before (an error) or waits for another wave's commit.
    quarantine = [e for e in errors if e.get("waits")]
    errors = [e for e in errors if not e.get("waits")]
    unread = [{"file": str(path.relative_to(project)), "key": key, "message": message}
              for path, pack in packages.items() for key, message in unread_keys(pack)]
    research["contributions"] = {"applied": applied, "errors": errors, "warnings": warnings,
                                 "quarantine": quarantine, "unread": unread}
    # The browser refreshes when this changes, including edits by any author.
    if revisions or errors or quarantine:
        research["revision"] = (
            research.get("revision", "")
            + ":"
            + hashlib.sha256(
                json.dumps([revisions, errors, quarantine], ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest()[:12]
        )
    for error in errors:
        research["updates"].insert(
            0,
            {
                "title": "Дополнение требует исправления",
                "text": error["file"] + " · " + error["error"],
                "date": "",
                "status": "conflict",
                "person": root_person,
                "sources": [],
            },
        )
