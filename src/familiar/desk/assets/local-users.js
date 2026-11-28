const $ = id => document.getElementById(id);
const people = $('person'), users = $('users'), status = $('status'), add = $('add');
const credentials = $('credentials'), handout = $('handout');
let busy = false;

async function request(body) {
  const reply = await fetch('/api/local-users', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });
  if (!reply.ok) throw Error(reply.status);
  return reply.json();
}

function clearHandout() {
  credentials.textContent = '';
  handout.hidden = true;
}

function controls() {
  people.disabled = busy || people.options.length < 2;
  add.disabled = people.disabled || !people.value;
  for (const button of users.querySelectorAll('button')) button.disabled = busy;
}

function button(label, run) {
  const result = document.createElement('button');
  result.type = 'button';
  result.textContent = label;
  result.onclick = run;
  return result;
}

async function refresh() {
  const {users: accounts, eligible} = await request({action: 'list'});
  people.replaceChildren(new Option(eligible.length ? 'Выберите человека' : 'У всех доступных людей уже есть вход', ''));
  for (const p of eligible.sort((a, b) => a.name.localeCompare(b.name))) people.add(new Option(p.name, p.id));
  users.replaceChildren();
  for (const user of accounts.sort((a, b) => (a.name || a.username).localeCompare(b.name || b.username))) {
    const row = document.createElement('li');
    const name = document.createElement('strong');
    const details = document.createElement('small');
    name.textContent = user.name || user.username;
    const role = {reader: 'читатель', owner: 'хозяин'}[user.role] || user.role;
    const signIn = {CONFIRMED: 'пароль сменён', FORCE_CHANGE_PASSWORD: 'ждёт смены пароля'}[user.status] || 'вход не определён';
    details.textContent = [user.username, role, user.enabled ? signIn : 'вход выключен'].filter(Boolean).join(' · ');
    row.append(name, details);
    if (user.role === 'reader' && user.enabled) {
      row.append(button('Выдать новый пароль', () => run({action: 'reset', username: user.username})),
        button('Выключить вход', () => run({action: 'disable', username: user.username})));
    }
    users.append(row);
  }
}

async function run(body) {
  if (busy) return;
  if (body) clearHandout();
  busy = true;
  controls();
  status.textContent = body ? 'Сохраняем…' : 'Загружаем входы…';
  try {
    if (body) {
      const result = await request(body);
      if (result.password) {
        credentials.textContent = 'Логин: ' + result.username + '\nНачальный пароль: ' + result.password;
        handout.hidden = false;
      }
    }
    await refresh();
    status.textContent = !body && !users.children.length ? 'Пока входов нет.' :
      body?.action === 'disable' ? 'Вход выключен.' : '';
  } catch {
    status.textContent = 'Не удалось обновить входы. Перезагрузите страницу перед повтором.';
  } finally {
    busy = false;
    controls();
  }
}

people.onchange = controls;
$('add').onclick = () => run({action: 'add', person: people.value});
$('copy').onclick = async () => {
  try {
    await navigator.clipboard.writeText(credentials.textContent);
    clearHandout();
    status.textContent = 'Логин и пароль скопированы.';
  } catch {
    status.textContent = 'Выделите логин и пароль и скопируйте вручную.';
  }
};
$('dismiss').onclick = clearHandout;
window.addEventListener('pagehide', clearHandout);
run();
