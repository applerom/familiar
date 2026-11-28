# START_MODULE_CONTRACT: MOD-DESK-AWS
# PURPOSE: Provision and operate only a tagged account-owned desk stack through a replaceable AWS target.
# PRD_REF: docs/PRD.md#FAMILY-DESK
# INVARIANTS:
# - upload follows external 401 checks and a fresh comparison with the authorized local build [review: engine lead]
# - shared entry opens only after owner bytes are withdrawn and CDN invalidation completes [review: engine lead]
# - existing stacks must carry the exact project and family tags before any mutation [review: engine lead]
# - retrieved feedback is append-only, byte-preserving and never automatically accepted [review: engine lead]
# - the literal envelope arrives independently; each attached original must match its SHA-256 [review: engine lead]
# - failed provisioning retains recoverable credentials and diagnoses incomplete state before deployment use [review: engine lead]
# - cloud mutations share a crash-released family lock; login transitions resume from non-data state [review: engine lead]
# - personal uploads recheck the current stack and external gate after staging, immediately before sync [review: engine lead]
# CHANGES_WITH:
# - MOD-DESK-AWS-TEMPLATE (logical outputs)
# - MOD-FAMILY-WRITER (secrets and feedback inbox)
# :END_MODULE_CONTRACT
import base64
import hashlib
import json
import os
import re
import secrets as random_secrets
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from functools import wraps
from importlib.resources import files as package_files

from familiar.instance.gate import boundary

from .model import publication, secret_path, secrets


def cloud_command(function):
    @wraps(function)
    def locked(instance, *args, **kwargs):
        from familiar.instance.writer import desk_cloud
        publication(instance)  # Refuse an unselected target before even creating a lock.
        command = 'desk ' + ('user ' + args[0].user_action if function.__name__ == 'execute'
                             else function.__name__.replace('_', '-'))
        with desk_cloud(instance, command):
            return function(instance, *args, **kwargs)
    return locked


def _aws(instance, *args, binary=False, missing=False, timeout=55):
    target = publication(instance)
    command = ['aws', '--no-cli-pager', '--region', target.get('region', 'eu-north-1')]
    if target.get('profile'):
        command += ['--profile', target['profile']]
    command += list(args)
    if not binary:
        command += ['--output', 'json']
    try:
        result = subprocess.run(command, check=False, capture_output=True, timeout=timeout,
                                env=os.environ | {'AWS_PAGER': '', 'AWS_CLI_AUTO_PROMPT': 'off',
                                                  'AWS_CLI_FILE_ENCODING': 'UTF-8',
                                                  'PYTHONIOENCODING': 'UTF-8', 'PYTHONUTF8': '1'})
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'AWS {args[0]} {args[1]} timed out; rerun safely') from None
    except FileNotFoundError:
        raise RuntimeError('AWS CLI program "aws" was not found; install it and configure '
                           'an authorized profile, or use desk build and desk serve locally') from None
    if result.returncode:
        error = result.stderr.decode('utf-8', errors='replace')
        if 'profile' in error.lower() and ('could not be found' in error.lower()
                                          or 'does not exist' in error.lower()):
            raise RuntimeError('AWS profile was not found; configure the profile selected in '
                               'familiar.toml [publication] or choose an existing authorized profile')
        if 'Unable to locate credentials' in error:
            raise RuntimeError('AWS credentials are unavailable; authorize the selected AWS profile '
                               'before retrying desk provision')
        if missing and 'does not exist' in error and 'ValidationError' in error:
            return None
        if 'No updates are to be performed' in error:
            return {}
        code = re.search(r'\(([-A-Za-z0-9_.]+)\)', error)
        raise RuntimeError(f'AWS {args[0]} {args[1]} failed: {code[1] if code else "see AWS session/permissions"}')
    return result.stdout if binary else json.loads(result.stdout or '{}')


def _target(instance):
    target = publication(instance)
    stack, family = target.get('stack', ''), target.get('family_tag', '')
    if not re.fullmatch(r'familiar-[a-z0-9-]{1,80}', stack):
        raise ValueError('publication.stack must be a dedicated familiar-* stack')
    if not re.fullmatch(r'[a-z0-9-]{1,40}', family):
        raise ValueError('publication.family_tag is required')
    if target.get('region', 'eu-north-1') != 'eu-north-1':
        raise ValueError('AWS desk currently requires eu-north-1')
    return stack, family


