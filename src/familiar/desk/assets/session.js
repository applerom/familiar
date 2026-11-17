// Shared and loopback desks keep their existing anonymous reader behavior.
window.familiarDeskIdentity = location.hostname.endsWith('.cloudfront.net')
  ? fetch('/auth/session', {cache: 'no-store'}).then(r => r.ok ? r.json() : null).catch(() => null)
  : Promise.resolve(null);
window.familiarDeskIdentity.then(user => {
  window.familiarDeskUser = user;
  if (!user) return;
  document.documentElement.dataset.deskRole = user.role;
  if (user.role === 'reader') {
    document.querySelectorAll('[href="/desk/progress.html"]').forEach(n => n.remove());
  }
  if (user.role === 'owner') {
    const access = document.createElement('a'); access.href = '/desk/access.html';
    access.textContent = 'Доступ';
    if (location.pathname === access.pathname) access.setAttribute('aria-current', 'page');
    document.querySelector('#desk-nav')?.append(access);
  }
  const slot = document.querySelector('#desk-notice');
  if (slot) {
    const logout = document.createElement('a'); logout.href = '/auth/logout';
    logout.textContent = 'Выйти / Sign out'; logout.style.marginInlineStart = '12px';
    slot.append(logout);
  }
});
