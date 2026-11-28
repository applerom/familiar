# START_MODULE_CONTRACT: MOD-TREE-LIFE
# PURPOSE: Assess life status consistently from attributed events and reversible family decisions.
# PRD_REF: docs/PRD.md#TRUST
# INVARIANTS:
# - tentative relatives cannot use the shorter home age horizon [review: engine lead]
# - merges retain declarations on either card; unresolved status uses the ordinary age horizons [test: tests/gate/test_data_guarantees.py::test_f3_public_name_and_kinship_and_private_address_exclusion]
# - a death before the person's own dated birth remains a protected conflict [review: engine lead]
# - life declarations for merged people follow their active successors [review: engine lead]
# - unknown status remains protected and revoking a death decision restores protection [review: engine lead]
# - card estimates, proposed events and identity guesses cannot establish death [review: engine lead]
# - only adopted canonical records bound birth; collector drafts and hypothetical attributions never do [review: engine lead]
# - a paper's date applies only to its written participants; a citation does not establish participation [test: tests/gate/test_data_guarantees.py::test_only_recorded_events_open_a_card]
# - the family age horizon applies to inferred status; explicit living or unknown decisions and life conflicts stay protected [review: engine lead]
# - an unscoped death decision keeps its family view and cannot itself open a public card [test: tests/gate/test_data_guarantees.py::test_life_decision_scope]
# CHANGES_WITH:
# - MOD-RULES-SETTINGS-DATA (privacy.living_years and privacy.family_years)
# - MOD-INSTANCE-VALIDATION (privacy.life_decisions)
# - MOD-CHECKS-ENGINE (life_status)
# - MOD-PUBLICATION (reader flags reflect the effective assessment)
# :END_MODULE_CONTRACT
import copy
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


def explicit_alive(person):
    return (person.get('living') is True and person.get('life_origin') != 'gedcom'
            and not str(person.get('living_basis', '')).casefold().startswith('precaution:'))


def decision_scope(decision):
    # Legacy death decisions can be age judgements. Only the author knows the
    # intended scope of their written basis. Protective declarations travel.
    if decision['status'] != 'dead':
        return 'everywhere'
    return 'everywhere' if decision.get('scope') == 'everywhere' else 'home'


def attributed_link(row):
    """The same relationship can own a citation and carry a recorded life bound."""
    status = row.get('status', 'export')
    if status not in {'export', 'verified', 'hypothesis', 'possible', 'probable', 'accepted', 'confirmed'} or row.get('identity'):
        return False
    weight = row.get('weight')
    if weight is None:
        return status in {'export', 'verified', 'accepted', 'confirmed'} and not row.get('derived')
    return type(weight) in (float, int) and .30 <= weight <= 1


UNCERTAIN = {'hypothesis', 'possible', 'probable', 'unknown', 'rejected', 'candidate', 'hearsay',
             'unverified', 'conflict', 'disproved', 'declined', 'proposed', 'draft', 'inferred', 'estimated'}


def recorded(row):
    if re.match(r'\s*(?:EST|CAL|estimated|calculated)\b', str(row.get('date', '')), re.I):
        return False
    weight = row.get('weight')
    if weight is not None and not (type(weight) in (float, int) and .5 <= weight <= 1):
        return False
    return (not any(row.get(k) in UNCERTAIN for k in ('status', 'confidence', 'testimony'))
            and not any(row.get(key) for key in ('derived', 'identity', 'amendment', 'inferred', 'estimated', 'guess'))
            and not (row.get('approximate') and row.get('status') not in {'verified', 'export', 'reported'}))


def life_link(row, family_display):
    # An unweighted adopted family link can still date the older generations
    # at home. A weighted proposal needs established evidence of its own.
    return attributed_link(row) and (recorded(row) or family_display and row.get('weight') is None)


def relation_people(row):
    members = {row[k] for k in ('parent', 'child', 'from', 'to', 'husband', 'wife') if row.get(k)}
    if not (row.get('history') and row.get('husband') and row.get('wife')):
        members.update(row.get('children', ()))
    return members


