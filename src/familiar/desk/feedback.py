# START_MODULE_CONTRACT: MOD-DESK-FEEDBACK
# PURPOSE: Validate the same literal narrator message envelope for local and hosted desks.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - accepted feedback is bounded literal text, never a tree mutation [review: engine lead]
# - add_person fields stay the narrator's bounded strings beside the readable text [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-AWS-TEMPLATE (identical envelope and subject matching; no cooldown)
# - MOD-DESK-BUILD (reader receipt projection)
# - MOD-FAMILY-WRITER (immutable inbox)
# :END_MODULE_CONTRACT
import json
import uuid
from datetime import UTC, datetime

FIELDS = {'id', 'text', 'kind', 'page', 'person', 'question', 'ask_id', 'finding',
          'client_time', 'subject', 'anchor', 'relation', 'place', 'where', 'screen',
          'feed', 'step', 'text_mode', 'language', 'selection', 'viewport',
          'engine_version', 'build'}
LIMITS = {'page': 2048, 'person': 200, 'question': 200, 'ask_id': 200, 'finding': 1000,
          'client_time': 40, 'subject': 200, 'anchor': 200, 'relation': 40, 'place': 200,
          'where': 1000, 'screen': 80, 'feed': 200, 'step': 40, 'text_mode': 40,
          'language': 40, 'selection': 300, 'viewport': 40, 'engine_version': 80, 'build': 100}
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


def validate(body):
    if len(body) > 20000:
        raise ValueError('too_large')
    data = json.loads(body)
    if (not isinstance(data, dict)
            or not all(isinstance(data.get(k, ''), str) for k in FIELDS)
            or not 1 <= len(data.get('text', '').strip()) <= 6000 or len(data['text']) > 6000
            or not data.get('kind', '').strip()
            or any(len(data.get(k, '')) > limit for k, limit in LIMITS.items())
            or not data.get('page', '').startswith('/') or data['page'].startswith('//')):
        raise ValueError('invalid_feedback')
    if data.get('kind') == 'add_person' and (not data.get('anchor') or data.get('relation') not in RELATIONS):
        raise ValueError('invalid_feedback')
    if not new_person_valid(data):
        raise ValueError('invalid_feedback')
    data['id'] = str(uuid.UUID(data['id']))
    return data


def received(data):
    return data | {'schema_version': 1, 'received_at': datetime.now(UTC).isoformat()}


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
