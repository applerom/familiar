"""OAuth code/PKCE callback, composed into the existing feedback Lambda."""
# ruff: noqa: F821 -- the composed source supplies the file session helpers.
import hashlib
import hmac
import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request

import boto3
from botocore.exceptions import ClientError

cognito = boto3.client('cognito-idp')
SESSION_SECONDS = 3600


def b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def signed(data):
    raw = b64(json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
    return raw + '.' + hmac.new(os.environ['SESSION_KEY'].encode(), raw.encode(), hashlib.sha256).hexdigest()


def unsign(raw):
    body, signature = raw.split('.')
    expected = hmac.new(os.environ['SESSION_KEY'].encode(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError('signature')
    data = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
    if data['exp'] <= time.time():
        raise ValueError('expired')
    return data


def cookie(name, value, age):
    return f'{name}={value}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age={age}'


def auth_reply(status, body='', *, location=None, cookies=None, content_type='text/html; charset=utf-8'):
    result = {'statusCode': status, 'headers': {'content-type': content_type,
        'cache-control': 'no-store', 'referrer-policy': 'no-referrer',
        'x-content-type-options': 'nosniff'}, 'body': body}
    if location:
        result['headers']['location'] = location
    if cookies:
        result['cookies'] = cookies
    return result


def client():
    # Cognito verifies access-token signatures via GetUser; no JWT parser or
    # downloaded signing key is trusted by this function. ID/refresh tokens are discarded.
    return cognito.describe_user_pool_client(UserPoolId=os.environ['USER_POOL'],
        ClientId=os.environ['USER_CLIENT'])['UserPoolClient']


def auth(event):
    path = event.get('rawPath', '')
    headers = event.get('headers', {})
    host = headers.get('x-familiar-host', '')
    if not host.endswith('.cloudfront.net') or '/' in host:
        return auth_reply(400, 'Invalid desk host')
    origin = 'https://' + host
    domain = 'https://' + os.environ['COGNITO_DOMAIN']
    query = event.get('queryStringParameters') or {}
    jar = {}
    for line in event.get('cookies', []):
        name, _, value = line.partition('=')
        jar[name] = value
    if path == '/auth/session':
        try:
            claims = unsign(jar.get('__Host-familiar', ''))
            if claims['sub'] != headers.get('x-familiar-user'):
                raise ValueError('principal')
        except (ValueError, KeyError, TypeError):
            return auth_reply(401, '{}', content_type='application/json')
        return auth_reply(200, json.dumps({k: claims.get(k, '') for k in
            ('sub', 'username', 'role', 'person', 'login')}), content_type='application/json')
    if path == '/auth/logout':
        try:
            files_end_session(unsign(jar.get('__Host-familiar', '')))
        except (ValueError, KeyError, TypeError):
            pass  # No live personal session to close.
        except (ClientError, BotoCoreError):
            print('Could not revoke upload grants on logout; clearing browser cookies')
        target = domain + '/logout?' + urllib.parse.urlencode({
            'client_id': os.environ['USER_CLIENT'], 'logout_uri': origin + '/auth/login'})
        return auth_reply(302, location=target, cookies=[cookie('__Host-familiar', '', 0),
            cookie('__Host-familiar-flow', '', 0)])
    if path == '/auth/start':
        flow = {'state': secrets.token_urlsafe(32), 'verifier': secrets.token_urlsafe(48),
                'exp': int(time.time()) + 600, 'origin': origin}
        target = domain + '/oauth2/authorize?' + urllib.parse.urlencode({
            'response_type': 'code', 'client_id': os.environ['USER_CLIENT'],
            'redirect_uri': origin + '/auth/callback', 'scope': 'openid aws.cognito.signin.user.admin',
            'prompt': 'login',
            'state': flow['state'], 'code_challenge_method': 'S256',
            'code_challenge': b64(hashlib.sha256(flow['verifier'].encode()).digest())})
        return auth_reply(302, location=target,
            cookies=[cookie('__Host-familiar-flow', signed(flow), 600)])
    if path == '/auth/login':
        # Ambient requests redirected here (including favicon fetches) must not
        # replace the state/PKCE cookie of a login already in progress.
        # This is a help/continue page, never a credential form. Cognito owns all
        # password, forced-change and recovery interactions.
        body = ('<!doctype html><html lang="ru"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Вход в семейный кабинет · Family desk</title><style>'
            'body{font:18px/1.6 system-ui;margin:48px auto;padding:24px;max-width:560px;'
            'color:#24322b;background:#f5f1e6}a{display:block;padding:14px 20px;'
            'background:#486b52;color:white;border-radius:12px;text-align:center}'
            '</style><h1>Семейный кабинет</h1><p>Ваш личный вход · Your personal sign-in</p>'
            '<p><a href="/auth/start">Войти / Sign in</a></p>'
            '<p>Забыли пароль — напишите тому, кто дал вам вход. Если к входу добавлена почта, '
            'можно получить код через «Forgot your password?» на странице входа.</p>'
            '<p>Forgot your password? Contact the person who gave you access, or use email recovery '
            'on the sign-in page if an email was added.</p></html>')
        return auth_reply(200, body)
    if path != '/auth/callback':
        return auth_reply(404, 'Not found')
    try:
        flow = unsign(jar.get('__Host-familiar-flow', ''))
        if (flow['origin'] != origin or not query.get('code') or
                not hmac.compare_digest(query.get('state', ''), flow['state'])):
            raise ValueError('state')
        app = client()
        credentials = base64.b64encode((app['ClientId'] + ':' + app['ClientSecret']).encode()).decode()
        request = urllib.request.Request(domain + '/oauth2/token', data=urllib.parse.urlencode({
            'grant_type': 'authorization_code', 'client_id': app['ClientId'],
            'redirect_uri': origin + '/auth/callback', 'code': query['code'],
            'code_verifier': flow['verifier']}).encode(), headers={
                'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': 'Basic ' + credentials})
        with urllib.request.urlopen(request, timeout=8) as response:
            token = json.load(response)
        verified = cognito.get_user(AccessToken=token['access_token'])
        user = cognito.admin_get_user(UserPoolId=os.environ['USER_POOL'], Username=verified['Username'])
        attrs = {a['Name']: a['Value'] for a in user['UserAttributes']}
        if (not user['Enabled'] or user.get('UserStatus') != 'CONFIRMED' or
                attrs.get('custom:role') not in {'reader', 'owner'}):
            raise ValueError('disabled')
        claims = {'sub': attrs['sub'], 'username': user['Username'], 'role': attrs['custom:role'],
            'person': attrs.get('custom:person', ''), 'session': attrs['custom:session'],
            'exp': int(time.time()) + SESSION_SECONDS, 'login': secrets.token_urlsafe(12)}
        return auth_reply(302, location='/', cookies=[cookie('__Host-familiar', signed(claims), SESSION_SECONDS),
            cookie('__Host-familiar-flow', '', 0)])
    except (ValueError, KeyError, TypeError, urllib.error.URLError, ClientError):
        # No tokens, callback codes, passwords or AWS exception text go to logs.
        return auth_reply(400, '<p>Вход не завершён. <a href="/auth/login">Попробовать снова / Try again</a></p>',
            cookies=[cookie('__Host-familiar-flow', '', 0)])
