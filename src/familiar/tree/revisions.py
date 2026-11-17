# START_MODULE_CONTRACT: MOD-TREE-REVISIONS
# PURPOSE: Apply explicit documentary decisions to derived relationships, facts and events without rewriting their inputs.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - decisions name an existing target and retain prior claims with their retirement reason [review: engine lead]
# - documentary relationship acceptance does not promote another relationship or family member [review: engine lead]
# CHANGES_WITH:
# - MOD-TREE-CONTRIBUTIONS (atomic package application)
# - MOD-READER-GRAPH (finalized events reach the reader)
# :END_MODULE_CONTRACT
import copy


def apply(pack, people, edges, families, sources, check_fact, author, record_ids):
    def person(pid):
        if pid not in people:
            raise ValueError('Unknown revision person: ' + pid)
        return people[pid]

    def grounds(row, key='sources'):
        refs = row.get(key)
        if not isinstance(refs, list) or not refs or any(s not in sources for s in refs):
            raise ValueError('Revision needs resolved sources')
        if not any(sources[s].get('record') in record_ids and sources[s].get('kind') in
                   {'archive-record', 'home-paper', 'record', 'document'} for s in refs):
            raise ValueError('Documentary revision needs a record source')
        return refs

    for row in pack.get('relationship_decisions', []):
        check_fact(row)
        refs = grounds(row)
        if bool(row.get('family')) == bool(row.get('parent') or row.get('child')):
            raise ValueError('Select a family union OR a parent/child pair')
        if not row.get('basis') or not row.get('previous_status'):
            raise ValueError('Relationship decision needs basis and previous_status')
        if row.get('family'):
            targets = [f for f in families if f.get('id') == row['family']]
        else:
            person(row['parent']); person(row['child'])
            targets = [e for e in edges if (e.get('parent'), e.get('child')) ==
                       (row['parent'], row['child'])]
        if len(targets) != 1:
            raise ValueError('Relationship decision must select exactly one existing link')
        target = targets[0]
        if target.get('status', 'export') != row['previous_status']:
            raise ValueError('Relationship previous_status changed; inspect the earlier decision')
        target.setdefault('history', []).append({k: copy.deepcopy(v) for k, v in target.items() if k != 'history'})
        target.update(status=row['status'], sources=refs, basis=row['basis'],
                      text=row['text'], author=author, derived=False)
        target.update({key: copy.deepcopy(row[key]) for key in ('confidence', 'weight') if key in row})
        if row.get('family'):
            target['provenance'] = refs

    for row in pack.get('fact_replacements', []):
        p = person(row['person'])
        prior = row['prior']
        matches = [f for f in p.get('facts', []) if f.get('text') == prior.get('text')
                   and set(f.get('sources', [])) == set(prior.get('sources', []))]
        if len(matches) != 1 or not row.get('reason'):
            raise ValueError('Fact replacement needs exactly one prior text/source set and a reason')
        fact = row['fact']
        check_fact(fact); grounds(fact)
        p.setdefault('retiredFacts', []).append(dict(matches[0], retiredBecause=row['reason']))
        p['facts'].remove(matches[0])
        p['facts'].append(dict(copy.deepcopy(fact), author=author))

    for pid, events in pack.get('events', {}).items():
        p = person(pid)
        for event in events:
            grounds(event, 'provenance')
            if not event.get('type') or not event.get('date'):
                raise ValueError('Revision event needs type and literal date')
            event = dict(copy.deepcopy(event), author=author, status='verified')
            event.setdefault('tag', {'birth': 'BIRT', 'death': 'DEAT', 'marriage': 'MARR'}.get(event['type'], event['type'].upper()))
            if event not in p.setdefault('events', []):
                p['events'].insert(0, event)  # The newly read date leads older imported estimates.
                p.setdefault('facts', []).append({'label': 'events', 'eventType': event['type'],
                    'text': ' · '.join(str(event[k]) for k in ('date', 'place', 'note', 'cause') if event.get(k)),
                    'status': 'verified', 'sources': event['provenance'], 'author': author})

    for pid, media in pack.get('media', {}).items():
        p = person(pid)
        for image in media:
            if image.get('sourceSid', image.get('sid')) not in sources or not image.get('asset') or not image.get('title'):
                raise ValueError('Card document needs a source, asset and caption')
            if image not in p.setdefault('media', []):
                p['media'].append(copy.deepcopy(image))