def _record_bounds(instance, graph, *, family_display=False):
    """Use attributed roles only; prose, name matches and document metadata are not identity."""
    from familiar.checks.engine import load
    from familiar.instance.display import research_inputs
    from familiar.instance.gate import shared
    from familiar.instance.subjects import feedback_record, recorded_match

    bounds, deaths, births, child_dates = {}, {}, {}, {}
    aliases = graph.get('identityAliases', {})
    adult = {'father', 'mother', 'parent', 'godfather', 'godmother', 'godparent', 'adult-witness',
             'spouse', 'husband', 'wife', 'bride', 'groom'}
    child = {'child', 'son', 'daughter', 'baptized', 'baptised', 'infant'}
    present = {'subject', 'named', 'signer', 'witness', 'participant', 'household-member'}

    family_only = {}

    def add(pid, role, when, *, event_type=None, direct_event=False, home_only=False):
        pid = aliases.get(pid, pid)
        interval = _birth_bounds(when)
        if pid not in graph['people'] or not interval:
            return
        if role == 'deceased':
            deaths.setdefault(pid, []).append(interval)
        elif role not in adult | child | present:
            return
        upper = interval[1] - (12 if role in adult else 0)
        (family_only if home_only else bounds).setdefault(pid, []).append(upper)
        if event_type == 'birth' and role in child:
            births.setdefault(pid, []).append(when)
        if direct_event or (event_type == 'baptism' and role in child):
            child_dates[pid] = min(child_dates.get(pid, upper), upper)

    for pid, person in graph['people'].items():
        for event in person.get('events', []):
            kind = event.get('type')
            if kind == 'birth' or not recorded(event):
                continue
            role = event.get('role', {'baptism': 'baptized', 'marriage': 'spouse', 'residence': 'subject',
                                      'occupation': 'subject', 'service': 'participant', 'death': 'named'}.get(kind, ''))
            add(pid, role, event.get('date', ''), direct_event=True)
    for path in sorted(research_inputs(instance)):
        if not path.is_relative_to(instance.path('records')):
            continue
        record = shared(instance, ('life-record', path), lambda: load(path, {}))
        if not recorded(record) or feedback_record(record) or record.get('record_role') in {'analysis', 'catalogue'}:
            continue
        # A subject on an event is dated by that event. Record-level subjects may
        # use a record date, or its single event date, never a fetching/book date.
        events = record.get('events', [])
        when = record.get('date', '')
        match = record.get('match') or {}
        single = events[0] if len(events) == 1 and recorded(events[0]) else {}
        roles = {'birth': child | {'father', 'mother', 'parent'},
                 'baptism': child | {'father', 'mother', 'parent', 'godfather', 'godmother', 'godparent'},
                 'marriage': {'spouse', 'husband', 'wife', 'bride', 'groom'}, 'death': {'deceased'}}
        for node, dated in [(record, when), *((e, e.get('date', '')) for e in events if recorded(e))]:
            for subject in node.get('subjects', []):
                if isinstance(subject, str):
                    add(subject, 'named', record.get('date') if node is record else dated)
                elif isinstance(subject, dict) and recorded(subject):
                    role = subject.get('role', 'named')
                    if role == 'witness' and subject.get('adult') is True:
                        role = 'adult-witness'
                    own_event = node is record and not dated and (
                        role in roles.get(single.get('type'), ()) or role == 'adult-witness')
                    add(subject.get('person'), role, dated or (single.get('date') if own_event else None),
                        event_type=single.get('type') if own_event else node.get('type'))
        for relative in record.get('relatives', []):
            if isinstance(relative, dict) and recorded(relative):
                role = relative.get('role', 'named')
                add(relative.get('id'), role if role in adult | child | present else 'named', when)
        for subjects in record.get('field_subjects', {}).values():
            for pid in subjects:
                add(pid, 'named', when)
        listed = record.get('people', {})
        for pid in listed.values() if isinstance(listed, dict) else listed or []:
            if isinstance(pid, str):
                add(pid, 'named', record.get('date'))
        primary = record.get('person', {})
        pid = primary.get('id') if isinstance(primary, dict) else primary
        if not pid:
            pid = recorded_match(record)
        if not recorded(match) or isinstance(primary, dict) and not recorded(primary):
            pid = None
        add(pid, 'named', record.get('date', ''))
        named_roles = {s.get('role') for s in record.get('subjects', []) if isinstance(s, dict) and s.get('person') == pid}
        for event in events:
            if not event.get('subjects') and recorded(event):
                role = {'birth': 'child', 'baptism': 'baptized', 'marriage': 'spouse', 'death': 'deceased'}.get(event.get('type'))
                if not named_roles or role in named_roles or role == 'child' and named_roles & child:
                    add(pid, role, event.get('date', ''), event_type=event.get('type'))
    for family in graph.get('families', []):
        if attributed_link(family) and (family_display or recorded(family)):
            for event in family.get('events', []):
                if event.get('type') == 'marriage' and recorded(event):
                    for partner in ('husband', 'wife'):
                        add(family.get(partner), 'spouse', event.get('date', ''), direct_event=True,
                            home_only=not recorded(family))
    # Each independently dated appearance bounds this person's birth.
    return ({pid: (0, min(values), 'record') for pid, values in bounds.items()}, deaths, births, child_dates,
            {pid: min(values) for pid, values in family_only.items()})


