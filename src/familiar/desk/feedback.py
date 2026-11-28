# START_MODULE_CONTRACT: MOD-DESK-FEEDBACK
# PURPOSE: Validate the same literal narrator message envelope for local and hosted desks.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - accepted feedback is bounded literal text, never a tree mutation [review: engine lead]
# - correspondence feedback is owner-only, including remarks from its page [review: engine lead]
# - add_person fields stay the narrator's bounded strings beside the readable text [review: engine lead]
# - amendment replies are private envelopes and settle only an offer served to an authorized reader [review: engine lead]
# - a message may carry attached files instead of words; their list is declared, the bytes are checked by the server [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-AWS-TEMPLATE (identical envelope and subject matching; no cooldown)
# - MOD-DESK-BUILD (reader receipt projection)
# - MOD-DESK-ATTACHMENTS (declared files)
# - MOD-FAMILY-WRITER (immutable inbox)
# :END_MODULE_CONTRACT
import json
import uuid
from datetime import UTC, datetime
from urllib.parse import unquote

from familiar.instance.asks import FEEDBACK, WANTS, key

from .feedback_offer import amendment_reply

FIELDS = {'id', 'text', 'kind', 'page', 'person', 'question', 'ask_id', 'finding',
          'client_time', 'subject', 'anchor', 'relation', 'place', 'where', 'screen',
          'feed', 'step', 'text_mode', 'language', 'selection', 'viewport',
          'engine_version', 'build', 'amendment_revision'}
LIMITS = {'page': 2048, 'person': 200, 'question': 200, 'ask_id': 200, 'finding': 1000,
          'client_time': 40, 'subject': 200, 'anchor': 200, 'relation': 40, 'place': 200,
          'where': 1000, 'screen': 80, 'feed': 200, 'step': 40, 'text_mode': 40,
          'language': 40, 'selection': 300, 'viewport': 40, 'engine_version': 80, 'build': 100,
          'amendment_revision': 64}
RELATIONS = {'child', 'spouse', 'parent', 'father', 'mother', 'sibling', 'relative', 'self'}
# The narrator's own fields for one added person; `text` repeats them as the readable message.
NEW_PERSON = {'surname': 200, 'given': 200, 'patronymic': 200, 'maiden_surname': 200, 'birth': 200,
              'birth_place': 200, 'living': 20, 'death': 200, 'death_place': 200, 'known_from': 20,
              'told_by': 200, 'kin_words': 200, 'note': 4000}
CHOICES = {'living': {'alive', 'dead', 'unknown'}, 'known_from': {'memory', 'told', 'document'}}


def new_person_valid(data):
    person = data.get('new_person')
    if person is None:
        return True
    return (data.get('kind') == 'add_person' and isinstance(person, dict) and not set(person) - set(NEW_PERSON)
            and all(isinstance(v, str) and len(v) <= NEW_PERSON[k] for k, v in person.items())
            and all(person.get(k, '') in v | {''} for k, v in CHOICES.items()))


def owner_only(data):
    # Legacy receipts may name the page through an encoded or normalized alias.
    try:
        page = unquote(data.get('page', ''), errors='strict').lower().split('?', 1)[0]
        if '%' in page or '\\' in page or any(ord(c) < 32 for c in page):
            return True
        parts = []
        for part in page.split('/'):
            if part == '..':
                if parts:
                    parts.pop()
            elif part and part != '.':
                parts.append(part.rstrip('.'))
        page = '/' + '/'.join(parts)
    except (TypeError, ValueError, UnicodeError, AttributeError):
        return True
    return (data.get('kind') in {'correspondence_sent', 'correspondence_reply'}
            or data.get('screen', '').lower() == 'correspondence'
            or page.startswith('/desk/correspondence'))


def ask_valid(data):
    kind = data['kind']
    if kind not in FEEDBACK:
        return not any(k in data for k in ('wants', 'private', 'tender', 'via_child', 'ask_state', 'ask_context'))
    key(data.get('ask_id'))
    wants = data.get('wants', {})
    state = data.get('ask_state', '')
    context = data.get('ask_context', '')
    if not all(type(data.get(k, False)) is bool for k in ('private', 'tender', 'via_child')):
        return False
    if not isinstance(context, str) or context and (len(context) != 16 or any(c not in '0123456789abcdef' for c in context)):
        return False
    if kind == 'ask_answer':
        return (not state and isinstance(wants, dict) and not set(wants) - set(WANTS)
                and all(isinstance(v, str) and len(v) <= 1000 for v in wants.values()))
    return (not wants and isinstance(state, str) and (state in ('dont_know', 'private')
            or state.startswith('will_ask:') and 0 < len(state[9:]) <= 200))


def research_feedback(data):
    return data.get('kind') in FEEDBACK or amendment_reply(data)


def preserve_tender(instance, data):
    """Bind a local answer to the current ask before storing the literal envelope."""
    if data.get('kind') in FEEDBACK:
        from familiar.instance.asks import get
        from .model import source
        _, ask = get(source(instance), data['ask_id'])
        if ask.get('tender') or ask.get('state') == 'private':
            return data | {'tender': True, 'private': True}
    return data


def validate(body):
    if len(body) > 20000:
        raise ValueError('too_large')
    data = json.loads(body)
    if isinstance(data, dict) and 'files' in data:
        from .attachments import declared
        data['files'] = declared(data['files'])
    if (not isinstance(data, dict)
            or not all(isinstance(data.get(k, ''), str) for k in FIELDS)
            or not (1 if 'files' not in data else 0) <= len(data.get('text', '').strip()) <= 6000
            or len(data.get('text', '')) > 6000
            or not data.get('kind', '').strip()
            or any(len(data.get(k, '')) > limit for k, limit in LIMITS.items())
            or not data.get('page', '').startswith('/') or data['page'].startswith('//')):
        raise ValueError('invalid_feedback')
    if data.get('kind') == 'add_person' and (not data.get('anchor') or data.get('relation') not in RELATIONS):
        raise ValueError('invalid_feedback')
    if not new_person_valid(data) or not ask_valid(data):
        raise ValueError('invalid_feedback')
    from familiar.instance.correspondence import ACTIONS, token
    if data['kind'] in ACTIONS:
        token(data.get('subject'))
    data['id'] = str(uuid.UUID(data['id']))
    data.setdefault('text', '')
    return data


def received(data):
    return {k: v for k, v in data.items() if k not in {'sender', 'amendment_offered'}} | {
        'schema_version': 1, 'received_at': datetime.now(UTC).isoformat()}


def matches(data, subject):
    return bool(subject) and any(data.get(k) == subject for k in ('subject', 'anchor', 'question', 'ask_id', 'person'))


def receipt(instance, identity, read=None):
    """Only reader-facing review fields leave the researcher's mark."""
    path = instance._inside('family/feedback/read/' + str(uuid.UUID(identity)) + '.json')
    raw = read(path) if read else path.read_bytes() if path.is_file() else None
    if raw is None:
        return {'status': 'sent', 'reply': ''}
    mark = json.loads(raw)
    return {'status': 'addressed' if mark.get('status') == 'addressed' else 'read',
            'reply': mark.get('reply', '') if isinstance(mark.get('reply', ''), str) else ''}
