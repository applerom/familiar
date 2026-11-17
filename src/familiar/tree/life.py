# START_MODULE_CONTRACT: MOD-TREE-LIFE
# PURPOSE: Assess life status consistently from dated generations and reversible family decisions.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - life declarations for merged people follow their active successors [review: engine lead]
# - unknown status remains protected and revoking a death decision restores protection [review: engine lead]
# - direct verified/export parent links bound either endpoint regardless of sex; hypotheses do not [review: engine lead]
# - only adopted canonical records bound birth; collector drafts and hypothetical attributions never do [review: engine lead]
# - generation bounds are estimates, never invented birth events [review: engine lead]
# CHANGES_WITH:
# - MOD-RULES-SETTINGS-DATA (privacy.living_years)
# - MOD-INSTANCE-VALIDATION (privacy.life_decisions)
# - MOD-CHECKS-ENGINE (life_status)
# - MOD-PUBLICATION (reader flags reflect the effective assessment)
# :END_MODULE_CONTRACT
import re
from datetime import date


def _years(value):
    return [int(y) for y in re.findall(r'\b(?:1\d{3}|20\d{2})\b', str(value))]


def _birth_bounds(value):
    years = _years(value)
    if not years:
        return None
    text = str(value).casefold()
    lower, upper = min(years), max(years)
    if re.search(r'\b(aft|after|после)\b|>', text):
        upper = date.today().year
    elif re.search(r'\b(bef|before|до)\b|<', text):
        lower = 0
    elif re.search(r'\b(abt|about|circa|около|ок)\b|[~≈?]', text):
        lower, upper = lower - 5, upper + 5
    return lower, upper


def _record_bounds(instance, graph):
    """Use attributed roles only; prose, name matches and document metadata are not identity."""
    from familiar.checks.engine import load

    bounds, deaths = {}, set()
    aliases = graph.get('identityAliases', {})
    adult = {'father', 'mother', 'parent', 'godfather', 'godmother', 'godparent',
             'spouse', 'husband', 'wife', 'bride', 'groom'}
    child = {'child', 'baptized', 'baptised', 'infant', 'subject', 'named'}

    def add(pid, role, when, status=None):
        if status in {'hypothesis', 'possible', 'probable', 'rejected'}:
            return
        pid = aliases.get(pid, pid)
        interval = _birth_bounds(when)
        if pid not in graph['people'] or not interval:
            return
        if role == 'deceased':
            deaths.add(pid)
        elif role not in adult | child:
            return
        upper = interval[1] - (12 if role in adult else 0)
        bounds.setdefault(pid, []).append(upper)

    for pid, person in graph['people'].items():
        for event in person.get('events', []):
            kind = event.get('type')
            if kind in {'birth', 'death'}:
                continue  # Existing birth/death semantics remain authoritative.
            add(pid, event.get('role', {'baptism': 'baptized', 'marriage': 'spouse'}.get(kind, '')),
                event.get('date', ''), event.get('status'))
    from familiar.instance.display import research_inputs
    for path in sorted(research_inputs(instance)):
        if not path.is_relative_to(instance.path('records')):
            continue
        record = load(path, {})
        if record.get('status') in {'hypothesis', 'rejected'}:
            continue
        # A subject on an event is dated by that event. Record-level subjects may
        # use a record date, or its single event date, never a fetching/book date.
        events = record.get('events', [])
        when = record.get('date', '')
        if not when and len(events) == 1 and events[0].get('status') != 'hypothesis':
            when = events[0].get('date', '')
        for node, dated in [(record, when), *((e, e.get('date', '')) for e in events)]:
            for subject in node.get('subjects', []):
                if isinstance(subject, dict):
                    add(subject.get('person'), subject.get('role'), dated, subject.get('status', subject.get('confidence')))
        primary = record.get('person', {})
        match = record.get('match', {})
        pid = primary.get('id') if isinstance(primary, dict) else primary
        if not pid and match.get('confidence') == 'same':
            pid = match.get('tree_id')
        if match.get('confidence') in {'hypothesis', 'possible', 'probable', 'unknown'}:
            pid = None
        for event in events:
            role = {'birth': 'child', 'baptism': 'baptized', 'marriage': 'spouse', 'death': 'deceased'}.get(event.get('type'))
            add(pid, role, event.get('date', ''), event.get('status'))
    # Disagreeing records retain the youngest plausible bound.
    return {pid: (0, max(values), 'record') for pid, values in bounds.items()}, deaths


