# START_MODULE_CONTRACT: MOD-HOST-TEXT
# PURPOSE: Turn family requests, evidence and current case states into actionable prose for the host.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - requests ask an unprompted question before the family's current version [review: cold reviewer]
# - a next step changes with intake, answers, waiting and missing tests without writing inputs [review: cold reviewer]
# CHANGES_WITH:
# - MOD-INSTANCE-RESEARCH-FORMS (request and case storage vocabulary)
# - forms/request.json (optional host-facing request fields)
# - docs/gate.md (host explanation)
# :END_MODULE_CONTRACT
from datetime import date

from .host_language import HostData


def _letter(data, request):
    w = data.words
    question = data.find('versions', request.get('question'))
    subjects = data.subjects(question)
    paper = data.text(request.get('paper'), subjects)
    if not paper:
        return w('withheld')
    title = data.text(question.get('title'), subjects)
    witness = data.text(request.get('witness_question'), subjects) or (w('witness', question=title) if title else '')
    version = data.text(request.get('our_version'), subjects)
    why = data.text(request.get('why_this_paper'), subjects) or w('withheld' if request.get('why_this_paper') else 'purpose_unknown')
    is_self = request.get('addressee') == 'host'
    call_as = data.call_as(request)
    sender = data.personal_name(request.get('sender_name'))
    return '\n\n'.join(filter(None, [
        w('self_heading') if is_self else (w('greeting_named', name=call_as) if call_as else w('greeting')),
        '' if is_self else w('purpose'),
        witness,
        w('our_version', version=version) if version else '',
        w('request_self' if is_self else 'request', paper=paper, why=why),
        data.text(request.get('paper_description'), subjects),
        data.text(request.get('look_in'), subjects),
        data.text(request.get('photograph'), subjects),
        w('no_paper_self' if is_self else 'no_paper'),
        '' if is_self else (w('closing_named', name=sender) if sender else w('closing')),
    ]))


def _next(data, today):
    w = data.words
    hints = []
    for request in data.rows['questions']:
        case = data.find('cases', request.get('case'))
        question = data.find('versions', request.get('question'))
        subjects = data.subjects(question)
        paper = data.text(request.get('paper'), subjects)
        if request.get('paper') and not paper:
            hints.append(w('withheld'))
        if not paper or request.get('state') == 'closed':
            continue
        is_self = request.get('addressee') == 'host'
        who = data.call_as(request) or w('relative')
        if case.get('state') == 'bridged':
            papers = [data.find('records', rid) for rid in case.get('basis', [])]
            title = '; '.join(filter(None, (data.text(r.get('title'), data.subjects(r)) for r in papers if r)))
            hints.append(w('bridge', paper=title or paper))
            continue
        if case.get('state') == 'review':
            hints.append(w('case_review', question=data.text(question.get('title'), subjects) or w('question')))
            continue
        answer = data.find('answers', request.get('answer'))
        if not answer:
            answer = next((a for a in data.rows['answers'] if a.get('request') == request.get('id')), {})
        if answer or request.get('state') in {'answered', 'not-presented'}:
            if request.get('state') == 'not-presented':
                fallback = data.text(request.get('host_next'), subjects) or w('choose_test')
                hints.append(w('not_presented', paper=paper, next=fallback))
            else:
                result = data.text(answer.get('text'), subjects) or w('answer_private')
                if question.get('status') in {'accepted', 'closed', 'resolved'}:
                    decision = data.text(question.get('summary'), subjects) or w('withheld' if question.get('summary') else 'decision_unknown')
                else:
                    decision = w('answer_open')
                hints.append(w('answer', paper=paper, answer=result, decision=decision))
        elif request.get('state') == 'asked':
            try:
                days = (today - date.fromisoformat(request['asked_at'][:10])).days
                elapsed = w.days(max(0, days))
            except (KeyError, TypeError, ValueError):
                elapsed = w('date_unknown')
            hints.append(w('waiting_self', paper=paper, elapsed=elapsed) if is_self else
                         w('waiting', paper=paper, who=who, elapsed=elapsed))
        else:
            hints.append(w('draft_request_self', paper=paper) if is_self else
                         w('draft_request', paper=paper, who=who))
    for question in data.rows['versions']:
        if question.get('status') not in {'accepted', 'closed', 'resolved'} and not question.get('tests'):
            title = data.text(question.get('title'), data.subjects(question))
            if title:
                hints.insert(0, w('no_test', question=title))
        elif question.get('status') not in {'accepted', 'closed', 'resolved'} and not any(
                r.get('question') == question.get('id') and r.get('state') != 'closed' for r in data.rows['questions']):
            test = next((data.text((t.get('text') or t.get('test')), data.subjects(question)) for t in question.get('tests', []) if (t.get('text') or t.get('test'))), '')
            if test:
                title = data.text(question.get('title'), data.subjects(question))
                if title:
                    hints.append(w('run_test', question=title))
    if not hints and data.rows['versions']:
        hints.append(w('choose_story') if all(q.get('status') in {'accepted', 'closed', 'resolved'}
                                            for q in data.rows['versions']) else w('choose_test'))
    if not hints and not data.rows['versions']:
        if data.rows['records'] or any(m.get('items') for m in data.rows['memory']):
            hints.append(w('intake_ready'))
        elif data.people:
            hints.append(w('tree_ready'))
    return hints


