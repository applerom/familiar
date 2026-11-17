// Personal desks only. CloudFront authenticates cache hits as well as misses.
import cf from 'cloudfront';
import crypto from 'crypto';
const store = cf.kvs();
function response(status, body, location) {
  const headers = {'cache-control': {value: 'no-store'},
    'content-type': {value: 'text/plain; charset=utf-8'}};
  if (location) headers.location = {value: location};
  return {statusCode: status, headers: headers, body: body};
}
async function handler(event) {
  const r = event.request;
  const path = resourcePath(r.uri);
  if (path === null) return response(400, 'Invalid resource path');
  // Nothing supplied by the viewer may impersonate an authenticated principal.
  ['x-familiar-user', 'x-familiar-role', 'x-familiar-person', 'x-familiar-host'].forEach(k => delete r.headers[k]);
  r.headers['x-familiar-host'] = {value: r.headers.host.value};
  delete r.headers.authorization;
  if (['/auth/login', '/auth/start', '/auth/callback', '/auth/logout'].indexOf(r.uri) !== -1) return r;
  let user;
  try {
    const token = r.cookies['__Host-familiar'].value.split('.');
    if (token.length !== 2 || token[0].length > 3000) throw Error('cookie');
    const key = await store.get('session-key');
    const actual = crypto.createHmac('sha256', key).update(token[0]).digest('hex');
    if (actual.length !== token[1].length) throw Error('signature');
    let difference = 0;
    for (let i = 0; i < actual.length; i++) difference |= actual.charCodeAt(i) ^ token[1].charCodeAt(i);
    if (difference) throw Error('signature');
    user = JSON.parse(Buffer.from(token[0], 'base64url').toString('utf8'));
    if (!user.sub || !user.username || !user.session || user.exp <= Date.now() / 1000 ||
        ['owner', 'reader'].indexOf(user.role) === -1) throw Error('claims');
    const record = await store.get('user:' + user.sub);
    const current = JSON.parse(record);
    if (!current.enabled || current.session !== user.session) throw Error('revoked');
  } catch (_) {
    return response(302, 'Sign in', '/auth/login');
  }
  // Reader resources are allow-listed. New desk service pages default to owner-only.
  if (user.role !== 'owner' && (path === '/api/access' || path === '/desk' || path.indexOf('/desk/') === 0 &&
      !/^\/desk\/(?:desk\.(?:js|css)|tree-add\.(?:js|css)|session\.js|words\.json|stories\/[a-z0-9_-]+\.html)$/.test(path))) {
    return response(403, 'This page is for the family owner. / Эта страница доступна хозяину семьи.');
  }
  r.headers['x-familiar-user'] = {value: user.sub};
  r.headers['x-familiar-role'] = {value: user.role};
  // Person IDs stay in the signed JSON, never in an HTTP header: Unicode and
  // control characters in an otherwise valid ID must not invalidate the request.
  if (r.uri === '/') r.uri = '/index.html';
  return r;
}

// Compare meaning before role checks; reject malformed and multiply encoded paths.
function resourcePath(uri) {
  try {
    if (typeof uri !== 'string' || uri[0] !== '/') return null;
    const decoded = decodeURIComponent(uri).toLowerCase();
    if (decoded[0] !== '/' || /[%\\?#\s\x00-\x1f\x7f]/.test(decoded)) return null;
    const parts = [];
    for (const part of decoded.split('/')) {
      if (!part || part === '.') continue;
      if (part === '..') { if (!parts.length) return null; parts.pop(); }
      else { const clean = part.replace(/\.+$/, ''); if (!clean) return null; parts.push(clean); }
    }
    return '/' + parts.join('/');
  } catch (_) { return null; }
}
