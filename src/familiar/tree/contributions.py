# START_MODULE_CONTRACT: MOD-TREE-CONTRIBUTIONS
# PURPOSE: Accept researcher findings and explicit revisions atomically with provenance and resolved evidence.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - invalid packages leave the graph unchanged [review: engine lead]
# - sources-only packages publish no reader update [review: engine lead]
# - duplicate source declarations name both owners and keep intake ownership explicit [review: engine lead]
# - replayed claims cannot reactivate a fact retained in retiredFacts [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (the shared family boundary contract)
# - docs/PRD.md#INSTANCE
# - MOD-TREE-BUILDER (configured evidence path)
# :END_MODULE_CONTRACT
"""Merge independent researchers' additive findings without shared-file writes."""

import copy
import hashlib
import json
import re
from datetime import UTC, datetime


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
    seen = set()
    while pending:
        before = len(applied)
        retry, errors = [], []
        for path in pending:
            try:
                pack = json.loads(path.read_text(encoding="utf-8-sig"))
                if path not in seen:
                    revisions.append(pack)
                    seen.add(path)
                from familiar.instance.gate import require_assertions
                require_assertions(pack)
                author = pack["author"]
                if (
                    not isinstance(author, str)
                    or author != path.parent.name
                    or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", author)
                ):
                    raise ValueError("Автор не совпадает с собственной папкой")
                if pack.get("schema") != 1:
                    raise ValueError("Ожидается schema: 1")
                pp, ee, ss = copy.deepcopy(people), copy.deepcopy(edges), copy.deepcopy(sources)
                ff = copy.deepcopy(families)
                for sid, source in pack.get("sources", {}).items():
                    if sid in ss and (ss[sid] != source or owners.get(sid) == evidence_path):
                        other = str(owners[sid].relative_to(project)) if owners.get(sid) else 'ранее объявленный источник'
                        hint = ('Объявлением владеет приём; в evidence нужна только ссылка на ID источника, '
                                'без повторной записи в sources.' if source.get('intake') or ss[sid].get('intake') else
                                'Оставьте одно объявление; в evidence используйте ссылку на ID источника.')
                        raise ValueError(f'Источник {sid} объявлен дважды: {other} и {path.relative_to(project)}. {hint}')
                    if source.get("local"):
                        target = (project / source["local"]).resolve()
                        if not target.is_relative_to(project.resolve()) or not target.is_file():
                            raise ValueError("Источник недоступен: " + sid)
                    ss[sid] = source

                def check_fact(fact, ss=ss):
                    if fact.get("status") not in (
                        "verified",
                        "hypothesis",
                        "conflict",
                        "export",
                    ) or not fact.get("text"):
                        raise ValueError("Утверждение без текста / статуса")
                    if not fact.get("sources") or any(s not in ss for s in fact["sources"]):
                        raise ValueError("Утверждение без разрешимых источников")

                for pid, person in pack.get("people", {}).items():
                    if pid in pp:
                        raise ValueError("Карточка уже существует; используйте facts: " + pid)
                    if not person.get("name"):
                        raise ValueError("Нет имени: " + pid)
                    pp[pid] = dict(
                        copy.deepcopy(person),
                        id=pid,
                        author=author,
                        origin=labels.get("contribution_origin", "Research record · ") + author,
                    )
                    for fact in pp[pid].get("facts", []):
                        check_fact(fact)
                        fact["author"] = author
                        fact["_contribution_file"] = str(path.relative_to(project))
                for pid, facts in pack.get("facts", {}).items():
                    if pid not in pp:
                        raise ValueError("Неизвестный человек: " + pid)
                    for fact in facts:
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
                    if pid not in pp:
                        raise ValueError("Подтверждение неизвестного человека: " + pid)
                    level = confirmation.get("level")
                    if level not in ("document", "family", "mention"):
                        raise ValueError("Неизвестное основание подтверждения: " + pid)
                    if not confirmation.get("sources") or any(
                        s not in ss for s in confirmation["sources"]
                    ):
                        raise ValueError("Подтверждение без разрешимых источников: " + pid)
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
                    pp[pid]["confirmation"] = copy.deepcopy(confirmation)
                pairs = {(e["child"], e["parent"]) for e in ee}
                for edge in pack.get("edges", []):
                    check_fact(edge)
                    pair = (edge["child"], edge["parent"])
                    if pair[0] not in pp or pair[1] not in pp:
                        raise ValueError("Связь с неизвестным человеком")
                    if pair in pairs:
                        raise ValueError("Связь уже существует; исправление обсудить на доске")
                    ee.append(dict(edge, author=author))
                    pairs.add(pair)
                from .revisions import apply
                apply(pack, pp, ee, ff, ss, check_fact, author, record_ids)
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
            except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
                retry.append(path)
                errors.append({"file": str(path.relative_to(project)), "error": str(exc)})
        # Later packages may introduce referenced people or sources. Failed
        # packages remain atomic and are retried only while a pass adds data.
        if len(applied) == before:
            break
        pending = retry
    updates = sorted((x["update"] for x in applied if x["update"] is not None), key=lambda x: x["published_at"], reverse=True)
    research["updates"] = updates + research.get("updates", [])
    research["highlights"] = updates[:6] if updates else research.get("highlights", [])
    if updates:
        latest = datetime.fromisoformat(updates[0]["published_at"])
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
    research["contributions"] = {"applied": applied, "errors": errors, "warnings": warnings}
    # The browser refreshes when this changes, including edits by any author.
    if revisions or errors:
        research["revision"] = (
            research.get("revision", "")
            + ":"
            + hashlib.sha256(
                json.dumps([revisions, errors], ensure_ascii=False, sort_keys=True).encode()
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
