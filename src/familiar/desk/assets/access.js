(() => {
  const el = id => document.getElementById(id);
  const status = (text, error = false) => { el('access-status').textContent = text; el('access-status').dataset.error = error; };
  let people = [], selected = null, busy = false;
  const api = async data => {
    const body = data ? JSON.stringify(data) : null;
    const digest = body && await crypto.subtle.digest('SHA-256', new TextEncoder().encode(body));
    const hash = digest && [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2,'0')).join('');
    const response = await fetch('/api/access', {cache:'no-store', ...(data ? {
      method:'POST', headers:{'Content-Type':'application/json','X-Amz-Content-Sha256':hash}, body
    } : {})});
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw Error(response.status === 403 ? 'Эта страница доступна только хозяину. Войдите снова.' :
      result.error === 'username_exists' ? 'Этот логин уже занят. Выберите другой.' :
      'Действие не завершено. Обновите список и проверьте вход перед повтором.');
    return result;
  };
  const latin = name => {
    const letters = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя';
    const values = ['a','b','v','g','d','e','e','zh','z','i','i','k','l','m','n','o','p','r','s','t','u','f','kh','ts','ch','sh','shch','','y','','e','yu','ya'];
    return [...name.toLowerCase()].map(c => letters.includes(c) ? values[letters.indexOf(c)] : c)
      .join('').replaceAll('ł','l').normalize('NFKD').replace(/[\u0300-\u036f]/g,'')
      .replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,40) || 'relative';
  };
  const button = (label, action) => { const b = document.createElement('button'); b.type='button'; b.textContent=label; b.onclick=action; return b; };
  function search() {
    selected = null; el('access-person').textContent = 'Выберите человека из результатов поиска.';
    const query = el('access-search').value.trim().toLocaleLowerCase();
    el('access-matches').replaceChildren();
    if (!query) return;
    const matches = people.filter(p => p.name.toLocaleLowerCase().includes(query));
    for (const person of matches.slice(0,30)) el('access-matches').append(button(person.name, () => {
      selected = person; el('access-search').value = person.name;
      el('access-person').textContent = 'Выбран: ' + person.name;
      el('access-username').value = latin(person.name); el('access-matches').replaceChildren();
    }));
    if (!matches.length) el('access-matches').textContent = 'Никого не нашли. Попробуйте часть имени.';
    else if (matches.length > 30) el('access-matches').append('Уточните имя, чтобы увидеть остальные результаты.');
  }
  function handout(data) {
    el('access-password-user').textContent = 'Логин: ' + data.username;
    el('access-password-value').value = data.temporary_password;
    data.temporary_password = ''; el('access-copy-status').textContent = '';
    el('access-password').showModal();
  }
  function forget() { el('access-password-value').value=''; el('access-password-user').textContent=''; el('access-copy-status').textContent=''; }
  el('access-password').addEventListener('close',forget);
  el('access-close').onclick = () => { forget(); el('access-password').close(); };
  el('access-copy').onclick = async () => {
    try { await navigator.clipboard.writeText(el('access-password-value').value); el('access-copy-status').textContent='Скопировано. Передайте лично.'; }
    catch (_) { el('access-password-value').select(); el('access-copy-status').textContent='Выделено — скопируйте вручную.'; }
  };
  window.addEventListener('pagehide',forget);
  window.addEventListener('pageshow',event => { if(event.persisted) { forget(); el('access-password').close(); } });
  const confirm = text => new Promise(resolve => {
    el('access-confirm-text').textContent=text; el('access-confirm').returnValue='cancel';
    el('access-confirm').addEventListener('close',() => resolve(el('access-confirm').returnValue==='confirm'),{once:true});
    el('access-confirm').showModal();
  });
  async function change(data) {
    if (busy) return;
    busy=true; document.querySelectorAll('#access-controls button').forEach(b => b.disabled=true);
    try {
      const result=await api(data);
      if (result.temporary_password) handout(result);
      await refresh();
      status('Готово. Изменение доступа может занять несколько секунд.');
      if (data.action==='add') { el('access-add').reset(); search(); }
    } catch (error) { status(error.message,true); }
    finally { busy=false; document.querySelectorAll('#access-controls button').forEach(b => b.disabled=false); }
  }
  async function refresh() {
    const data=await api(); people=data.people; el('access-users').replaceChildren();
    for (const user of data.users) {
      const row=document.createElement('article'); row.className='access-user';
      const heading=document.createElement('h3'); heading.textContent=user.username + (user.self ? ' · ваш вход' : '');
      const details=document.createElement('p');
      details.textContent=(people.find(p => p.id===user.person)?.name || 'Без привязки к человеку дерева') + ' · ' +
        (user.role==='owner' ? 'Хозяин' : 'Родной') + ' · ' + (user.enabled ? 'Включён' : 'Отключён');
      row.append(heading,details);
      if (!user.self) {
        const actions=document.createElement('div'); actions.className='access-actions';
        for (const [action,label] of [['reset','Сбросить пароль'],[user.enabled?'disable':'enable',user.enabled?'Отключить':'Включить'],['remove','Удалить']])
          actions.append(button(label,async () => {
            if (busy) return;
            const detail=action==='remove' ? ' Вход будет удалён. Уже полученные копии семейных страниц останутся у родного.' :
              action==='reset'||action==='disable' ? ' Прежние сессии будут отозваны.' : ' Потребуется новый вход; прежние сессии останутся отозванными.';
            if (await confirm(label + ' — ' + user.username + '?' + detail)) await change({action,username:user.username});
          }));
        row.append(actions);
      }
      el('access-users').append(row);
    }
  }
  el('access-search').addEventListener('input',search);
  // Keep the selected graph identity separate from the editable search text.
  el('access-add').onsubmit = event => {
    event.preventDefault(); if (!selected) return status('Выберите человека из результатов поиска.',true);
    change({...Object.fromEntries(new FormData(event.target)),action:'add',person:selected.id});
  };
  window.familiarDeskIdentity.then(async user => {
    if(user?.role!=='owner') { status('Эта страница доступна только хозяину.',true); return; }
    try { await refresh(); el('access-controls').hidden=false; status('Управляйте входами. Ваш собственный вход защищён от изменений на этой странице.'); }
    catch(error) { status(error.message,true); }
  });
})();
