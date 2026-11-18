/*
START_MODULE_CONTRACT: MOD-DESK-CLIENT
PURPOSE: Give every narrator screen one literal feedback path, located receipts and a quiet lower entry.
PRD_REF: docs/PRD.md#FAMILY-DESK
INVARIANTS:
- feedback is never inserted into the tree and closing or failed delivery retains the draft [review: engine lead]
- the browser hashes every message before CloudFront signs it and remembers only its own receipts [review: engine lead]
- click alone opens the common sheet without scrolling; dismissal retains and advertises drafts [review: browser walk]
- one lower navigation updates its active reader route on every screen [review: browser walk]
CHANGES_WITH:
- MOD-DESK-AWS-TEMPLATE (body digest and extensible envelope)
- MOD-DESK-FEEDBACK (read and addressed receipt fields)
- MOD-DESK-TREE-ADD (shared sender and receipt history)
:END_MODULE_CONTRACT
*/
(async function () {
  if (window.familiarDesk) return;
  window.familiarDesk = true;
  const identity = await window.familiarDeskIdentity;
  const config = await (await fetch('/desk/words.json')).json();
  const words = () => config.languages?.[document.documentElement.lang] || config;
  const el = (tag, cls, text) => {
    const n = document.createElement(tag); if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text; return n;
  };
  const key = 'familiar-feedback:' + config.family_id + (identity ? ':' + identity.sub : '');
  const read = (name, fallback) => { try { return JSON.parse(localStorage.getItem(key + name)) || fallback; } catch { return fallback; } };
  const save = (name, value) => { try { localStorage.setItem(key + name, JSON.stringify(value)); } catch { /* received messages remain in the inbox */ } };
  let mine = read(':mine', []), drafts = read(':drafts', {}), receipts = {};
  const nav = document.querySelector('#desk-nav');
  let activeLink = '';
  const entry = el('button', '', words().remark); entry.type = 'button';
  entry.setAttribute('aria-controls', 'desk-feedback'); entry.setAttribute('aria-expanded', 'false');
  document.querySelector('#desk-feedback-entry').append(entry);
  const dialog = el('dialog'); dialog.id = 'desk-feedback'; dialog.setAttribute('aria-labelledby', 'desk-feedback-title');
  const form = el('form'), heading = el('h2'), where = el('p', 'desk-feedback-where'); heading.id = 'desk-feedback-title';
  // dialog.show() focuses this fixed sheet; the textarea then uses preventScroll.
  dialog.tabIndex = -1; dialog.autofocus = true;
  const label = el('label'), area = el('textarea'); area.required = true; area.maxLength = 6000; area.rows = 3;
  label.append(area);
  const status = el('p'); status.setAttribute('role', 'status');
  const send = el('button'), close = el('button'); send.type = 'submit'; close.type = 'button';
  const myTitle = el('h3'), history = el('div', 'desk-feedback-history'); history.setAttribute('aria-live', 'polite');
  // A new person has its own form; the remark sheet only points to it.
  const addHint = el('p', 'desk-feedback-add'), addLink = el('button'); addLink.type = 'button';
  addHint.append(el('span'), addLink);
  addLink.onclick = () => { const person = context.person; hide(); window.familiarDeskAddPerson?.(person); };
  form.append(heading, where, addHint, label, status, send, close); dialog.append(form, myTitle, history); document.body.append(dialog);
  let context = {}, draftKey = '', pending = null;
  const fmt = (text, values) => Object.entries(values).reduce((s, [k, v]) => s.replaceAll('{' + k + '}', v), text);
  function locate(details = {}) {
    const w = words(), shell = document.querySelector('[data-feedback-screen]');
    const feed = document.querySelector('.feed-viewer'), panel = document.querySelector('.panel');
    const cardOpen = panel && (!matchMedia('(max-width:800px)').matches || panel.classList.contains('open'));
    const screen = feed ? 'feed' : shell?.dataset.feedbackScreen || (location.pathname.includes('progress') || location.pathname.includes('questions') ? 'progress' : 'page');
    const data = {page: location.pathname + location.search + location.hash, screen,
      language: document.documentElement.lang, person: screen === 'tree' && cardOpen ? panel.dataset.feedbackPerson || '' : '',
      feed: feed?.dataset.feedbackFeed || '', step: feed?.dataset.feedbackStep || '', text_mode: feed?.dataset.feedbackTextMode || '',
      selection: String(getSelection() || '').slice(0, 300), viewport: innerWidth + 'x' + innerHeight,
      engine_version: config.engine_version, build: config.build, ...details};
    const person = document.querySelector(`.panel[data-feedback-person="${CSS.escape(data.person || '')}"]`)?.dataset.feedbackPersonLabel || data.person;
    data.where = data.feed ? fmt(w.where_feed, {feed: feed?.dataset.feedbackFeedLabel || data.feed, step: data.step,
      mode: data.text_mode === 'kids' ? w.kids_text : w.full_text})
      : data.person ? fmt(w.where_person, {person}) : w['screen_' + screen] || document.title;
    if (data.question) data.where += ' · ' + (data.finding || data.question);
    return data;
  }
  function renderHistory() {
    const w = words(); myTitle.textContent = w.my_remarks; history.replaceChildren();
    if (!mine.length) history.append(el('p', '', w.no_remarks));
    for (const item of mine.slice(-20).reverse()) {
      const mark = receipts[item.id] || item.receipt || {status: 'sent'}, row = el('article');
      row.append(el('small', '', item.where || item.page), el('p', '', item.text),
        el('small', 'desk-receipt-state', w['status_' + mark.status] || w.status_sent));
      if (mark.reply) row.append(el('p', 'desk-feedback-reply', w.researcher_reply + ': ' + mark.reply));
      history.append(row);
    }
  }
  async function refreshHistory() {
    try {
      if (identity?.role !== 'reader') {
        const r = await fetch('/desk/feedback.json', {cache: 'no-store'});
        if (r.ok) receipts = {...receipts, ...await r.json()};
      }
      // Cloud receipts are a build projection; loopback adds live read marks.
      for (let start = 0; start < mine.length; start += 30) {
        const ids = mine.slice(start, start + 30).map(x => x.id).join(',');
        const r = await fetch('/api/feedback?ids=' + encodeURIComponent(ids), {cache: 'no-store'});
        if (r.ok) for (const row of (await r.json()).items || []) {
          if (row.status) receipts[row.id] = {status: row.status, reply: row.reply || ''};
        }
      }
      for (const item of mine) if (receipts[item.id]) item.receipt = receipts[item.id];
      save(':mine', mine);
    } catch { /* previous receipts and successful local sends still show */ }
    renderHistory();
  }
  function remember(item) {
    if (!mine.some(x => x.id === item.id)) mine.push(item);
    save(':mine', mine); renderHistory();
    document.dispatchEvent(new CustomEvent('familiar-feedback-received', {detail: item}));
  }
  window.familiarDeskSend = async details => {
    const item = {kind: 'remark', ...locate(details), id: crypto.randomUUID(), client_time: new Date().toISOString(), ...details};
    const body = JSON.stringify(item), digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(body));
    const hash = Array.from(new Uint8Array(digest), x => x.toString(16).padStart(2, '0')).join('');
    const response = await fetch('/api/feedback', {method: 'POST', credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-Amz-Content-Sha256': hash}, body});
    if (!response.ok) throw new Error(words().failed);
    const acknowledgement = await response.json();
    if (acknowledgement.id !== item.id) throw new Error(words().failed);
    remember(item); return item;
  };
  function keepDraft() {
    if (draftKey) { drafts[draftKey] = {text: area.value, pending, context}; save(':drafts', drafts); }
    if (area.value.trim()) save(':active-draft', draftKey);
    update();
  }
  function hide() { keepDraft(); dialog.close(); entry.setAttribute('aria-expanded', 'false'); }
  function placeSheet() {
    const feed = document.querySelector('.feed-viewer');
    const head = document.querySelector(feed ? '.feed-head' : '.page-top,.shell .top');
    const bar = feed ? document.querySelector('.feed-foot') : [...document.querySelectorAll('#desk-footer')]
      .find(node => node.getBoundingClientRect().height > 0 && getComputedStyle(node).display !== 'none');
    dialog.style.setProperty('--feedback-bottom', Math.max(34, bar ? innerHeight - bar.getBoundingClientRect().top + 8 : 34) + 'px');
    dialog.style.setProperty('--feedback-top', Math.max(8, head ? head.getBoundingClientRect().bottom + 8 : 8) + 'px');
  }
  function open(details = {}, resume = false) {
    if (send.disabled) return;
    if (dialog.open) keepDraft();
    const w = words(), next = locate(details);
    const saved = read(':active-draft', '');
    const latest = drafts[saved]?.text?.trim() ? saved : Object.keys(drafts).reverse().find(key => drafts[key].text?.trim());
    draftKey = resume && drafts[latest]?.text?.trim() ? latest
      : JSON.stringify([next.page, next.person, next.question, details.kind || 'remark']);
    const draft = drafts[draftKey]; context = draft?.text ? draft.context : next;
    pending = draft?.pending || null; area.value = draft?.text || '';
    heading.textContent = context.kind === 'name_person' ? w.name_person : context.kind === 'correction' ? w.correct : context.question ? w.answer : w.remark;
    where.textContent = w.attached_to + ': ' + context.where;
    addHint.hidden = !window.familiarDeskAddPerson || !['tree', 'person'].includes(context.screen);
    addHint.firstChild.textContent = w.add_elsewhere + ' '; addLink.textContent = w.add_relative;
    if (label.firstChild?.nodeType === Node.TEXT_NODE) label.firstChild.remove();
    label.prepend(document.createTextNode(w.feedback_label));
    send.textContent = w.send; close.textContent = w.close; status.textContent = '';
    placeSheet(); if (!dialog.open) dialog.show(); entry.setAttribute('aria-expanded', 'true'); refreshHistory();
    area.focus({preventScroll: true});
  }
  window.familiarDeskOpen = details => open(details);
  document.addEventListener('familiar-feedback-open', event => open(event.detail));
  entry.onclick = () => { if (dialog.open) hide(); else open({}, true); };
  close.onclick = hide;
  dialog.addEventListener('keydown', event => { if (['ArrowLeft', 'ArrowRight', ' '].includes(event.key)) event.stopPropagation(); });
  document.addEventListener('keydown', event => {
    if (dialog.open && event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); hide(); entry.focus({preventScroll: true}); }
  }, true);
  document.addEventListener('pointerdown', event => { if (dialog.open && !dialog.contains(event.target) && event.target !== entry) hide(); });
  area.oninput = () => { pending = null; keepDraft(); };
  form.onsubmit = async event => {
    event.preventDefault(); if (!area.value.trim() || send.disabled) return;
    send.disabled = true; status.textContent = words().sending; pending ||= crypto.randomUUID(); keepDraft();
    try {
      await window.familiarDeskSend({...context, kind: context.kind || 'remark', id: pending, text: area.value});
      area.value = ''; pending = null; keepDraft(); status.textContent = words().received;
    } catch (error) { status.textContent = error.message || words().failed; }
    finally { send.disabled = false; }
  };
  for (const answer of document.querySelectorAll('.desk-answer')) {
    answer.onsubmit = async event => {
      event.preventDefault(); const input = answer.querySelector('textarea'), result = answer.querySelector('[role=status]');
      const button = answer.querySelector('button[type=submit]'); if (!input.value.trim()) return;
      button.disabled = true; result.textContent = words().sending; answer.dataset.pending ||= crypto.randomUUID();
      try {
        await window.familiarDeskSend({...locate({kind: 'answer', question: answer.dataset.question}), text: input.value, id: answer.dataset.pending});
        input.value = ''; delete answer.dataset.pending; result.textContent = words().received;
      } catch (error) { result.textContent = error.message || words().failed; }
      finally { button.disabled = false; }
    };
    answer.querySelector('textarea').oninput = () => { delete answer.dataset.pending; };
  }
  function update() {
    // Avoid mutations when unchanged: the reader observer also watches child text.
    const hasDraft = Object.values(drafts).some(draft => draft.text?.trim());
    const label = words().remark + (hasDraft ? ' · ' + words().unsent_draft : '');
    if (entry.textContent !== label) entry.textContent = label;
    entry.title = label; entry.dataset.draft = String(hasDraft);
    const notice = document.querySelector('#desk-notice');
    const privateLabel = notice?.querySelector('.desk-private-label');
    if (privateLabel && privateLabel.textContent !== words().private_notice) privateLabel.textContent = words().private_notice;
    const route = new URLSearchParams(location.hash.slice(1));
    const view = route.has('feed') ? 'stories' : route.has('person') ? 'tree' : route.get('view') || 'tree';
    for (const link of nav.children) {
      const label = words()[link.dataset.deskLabel];
      if (label !== undefined && link.textContent !== label) link.textContent = label;
      const active = link.pathname === '/' ? location.pathname === '/' && link.hash === '#view=' + view
        : location.pathname === link.pathname || location.pathname === '/desk/questions.html' && link.pathname === '/desk/progress.html';
      if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
      if (active && activeLink !== link.href) {
        activeLink = link.href;
        const bar = nav.getBoundingClientRect(), item = link.getBoundingClientRect();
        // Reveal the current link inside the narrow row, without scrolling the page.
        nav.scrollLeft += item.left < bar.left ? item.left - bar.left : Math.max(0, item.right - bar.right);
      }
    }
  }
  new MutationObserver(update).observe(document.querySelector('#root') || nav, {childList: true, subtree: true});
  new MutationObserver(update).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
  update(); document.dispatchEvent(new Event('familiar-desk-ready'));
  document.fonts.ready.then(() => { activeLink = ''; update(); });
  window.addEventListener('hashchange', update);
  window.addEventListener('pagehide', keepDraft);
  window.addEventListener('focus', () => { if (dialog.open) refreshHistory(); });
  window.addEventListener('resize', () => { activeLink = ''; update(); if (dialog.open) placeSheet(); });
})();