def _stack(instance):
    stack, family = _target(instance)
    result = _aws(instance, 'cloudformation', 'describe-stacks', '--stack-name', stack, missing=True)
    if result is None:
        return None
    value = result['Stacks'][0]
    tags = {t['Key']: t['Value'] for t in value.get('Tags', [])}
    if tags.get('project') != 'familiar' or tags.get('family') != family:
        raise ValueError('Refusing a stack without this desk ownership tag pair')
    return value


def _outputs(stack):
    return {row['OutputKey']: row['OutputValue'] for row in stack.get('Outputs', [])}


def _authorization(state):
    return 'Basic ' + base64.b64encode((state['login'] + ':' + state['password']).encode()).decode()


def request(url, *, authorization=None, data=None, method=None, follow_redirects=True):
    headers = {}
    if authorization:
        headers['Authorization'] = authorization
    if data is not None:
        headers.update({'Content-Type': 'application/json',
                        'X-Amz-Content-Sha256': hashlib.sha256(data).hexdigest()})
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        opener = urllib.request.build_opener() if follow_redirects else urllib.request.build_opener(NoRedirect)
        with opener.open(req, timeout=25) as response:
            return response.status, response.read(), {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as error:
        return error.code, error.read(), {k.lower(): v for k, v in error.headers.items()}
    except urllib.error.URLError:
        raise RuntimeError('Desk HTTPS connection failed; retry after distribution deployment') from None


def _anonymous(state):
    for path in ('/', '/graph.json', '/reader-manifest.json', '/api/feedback', '/desk/asks.html'):
        status, _, headers = request(state['url'] + path, follow_redirects=False)
        if state.get('login_mode') == 'personal':
            if status != 302 or headers.get('location') != '/auth/login':
                raise ValueError('Anonymous personal gate check failed; no family data may be uploaded')
            continue
        if status != 401 or 'Basic ' not in headers.get('www-authenticate', ''):
            raise ValueError('Anonymous gate check failed; no family data may be uploaded')


@boundary('consume')
@cloud_command
def provision(instance):
    from familiar.instance.writer import desk_secret, desk_transition
    from .accounts import mode
    login_mode = mode(instance)
    stack_name, family = _target(instance)
    before = _stack(instance)
    if before and not secret_path(instance).exists():
        raise ValueError('Existing stack has no local deployment state; restore .secrets/desk.txt '
                         'from its private backup; refusing to adopt it')
    if not secret_path(instance).exists():
        desk_secret(instance, {'schema_version': 1, 'login': random_secrets.token_urlsafe(9),
                              'password': random_secrets.token_urlsafe(27)})
    state = secrets(instance, deploying=True)
    if login_mode == 'personal' and not state.get('session_key'):
        state['session_key'] = random_secrets.token_urlsafe(48)
        desk_secret(instance, state)
    if before and not state.get('stack_id'):
        raise ValueError('Incomplete .secrets/desk.txt: missing stack_id for an existing stack; '
                         'restore its private state backup; refusing to adopt it')
    if before and state.get('stack_id') != before['StackId']:
        raise ValueError('Desk stack identity changed; refusing mutation')
    journal = instance._inside('.state/desk-transition.json')
    transition = json.loads(journal.read_bytes()) if journal.exists() else None
    resuming = transition is not None
    if transition:
        if not before or transition['stack_id'] != before['StackId']:
            raise ValueError('Desk transition stack identity changed; refusing mutation')
        if transition['to'] != login_mode:
            raise ValueError('Resume desk provision with publication.login=' + transition['to']
                             + ' before choosing another login mode')
        print('Resuming desk login transition; reconciling the owned stack and external gate', flush=True)
    elif before and state.get('login_mode', 'shared') != login_mode:
        transition = {'stack_id': before['StackId'], 'from': state.get('login_mode', 'shared'),
                      'to': login_mode, 'stage': 'withdrawing'}
        desk_transition(instance, transition)
    switched = (transition and transition['stage'] == 'updating'
                and bool(_outputs(before).get('UserPool')) == (login_mode == 'personal'))
    if before and login_mode == 'shared' and (state.get('login_mode') == 'personal'
                                              or _outputs(before).get('UserPool')) and not switched:
        if before['StackStatus'].endswith('_IN_PROGRESS'):
            raise ValueError('Wait for the personal stack deployment, then rerun desk provision')
        outputs = _outputs(before)
        if any(state.get(k) != outputs.get(v) for k, v in
               [('bucket', 'Bucket'), ('distribution', 'Distribution'), ('url', 'Url')]):
            raise ValueError('Restore the personal deployment state before switching to shared login')
        _anonymous(state)
        print('Withdrawing correspondence before opening shared login; '
              'a checked desk build and completed CDN invalidation are required', flush=True)
        try:
            _upload(instance, state, personal=False)
        except (ValueError, RuntimeError) as error:
            raise RuntimeError('Shared login was not opened. Run desk build, then rerun desk provision; '
                               'wait for CDN invalidation to complete. ' + str(error)) from error
    if transition:
        transition['stage'] = 'updating'
        desk_transition(instance, transition)  # Persist intent before an accepted-but-lost response.
    auth_hash = hashlib.sha256(_authorization(state).encode()).hexdigest()
    template = package_files('familiar.desk').joinpath('aws', 'stack.yaml')
    operation = 'update-stack' if before else 'create-stack'
    if before and before['StackStatus'].endswith('_IN_PROGRESS'):
        print('Desk stack already deploying; checking it in this run', flush=True)
    else:
        if login_mode == 'personal':
            from .accounts import runtime_key, template, template_url
            from familiar.instance.writer import desk_private
            location = ({'TemplateURL': template_url(instance, before)} if before
                        else {'TemplateBody': template(bootstrap=True)})
            payload = {'StackName': stack_name, **location,
                'Capabilities': ['CAPABILITY_IAM'],
                'DeploymentConfig': {'Mode': 'EXPRESS', 'DisableRollback': True},
                'Parameters': [{'ParameterKey': 'SessionKey', 'ParameterValue': state['session_key']},
                               {'ParameterKey': 'AccessRuntimeKey', 'ParameterValue': runtime_key(before)},
                               {'ParameterKey': 'FamilyTag', 'ParameterValue': family}],
                'Tags': [{'Key': 'project', 'Value': 'familiar'}, {'Key': 'family', 'Value': family}]}
            path = desk_private(instance, 'desk-provision.json', payload)
            try:
                result = _aws(instance, 'cloudformation', operation, '--cli-input-json', 'file://' + str(path))
            finally:
                desk_private(instance, 'desk-provision.json', None)
        else:
            result = _aws(instance, 'cloudformation', operation, '--stack-name', stack_name,
                '--template-body', 'file://' + str(template), '--capabilities', 'CAPABILITY_IAM',
                '--deployment-config', 'Mode=EXPRESS,DisableRollback=true',
                '--parameters', json.dumps([{'ParameterKey': 'AuthHash', 'ParameterValue': auth_hash},
                                           {'ParameterKey': 'FamilyTag', 'ParameterValue': family}]),
                '--tags', 'Key=project,Value=familiar', 'Key=family,Value=' + family)
        if result.get('StackId'):
            state['stack_id'] = result['StackId']
            desk_secret(instance, state)
    # Bounded foreground wait, with progress. No process survives the command.
    deadline = time.monotonic() + 540
    while True:
        current = _stack(instance)
        if not current:
            raise ValueError('Desk stack is missing; rerun desk provision to create it')
        status = current['StackStatus']
        if status in {'CREATE_COMPLETE', 'UPDATE_COMPLETE'}:
            break
        if not status.endswith('_IN_PROGRESS'):
            raise RuntimeError('Desk stack did not complete: ' + status)
        if time.monotonic() >= deadline:
            raise RuntimeError('Desk stack still deploying; rerun desk provision')
        print('Desk stack: ' + status, flush=True)
        time.sleep(15)
    if login_mode == 'personal':
        from .accounts import access_runtime
        current = access_runtime(instance, current, state)
    outputs = _outputs(current)
    missing = [k for k in ('Url', 'Bucket', 'Distribution', 'FeedbackUrl') if not outputs.get(k)]
    if missing:
        raise ValueError('Desk stack outputs are incomplete: ' + ', '.join(missing)
                         + '; correct the owned stack deployment, then rerun desk provision')
    state.update({'url': outputs['Url'], 'bucket': outputs['Bucket'],
                  'distribution': outputs['Distribution'], 'feedback_url': outputs['FeedbackUrl'],
                  'login_mode': login_mode})
    if login_mode == 'personal':
        from .accounts import configure
        for field, key in [('user_pool', 'UserPool'), ('user_client', 'UserClient'), ('session_store', 'SessionStore')]:
            if not outputs.get(key):
                raise ValueError('Personal stack output missing: ' + key)
            state[field] = outputs[key]
        desk_secret(instance, state)
        configure(instance, state)
    desk_secret(instance, state)
    # Express completion can precede CloudFront/DNS readiness. Wait in this
    # foreground operation; never upload a family while the gate is unproven.
    deadline = time.monotonic() + 240
    while True:
        try:
            _anonymous(state)
            break
        except (RuntimeError, ValueError):
            if time.monotonic() >= deadline:
                raise
            print('Waiting for the external desk gate', flush=True)
            time.sleep(15)
    state['anonymous_gate_verified'] = True
    desk_secret(instance, state)
    desk_transition(instance, None)
    return ('Desk login transition resumed and completed. ' if resuming else '') + (
            'Desk provisioned; anonymous requests redirect to personal sign-in; create identities with desk user add'
            if login_mode == 'personal' else
            'Desk provisioned; anonymous requests: 401; address and login saved in .secrets/desk.txt; '
            'correspondence is not published; enable personal logins to include it')


@boundary('consume')
@cloud_command
def publish(instance):
    state = secrets(instance)
    from .accounts import mode
    if state.get('login_mode', 'shared') != mode(instance):
        raise ValueError('Desk login selection changed; run desk provision before publishing')
    current = _stack(instance)
    if not current or state.get('stack_id') != current['StackId']:
        raise ValueError('Provision this desk before publishing')
    outputs = _outputs(current)
    if any(state.get(k) != outputs.get(v) for k, v in
           [('bucket', 'Bucket'), ('distribution', 'Distribution'), ('url', 'Url')]):
        raise ValueError('Desk deployment state differs from the owned stack')
    _anonymous(state)
    try:
        waiting = json.loads((instance.path('state') / 'desk-quarantine.json').read_text(encoding='utf-8'))['quarantine']
        print(f'Quarantine: {len(waiting)} contributions or versions wait for an uncommitted reference '
              '(not in this desk)', flush=True)
    except (OSError, ValueError, KeyError):
        print('Quarantine: unknown (desk built by an earlier engine)', flush=True)
    count = _upload(instance, state, personal=mode(instance) == 'personal')
    return ('Desk published: ' + str(count) + ' delivery files; credentials remain in .secrets/desk.txt'
            + ('; correspondence is not published; enable personal logins to include it'
               if mode(instance) == 'shared' else ''))


def _upload(instance, state, *, personal):
    from familiar.instance.writer import desk_upload
    # Sync only staged hosted bytes; --delete withdraws any previous owner page.
    with desk_upload(instance, personal=personal) as (directory, count):
        if personal:
            from familiar.instance.model import Instance
            from .accounts import mode
            fresh = Instance(instance.root)
            current = _stack(fresh)
            latest = secrets(fresh)
            if (mode(fresh) != 'personal' or latest.get('login_mode') != 'personal'
                    or not current or current['StackId'] != state['stack_id']
                    or current['StackStatus'] not in {'CREATE_COMPLETE', 'UPDATE_COMPLETE'}
                    or not _outputs(current).get('UserPool')
                    or any(_outputs(current).get(v) != state.get(k) for k, v in
                           [('bucket', 'Bucket'), ('distribution', 'Distribution'), ('url', 'Url')])):
                raise ValueError('Personal upload is stale; run desk provision, then desk build and desk publish')
            _anonymous(latest)  # After staging, immediately before sending any owner bytes.
        _aws(instance, 's3', 'sync', str(directory), 's3://' + state['bucket'] + '/site/',
             '--delete', '--cache-control', 'max-age=0,s-maxage=300,must-revalidate',
             '--only-show-errors', binary=True, timeout=300)
    invalidation = _aws(instance, 'cloudfront', 'create-invalidation',
                        '--distribution-id', state['distribution'], '--paths', '/*')
    print('Waiting for desk CDN invalidation to complete', flush=True)
    _aws(instance, 'cloudfront', 'wait', 'invalidation-completed',
         '--distribution-id', state['distribution'], '--id', invalidation['Invalidation']['Id'], timeout=600)
    return count


@boundary('consume')
def verify(instance):
    state = secrets(instance)
    _anonymous(state)
    if state.get('login_mode') != 'personal':
        auth = _authorization(state)
        for path in ('/', '/graph.json', '/reader-manifest.json', '/desk/asks.html', '/desk/progress.html'):
            status, _, _ = request(state['url'] + path, authorization=auth)
            if status != 200:
                raise ValueError(f'Authenticated delivery check failed ({status})')
    if request(state['feedback_url'])[0] != 403:
        raise ValueError('Direct feedback origin must refuse anonymous requests')
    if request('https://' + state['bucket'] + '.s3.eu-north-1.amazonaws.com/site/graph.json')[0] != 403:
        raise ValueError('Direct S3 origin must refuse anonymous requests')
    return ('Anonymous: personal sign-in redirect; direct S3/Lambda: 403; execute the personal browser walk for roles'
            if state.get('login_mode') == 'personal' else
            'Anonymous: 401; authenticated reader and desk: 200; direct S3/Lambda: 403')


def _fetch_attachment(instance, state, identity, item, version):
    from familiar.instance.writer import attachment_path, desk_feedback_file
    from .attachments import remote_attachment_key, stored_attachment
    stored_attachment(item)
    if type(version) is not int or version not in {1, 2}:
        raise ValueError('unknown attachment storage version')
    path = attachment_path(instance, identity, item['n'], item['kind'])
    present = path.is_file()
    if present:
        if path.stat().st_size != item['size']:
            raise ValueError('local original differs from its recorded size')
        raw = path.read_bytes()
    else:
        key = remote_attachment_key(identity, item, version)
        head = _aws(instance, 's3api', 'head-object', '--bucket', state['bucket'], '--key', key)
        if head['ContentLength'] != item['size']:
            raise ValueError('remote original differs from its recorded size')
        raw = _aws(instance, 's3', 'cp', f"s3://{state['bucket']}/{key}", '-',
                   '--only-show-errors', binary=True, timeout=300)
    if len(raw) != item['size'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('original differs from its SHA-256')
    if not present:
        desk_feedback_file(instance, identity, item['n'], item['kind'], raw)
    return not present


def _fetch_added(instance, state, envelope, key, item):
    from familiar.instance.writer import attachment_catalog, attachment_path, desk_add_feedback_file, desk_loopback
    from .attachments import display_name, stored_attachment
    identity = envelope['id']
    stored_attachment(item | {'n': 1})
    for row in attachment_catalog(instance, identity):
        if row['sha256'] == item['sha256']:
            path = attachment_path(instance, identity, row['n'], row['kind'], row['sha256'])
            if path.is_file():
                with path.open('rb') as stream:
                    if path.stat().st_size != item['size'] or hashlib.file_digest(stream, 'sha256').hexdigest() != item['sha256']:
                        raise ValueError('local original differs from its recorded size or SHA-256')
                return False
            break
    bucket = state['bucket']
    head = _aws(instance, 's3api', 'head-object', '--bucket', bucket, '--key', key)
    name = head.get('Metadata', {}).get('name64', '')
    item['name'] = display_name(base64.urlsafe_b64decode(name + '=' * (-len(name) % 4)).decode('utf-8'))
    if head['ContentLength'] != item['size']:
        raise ValueError('remote original differs from its recorded size')
    raw = _aws(instance, 's3', 'cp', f's3://{bucket}/{key}', '-', '--only-show-errors', binary=True, timeout=300)
    if len(raw) != item['size'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('original differs from its SHA-256')
    with desk_loopback(instance):
        return desk_add_feedback_file(instance, envelope, item, raw)


@boundary('consume')
@cloud_command
def fetch_feedback(instance):
    from familiar.instance.writer import desk_expire_feedback_writes, desk_feedback
    state = secrets(instance)
    current = _stack(instance)
    if not current or state.get('stack_id') != current['StackId'] or state.get('bucket') != _outputs(current).get('Bucket'):
        raise ValueError('Feedback target is not the owned desk stack')
    try:
        desk_expire_feedback_writes(instance, time.time())
    except OSError as error:
        print(f'Feedback scratch cleanup: {error}')
    rows = _aws(instance, 's3api', 'list-objects-v2', '--bucket', state['bucket'], '--prefix', 'feedback/inbox/')
    saved = received = failures = 0
    item_errors = (ValueError, TypeError, KeyError, OSError, RuntimeError)
    from .attachments import original_prefix, original_rows, remote_attachment_key, stored_attachment
    try:
        objects = _aws(instance, 's3api', 'list-objects-v2', '--bucket', state['bucket'],
                       '--prefix', 'feedback/attachments/').get('Contents', [])
        originals = {}
        for obj in objects:
            identity = obj['Key'].split('/')[2]
            originals.setdefault(identity, {})[obj['Key']] = obj
    except item_errors as error:
        print(f'Attachment listing: {error}')
        originals = None
        failures += 1
    for row in rows.get('Contents', []):
        key = row.get('Key', '') if isinstance(row, dict) else ''
        name = key.removeprefix('feedback/inbox/') if isinstance(key, str) else ''
        try:
            if not re.fullmatch(r'[a-f0-9-]{36}\.json', name) or row.get('Size', 0) > 24000:
                raise ValueError('unexpected feedback object name or size')
            identity = str(uuid.UUID(name[:-5]))
            destination = instance._inside('family/feedback/inbox/' + identity + '.json')
            existed = destination.is_file()
            content = _aws(instance, 's3', 'cp', 's3://' + state['bucket'] + '/' + key, '-',
                           '--only-show-errors', binary=True)
            data = json.loads(content)
            if (not isinstance(data, dict) or data.get('id') != identity or data.get('schema_version') != 1
                    or not isinstance(data.get('text', ''), str) or 'text' not in data and not data.get('files')):
                raise ValueError('malformed feedback')
        except item_errors as error:
            print(f'Feedback {name}: {error}')
            failures += 1
            continue
        try:
            reason = desk_feedback(instance, identity, content)
            if reason:
                print(f'Feedback {identity}: {reason}')
        except item_errors as error:
            print(f'Feedback {identity}: {error}')
            failures += 1
            try:
                recorded = destination.is_file() and destination.read_bytes() == content
            except OSError:
                recorded = False
            if not recorded:
                continue
        saved += not existed
        attachments = data.get('files', [])
        if not isinstance(attachments, list):
            print(f'Feedback {identity}: invalid attachment list')
            failures += 1
            continue
        seen = set()
        objects = (originals or {}).get(identity, {})
        version = data.get('attachment_storage', 1)
        for index, item in enumerate(attachments, 1):
            try:
                if not isinstance(item, dict) or item.get('n') in seen:
                    raise ValueError('invalid or repeated attachment row')
                stored_attachment(item)
                if version != 2 or originals is not None and remote_attachment_key(identity, item, 2) in objects:
                    received += _fetch_attachment(instance, state, identity, item, version)
                seen.add(item['n'])
            except item_errors as error:
                number = item.get('n') if isinstance(item, dict) and type(item.get('n')) is int else index
                print(f'Attachment {identity}/{number}: {error}')
                failures += 1
        sub = data.get('sender', {}).get('sub', '')
        if sub and objects:
            try:
                prefix = original_prefix(identity, sub)
                for item in original_rows(prefix, (obj for key, obj in objects.items() if key.startswith(prefix))):
                    try:
                        key = prefix + item['sha256'] + '.' + item['kind']
                        received += _fetch_added(instance, state, data, key, item)
                    except item_errors as error:
                        print(f'Attachment {identity}/{item["sha256"][:12]}: {error}')
                        failures += 1
            except item_errors as error:
                print(f'Attachments {identity}: {error}')
                failures += 1
    return (f'Feedback retrieved: {saved}' + (f', attached files: {received} (familiar intake attachment)' if received else '')
            + (f', failures: {failures} (see IDs above; retry after repair)' if failures else '')
            + '; original remote objects retained; no memory accepted')


@boundary('consume')
@cloud_command
def delete_stack(instance):
    """An explicit host operation, confined to this desk's tagged stack."""
    state = secrets(instance)
    current = _stack(instance)
    if not current or state.get('stack_id') != current['StackId']:
        raise ValueError('Refusing deletion: stack identity does not match this desk')
    _aws(instance, 'cloudformation', 'delete-stack', '--stack-name', current['StackId'])
    return 'Owned desk stack deletion requested; the bucket and feedback are retained; coordinates remain in .secrets/desk.txt'
