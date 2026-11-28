"""Match an amendment answer to the served offer in both feedback runtimes."""


def amendment_reply(data):
    return str(data.get('subject', '')).startswith('amendment:')


def amendment_offered(data, links):
    revision = data.get('amendment_revision')
    if data.get('kind') not in {'confirm', 'decline'} or not revision or not isinstance(links, dict):
        return False
    return any(slot.get('subject') == data.get('subject') and slot.get('amendment_revision') == revision
               for slot in links.get('blanks', {}).get(data.get('person'), []))