def _summary(data, page_titles):
    w = data.words
    sections = []
    records = {r['id']: r for r in data.rows['records'] if 'id' in r}
    documented = []
    for record in records.values():
        title = data.text(record.get('title'))
        literal = '\n'.join(f'{data.text(key)}: {data.text(value)}' for key, value in record.get('fields', {}).items())
        if title:
            documented.append(title + ('\n' + literal if literal else ''))
            data.used_records.add(record['id'])
        else:
            documented.append(w('withheld'))
    for pid, person in data.people.items():
        for event in person.get('events', []):
            sources = event.get('provenance', event.get('sources', []))
            known = [records[s] for s in sources if s in records]
            if not known or event.get('open_question') or event.get('type') in {'address', 'residence'}:
                continue
            kind = event.get('type')
            if kind not in {'birth', 'death', 'baptism', 'marriage', 'emigration', 'immigration', 'occupation'}:
                continue
            detail = '; '.join(filter(None, (data.text(w.date(event.get(k)) if k == 'date' else event.get(k), [pid]) for k in ('date', 'place', 'value'))))
            source = '; '.join(filter(None, (data.text(r.get('title')) for r in known)))
            if detail and source:
                data.used_records.update(r['id'] for r in known)
                documented.append(w('documented', person=data.name(pid), event=w('event_' + kind), detail=detail, source=source))
    sections.append(w('papers') + '\n' + ('\n'.join(documented) or w('none')))
    permission_path = data.instance.path('research_permission')
    if permission_path.exists():
        import json
        permission = json.loads(permission_path.read_text(encoding='utf-8'))
        label = data.instance.language_pack_data.get(data.instance.source_language, {}).get('data', {}).get('table_intake', {}).get('words', {}).get('consent', 'Research permission')
        sections.append(label + ': ' + '; '.join(filter(None, (data.text(str(permission.get(k, ''))) for k in ('authorized_by', 'authorized_to', 'date', 'conveyed_via')))))
    firm, hearsay = {}, {}
    for memory in data.rows['memory']:
        for item in memory.get('items', []):
            subjects = data.subjects(item) | ({item['person']} if item.get('person') else set())
            text = data.text(item.get('display_text') or item.get('text'), subjects)
            if item.get('person'):
                text = data.name(item['person']) + ': ' + (text or w('withheld'))
            if item.get('text'):
                bucket = firm if item.get('strength') == 'firm' else hearsay
                bucket.setdefault(item.get('person', ''), []).append(text or w('withheld'))
    sections += [w('firm_memory') + '\n' + ('\n\n'.join('\n'.join(lines) for lines in firm.values()) or w('none')),
                 w('hearsay') + '\n' + ('\n\n'.join('\n'.join(lines) for lines in hearsay.values()) or w('none'))]
    questions = []
    for question in data.rows['versions']:
        if question.get('status') in {'accepted', 'closed', 'resolved'}:
            continue
        title = data.text(question.get('title'), data.subjects(question))
        if not title:
            questions.append(w('withheld'))
            continue
        request = next((r for r in data.rows['questions'] if r.get('question') == question['id']), {})
        paper = data.text(request.get('paper'), data.subjects(question))
        questions.append(w('open_question', question=title, paper=paper or w('test_missing')))
    sections.append(w('questions') + '\n' + ('\n'.join(questions) or w('none')))
    sections.append(w('stories') + '\n' + ('\n'.join(page_titles) or w('none')))
    return '\n\n'.join(sections)


def _build(instance, view, selection=None, feed=None, today=None):
    from .host_pages import _pages
    data = HostData(instance)
    w = data.words
    review = None
    if view == 'confirmation':
        text = w('confirmation')
    elif view == 'requests':
        requests = [r for r in data.rows['questions'] if not selection or r.get('id') == selection]
        if selection and not requests:
            raise ValueError('No such family request.')
        text = '\n\n'.join(_letter(data, request) for request in requests) or w('no_requests')
    elif view == 'pages':
        text, review = _pages(data, feed, selection)
    elif view in {'next', 'summary'}:
        hints = _next(data, today or date.today())
        page_text, _ = _pages(data, feed, titles_only=True)
        if view == 'summary':
            text = _summary(data, page_text)
        else:
            text = '\n\n'.join(' '.join(line.split()) for line in (hints + page_text)[:2]) or w('start')
    else:
        raise ValueError('Unknown host text view.')
    people = sorted(data.used_people)
    text = w('working_view') + '\n\n' + text
    return {'text': data.finish(text), 'people': people}, review, data.uses(view)