def _assess(instance, graph):
    from familiar.checks.engine import load
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root

    privacy = load(instance.path('privacy'), {})
    if not hasattr(instance, '_life_horizon'):
        instance._life_horizon = Registry(method_root() / 'rules', instance).resolve_setting('privacy.living_years').value
    horizon = instance._life_horizon
    cutoff = date.today().year - horizon
    people = graph['people']
    bounds = {}
    for pid, person in people.items():
        intervals = [_birth_bounds(e.get('date', '')) for e in person.get('events', []) if e.get('type') == 'birth']
        intervals = [b for b in intervals if b]
        if intervals:
            bounds[pid] = (min(b[0] for b in intervals), max(b[1] for b in intervals), 'birth')
    # Only direct dated relatives: no repeated propagation through guessed generations.
    direct = dict(bounds)
    related = {}
    parent_links = {}
    for edge in graph.get('edges', []):
        if edge.get('status') not in {'verified', 'export'}:
            continue
        if edge.get('type') == 'parent':
            parent, child = edge.get('from'), edge.get('to')
        else:
            parent, child = edge.get('parent'), edge.get('child')
        if parent in people and child in people:
            parent_links.setdefault(parent, []).append((child, -120, 0))
            parent_links.setdefault(child, []).append((parent, 0, 120))
    for family in graph.get('families', []):
        for pid in (family.get('husband'), family.get('wife'), *family.get('children', [])):
            related.setdefault(pid, []).append(family)
    for pid in people.keys() - direct.keys():
        estimates = [(direct[relative][0] + lower, direct[relative][1] + upper)
                     for relative, lower, upper in parent_links.get(pid, []) if relative in direct]
        for family in related.get(pid, []):
            parents = [p for p in (family.get('husband'), family.get('wife')) if p]
            children = family.get('children', [])
            if pid in parents:
                estimates += [(direct[c][0] - 120, direct[c][1]) for c in children if c in direct]
                estimates += [(direct[p][0] - 100, direct[p][1] + 100) for p in parents if p != pid and p in direct]
            if pid in children:
                estimates += [(direct[p][0], direct[p][1] + 120) for p in parents if p in direct]
        if estimates:
            # Union rather than intersection: disagreement must not make someone older.
            bounds[pid] = (min(b[0] for b in estimates), max(b[1] for b in estimates), 'generation')
    recorded, deaths = _record_bounds(instance, graph)
    for pid, interval in recorded.items():
        if pid not in bounds:
            bounds[pid] = interval
        else:
            # Preserve conflicting birth/generation evidence conservatively.
            old = bounds[pid]
            bounds[pid] = (old[0], max(old[1], interval[1]), old[2])
    decisions = privacy.get('life_decisions', [])
    aliases = graph.get('identityAliases', {})
    declared_living = {aliases.get(p if isinstance(p, str) else p['id'], p if isinstance(p, str) else p['id'])
                       for p in privacy.get('living', [])}
    for pid, person in people.items():
        decision = next((d for d in reversed(decisions) if aliases.get(d['person'], d['person']) == pid and not d.get('revoked')), None)
        if pid in declared_living:
            status, basis = 'living', 'explicit living privacy declaration'
        elif decision:
            status, basis = decision['status'], decision['basis']
        elif pid in deaths:
            status, basis = 'dead', 'attributed dated deceased record role'
        elif pid in bounds and bounds[pid][1] < cutoff:
            status, basis = 'dead', f'{bounds[pid][2]} upper bound {bounds[pid][1]} before {cutoff} ({horizon} years)'
        elif person.get('living') is False and person.get('life_origin') != 'gedcom':
            status, basis = 'dead', 'recorded death classification'
        elif any(e.get('type') == 'death' and e.get('status') != 'hypothesis' for e in person.get('events', [])):
            status, basis = 'dead', 'attributed death event'
        elif any(e.get('type') == 'death' and e.get('status') == 'hypothesis' for e in person.get('events', [])):
            status, basis = 'unknown', 'unverified imported death; no established death decision'
        elif pid in bounds and bounds[pid][2] == 'birth':
            status, basis = 'living', 'birth within living horizon; no established death'
        else:
            status, basis = 'unknown', 'birth unknown; generation does not establish age beyond horizon'
        person['life_assessment'] = {'status': status, 'basis': basis,
                                     **({'birth_bounds': list(bounds[pid][:2])} if pid in bounds else {})}
    return graph
