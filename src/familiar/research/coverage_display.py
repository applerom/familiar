# START_MODULE_CONTRACT: MOD-RESEARCH-COVERAGE-DISPLAY
# PURPOSE: Turn the search coverage matrix into the "where it was looked for" block of one person in the host-private reader.
# PRD_REF: docs/PRD.md#SOURCE-SEARCH
# INVARIANTS:
# - read-only: only the journal and the tree are read, nothing is written and no step is added for the researcher [review: engine lead]
# - the block exists only in the host-private reader graph; the public projection never carries it [review: engine lead]
# - without a journal or on any failure the reader is built without the block, never with a build error [review: engine lead]
# CHANGES_WITH:
# - MOD-RESEARCH-COVERAGE (the matrix it summarises)
# - MOD-PUBLICATION (declared coverage surface, host-private only)
# - MOD-FAMILY-GATE (attaches the block to the host-private reader graph from the host's own instance, since the display snapshot holds no journals)
# :END_MODULE_CONTRACT
from .coverage import cell_view, collect, recheck, title

SHOWN = 12


def person_blocks(instance):
    """{person id: block} for the people the journal or an open version names; {} when there is nothing to show."""
    data = collect(instance)
    if not data['sources']:
        return {}
    queue = {}
    for item in recheck(data):
        if item['reasons'] != ['not-searched']:
            queue[item['person']] = queue.get(item['person'], 0) + 1
    reference = lambda sid: data['resolver'].catalog.sources.get(sid, {}).get('kind') == 'reference'  # noqa: E731
    blocks = {}
    for pid in data['focus']:
        seen = []
        for sid in data['sources']:
            cell = data['cells'].get((pid, sid))
            if not cell:
                continue
            view = cell_view(data, pid, sid)
            seen.append({'id': sid, 'title': title(data, sid), 'outcome': view['outcome'], 'last': cell['last'] or '',
                         'strength': cell['strength'], 'forms': list(cell['forms'])[:4],
                         'identified': view['identified'], 'recordRead': bool(view['records']),
                         'surnameSearch': 'surname' in view['scope'], 'planComplete': view['plan_complete'],
                         'placeSearch': 'place' in view['scope'],
                         'identity': view['identity'], 'availability': view['availability'],
                         'latestRefusal': view['latest_refusal'],
                         'scriptStatus': view['script_status'], 'queryIssues': view['query_issues'],
                         'missingForms': view['missing_forms'][:4], 'missingMore': max(0, len(view['missing_forms']) - 4)})
        seen.sort(key=lambda s: s['last'], reverse=True)
        never = [{'id': sid, 'title': title(data, sid)} for sid in sorted(data['sources'])
                 if not sid.startswith('~') and (pid, sid) not in data['cells']
                 and not data['not_applicable'].get((pid, sid)) and not reference(sid)]
        block = {'searched': len(seen), 'found': sum(s['outcome'] == 'found' for s in seen),
                 'identified': sum(s['identified'] for s in seen),
                 'recheck': queue.get(pid, 0), 'sources': seen, 'never': never[:SHOWN]}
        if len(never) > SHOWN:
            block['neverMore'] = len(never) - SHOWN
        blocks[pid] = block
    return blocks


def attach(instance, graph):
    """Add `coverage` to the reader people; a failure leaves the graph unchanged."""
    try:
        blocks = person_blocks(instance)
    except Exception:  # noqa: BLE001 - the display is optional; a broken journal is reported by `instance check`
        return graph
    for pid, block in blocks.items():
        if pid in graph['people']:
            graph['people'][pid]['coverage'] = block
    return graph
