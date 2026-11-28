# START_MODULE_CONTRACT: MOD-DESK-MODEL
# PURPOSE: Define the host-authorized personal dataset and ignored desk configuration.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - a desk decision names its sender, recipient, date, family and accepted personal-reader scope [review: engine lead]
# - deployment state and credentials have one ignored home outside the delivery directory [review: engine lead]
# - local desk settings never consult publication; cloud state names missing fields before use [review: engine lead]
# - desk language switches use the selected pack over the bundled English wording [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-WRITER (desk storage)
# :END_MODULE_CONTRACT
import json
from datetime import date
from pathlib import Path

from familiar.instance.model import Instance
from familiar.instance.packs import bundled_root, read


def settings(instance):
    return instance.config.get('desk', {})


def publication(instance):
    """The cloud boundary, deliberately absent from local build/serve paths."""
    target = instance.config.get('publication', {})
    choice = target.get('target', 'none') if isinstance(target, dict) else None
    if choice not in ('none', 'aws'):
        raise ValueError('publication.target must be none or aws; local viewing needs no '
                         'publication target: use desk build, then desk serve --port 0')
    if choice == 'none':
        raise ValueError('Publication is not configured (publication.target = none). '
                         'Use desk build, then desk serve --port 0 for local viewing. '
                         'For AWS, add [publication] with target = "aws", region = "eu-north-1", '
                         'stack = "familiar-example-desk", family_tag = "example" and, '
                         'if needed, profile = "your-profile" to familiar.toml; see docs/family-desk.md')
    return target


def source(instance):
    config = settings(instance)
    return Instance((instance.root / config.get('source', '.')).resolve())


def output(instance):
    config = settings(instance)
    # The build is disposable; the only live family mutations are feedback and
    # ignored desk state. Source snapshots remain read-only.
    return instance._inside(config.get('output', '.secrets/desk-site'))


def secret_path(instance):
    return instance._inside('.secrets/desk.txt')


def secrets(instance, *, deploying=False):
    publication(instance)
    path = secret_path(instance)
    if not path.is_file():
        raise ValueError('Desk deployment state is missing: .secrets/desk.txt; run desk provision first')
    try:
        state = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError):
        raise ValueError('Invalid .secrets/desk.txt; restore the deployment state from a private '
                         'backup before retrying; do not overwrite an existing stack identity') from None
    fields = ('login', 'password') if deploying else (
        'login', 'password', 'stack_id', 'url', 'bucket', 'distribution', 'feedback_url')
    missing = [k for k in fields if not isinstance(state, dict)
               or not isinstance(state.get(k), str) or not state[k].strip()]
    if missing:
        raise ValueError('Incomplete .secrets/desk.txt: missing ' + ', '.join(missing)
                         + ('; restore the private state backup before retrying desk provision'
                            if any(k in missing for k in ('login', 'password'))
                            else '; rerun desk provision to finish deployment'))
    return state


# Swedish has no desk pack yet; the attach control and its refusals still speak to a Swedish reader.
SWEDISH_ATTACH = {'attach': 'Bifoga ett foto eller en skanning', 'attach_remove': 'Ta bort',
                  'file_kind': 'Välj ett foto eller en skanning.',
                  'file_large': 'Filen är större än {mb} MB. Ett nytt foto av sidan räcker.',
                  'file_many': 'Högst {count} filer åt gången; resten i nästa kommentar.',
                  'file_day': 'Det räcker med filer för i dag, resten i morgon. Texten finns kvar här.',
                  'file_failed': 'Anslutningen bröts. Du kan försöka skicka filerna igen.',
                  'file_batch_large': 'Filerna till en kommentar får tillsammans vara högst 100 MB.',
                  'files_pending': 'Kvar att skicka: {names}.', 'files_retry': 'Välj filer igen',
                  'files_sending': 'Skickar filer…', 'words_sent': 'Dina ord kom fram. Skickar filerna…',
                  'original_sent': 'Ditt tidigare meddelande kom fram. Din ändrade text finns kvar här. Tryck på Skicka för att skicka den.'}


def words(instance, language=None):
    language = language or instance.source_language
    pack = instance.language_pack_data.get(language, {}).get('data', {})
    if not pack and language == 'en':
        pack = read(bundled_root() / 'demo-english' / 'pack.toml')
    base = read(bundled_root() / 'demo-english' / 'pack.toml')['desk']
    local = pack.get('desk', {})
    result = base | local | {'show': base['show'] | local.get('show', {}),
                            'correspondence': base['correspondence'] | local.get('correspondence', {}),
                            'asks': base['asks'] | local.get('asks', {}),
                            'blanks': base['blanks'] | local.get('blanks', {}),
                            'search_map': base['search_map'] | local.get('search_map', {})}
    if language.split('-')[0] == 'sv' and 'attach' not in local:
        result |= SWEDISH_ATTACH
    return result


def decision(instance):
    config = settings(instance)
    path = instance._inside(config.get('decision', 'family/desk-access.json'))
    if not path.is_file():
        raise ValueError('desk requires the recorded host decision: family/desk-access.json')
    raw = path.read_bytes()
    data = json.loads(raw)
    if (data.get('schema_version') != 1 or data.get('family_id') != instance.id
            or data.get('projection') != 'reader-private' or data.get('revoked', False)
            or not all(isinstance(data.get(k), str) and data[k].strip()
                       for k in ('host', 'recipient', 'decided_at', 'reason'))
            or data.get('dataset') != 'accepted-family-reader'
            or data.get('pages') != ['reader', 'journal', 'stories', 'cases', 'plan', 'questions']):
        raise ValueError('desk host decision does not authorize this family dataset and pages')
    date.fromisoformat(data['decided_at'])
    return path, raw


def feedback_count(instance):
    root = instance._inside('family/feedback')
    return sum(1 for p in (root / 'inbox').glob('*.json')
               if not (root / 'read' / p.name).exists())


def listing(root, pattern):
    """One ordering for selection and check: Windows path order ignores case, names do not."""
    paths = sorted(root.glob(pattern), key=lambda p: p.name)
    return paths, tuple(p.name for p in paths)


def sha(data):
    from familiar.instance.writer import content_digest
    return content_digest(data)


def relative(name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name
            or Path(name).is_absolute() or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('unsafe desk resource path')
    return name