def _participants(person):
    """Original participants, including aliases that already had their own merges."""
    history = person.get('identityHistory', [])
    if not history:
        return [person]
    return _participants(history[0]['priorCanonical']) + [
        p for step in history for p in _participants(step['priorAlias'])]


def family_cards(instance, graph):
    """The people with the dates their cards show."""
    from familiar.instance.edition import apply
    from familiar.reader.graph import card_dates
    cards = copy.deepcopy(graph)
    card_dates(cards['people'], graph['people'])
    return apply(instance, cards)


def _birth_reaches_horizon(raw, today, horizon, *, strict=False):
    bounds = _birth_bounds(raw)
    if not bounds:
        return None
    year = bounds[1]
    if year != today.year - horizon:
        return year < today.year - horizon
    text = str(raw)
    try:
        born = date.fromisoformat(text)
    except ValueError:
        parts = text.upper().split()
        months = 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split()
        if len(parts) != 3 or parts[1] not in months:
            return not strict  # The best available precision is the year.
        try:
            born = date(int(parts[2]), months.index(parts[1]) + 1, int(parts[0]))
        except ValueError:
            return not strict
    birthday, now = (born.month, born.day), (today.month, today.day)
    return birthday < now if strict else birthday <= now


def _assess(instance, graph, *, family_display=False):
    from familiar.checks.engine import load
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root

    privacy = load(instance.path('privacy'), {})
    registry = Registry(method_root() / 'rules', instance)
    if not hasattr(instance, '_life_horizon'):
        instance._life_horizon = registry.resolve_setting('privacy.living_years').value
    horizon = instance._life_horizon
    today = date.today()
    cutoff = today.year - horizon
    family_horizon = registry.resolve_setting('privacy.family_years').value if family_display else None
    people = graph['people']
    record_bounds, deaths, birth_readings, child_dates, home_bounds = _record_bounds(
        instance, graph, family_display=family_display)
    bounds = {}
    for pid, person in people.items():
        dates = birth_readings.setdefault(pid, [])
        dates.extend(e.get('date', '') for e in person.get('events', []) if e.get('type') == 'birth' and recorded(e))
        intervals = [interval for value in dates if (interval := _birth_bounds(value))]
        if intervals:
            bounds[pid] = (min(b[0] for b in intervals), max(b[1] for b in intervals), 'birth')
    births = {pid: value[1] for pid, value in bounds.items()}
    # A recorded birth wins over another event or a baptism. General paper
    # dates belong only to the paper's participants.
    child_dates.update(births)

    def parent_bound(parent, child, link):
        if parent in people and child in child_dates:
            upper = child_dates[child] - 12
            # A later recorded birth of the parent contradicts the link.
            if births.get(parent, 0) > upper:
                return
            if not recorded(link):
                home_bounds[parent] = min(home_bounds.get(parent, upper), upper)
            elif parent not in record_bounds or upper < record_bounds[parent][1]:
                record_bounds[parent] = (0, upper, 'child')

    for edge in graph.get('edges', []):
        if life_link(edge, family_display):
            parent_bound(edge.get('parent'), edge.get('child'), edge)
    for family in graph.get('families', []):
        if life_link(family, family_display):
            for child in relation_people(family).intersection(family.get('children', [])):
                parent_bound(family.get('husband'), child, family)
                parent_bound(family.get('wife'), child, family)
    for pid, interval in record_bounds.items():
        if pid not in bounds:
            bounds[pid] = interval
    decisions = privacy.get('life_decisions', [])
    aliases = graph.get('identityAliases', {})
    declared_living = {aliases.get(p if isinstance(p, str) else p['id'], p if isinstance(p, str) else p['id'])
                       for p in privacy.get('living', [])}
    active_decisions = {}
    for d in decisions:
        if not d.get('revoked') and (family_display or decision_scope(d) == 'everywhere'):
            active_decisions[d['person']] = d
    for pid, person in people.items():
        birth_only = False
        applicable = [d for key, d in active_decisions.items() if aliases.get(key, key) == pid]
        decision = next((d for d in applicable if d['status'] == 'living'), None)
        decision = decision or next((d for d in applicable if d['status'] == 'unknown'), None) or active_decisions.get(pid)
        participants = _participants(person)
        explicit_living = (pid in declared_living or (decision and decision['status'] == 'living') or
                           any(explicit_alive(p) for p in participants))
        scope = 'everywhere'
        if explicit_living:
            status, basis = 'living', 'explicit living privacy declaration'
        elif decision:
            status, basis = decision['status'], decision['basis']
            scope = decision_scope(decision)
        elif pid in deaths:
            status, basis = 'dead', 'attributed dated deceased record role'
        elif person.get('living') is False and person.get('life_origin') != 'gedcom':
            status, basis = 'dead', 'recorded death classification'
        elif any(e.get('type') == 'death' and recorded(e) for e in person.get('events', [])):
            status, basis = 'dead', 'attributed death event'
        elif any(e.get('type') == 'death' for e in person.get('events', [])):
            status, basis = 'unknown', 'unverified imported death; no established death decision'
        elif pid in bounds and bounds[pid][2] == 'birth':
            status, basis = 'living', 'birth within living horizon; no established death'
            birth_only = True
        else:
            status, basis = 'unknown', 'no attributed event establishes age beyond horizon'
        conflicts = []
        death_dates = [_birth_bounds(e.get('date', '')) for e in person.get('events', [])
                       if e.get('type') == 'death' and recorded(e)] + deaths.get(pid, [])
        birth_dates = birth_readings[pid]
        birth_intervals = [_birth_bounds(value) for value in birth_dates]
        early_death = any(d and b and d[1] < b[0] for d in death_dates for b in birth_intervals)
        merged_aliases = [alias for alias, target in aliases.items() if target == pid]
        merged = bool(merged_aliases)
        protected = [p['id'] for p in participants if p.get('life_assessment', {}).get('status') != 'dead'] if merged else []
        if merged and not person.get('identityHistory'):
            protected = [pid, *merged_aliases]  # Imported aliases have no independent life evidence.
        # A death decision on an absorbed card is evidence for that participant,
        # not a decision about everyone. The canonical id names a merged decision.
        resolved = decision and decision['person'] == pid and decision['status'] == 'dead'
        if early_death or protected:
            if not resolved:
                status, basis = 'unknown', 'conflicting life evidence; protection retained'
                if explicit_living:
                    status = 'living'
            owners = []
            for participant in participants:
                evidence = [str(e.get('date', 'undated')) + ' ' + str(e.get('provenance', []))
                            for e in participant.get('events', []) if e.get('type') == 'death']
                assessment = participant.get('life_assessment', {})
                owners.append(participant['id'] + ': ' + assessment.get('basis', 'unassessed') +
                              '; own death events: ' + (', '.join(evidence) or 'none'))
            # Even an explicit resolution must not silently hide contradictory dates.
            if not resolved or early_death:
                conflicts.append(f"Life conflict for {pid} (merged with {', '.join(merged_aliases) or 'none'}): "
                    f"{'; '.join(owners)}; protected participants: {', '.join(protected) or 'none'}; "
                    f"death before own birth: {early_death}. "
                    f"Record privacy.life_decisions for canonical {pid} with a death basis, or undo the merge; correct conflicting dates.")
        if not (early_death or explicit_living or decision) and (status == 'unknown' or birth_only) and pid in bounds:
            upper = bounds[pid][1]
            if upper < cutoff or (upper == cutoff and birth_dates and
                                  all(_birth_reaches_horizon(value, today, horizon, strict=True) for value in birth_dates)):
                status, basis = 'dead', f'{bounds[pid][2]} upper bound {upper} beyond {horizon}-year horizon'
        if family_display and not (decision or explicit_living or early_death) and status != 'dead' and (status == 'unknown' or birth_only):
            dated = [reached for value in birth_dates
                     if (reached := _birth_reaches_horizon(value, today, family_horizon)) is not None]
            allowed = bounds.get(pid, (0, today.year, None))[1]
            # Tentative links may bound an older generation at home, but
            # cannot open the extra years allowed by the family horizon.
            if pid not in births and (home := home_bounds.get(pid, today.year)) <= cutoff:
                allowed = min(allowed, home)
            if all(dated) and allowed <= today.year - family_horizon:
                status, basis = 'dead', f'beyond family display horizon ({family_horizon} years)'
                scope = 'home'
        if status == 'dead' and not early_death:
            conflicts = []
        person['life_assessment'] = {'status': status, 'basis': basis, 'scope': scope,
                                     **({'conflicts': conflicts} if conflicts else {}),
                                     **({'birth_bounds': list(bounds[pid][:2])} if pid in bounds else {})}
    return graph
