/*
START_MODULE_CONTRACT: MOD-DESK-CLIENT
PURPOSE: Give every narrator screen one literal feedback path, located receipts and a quiet lower entry.
PRD_REF: docs/PRD.md#FAMILY-DESK
INVARIANTS:
- feedback is never inserted into the tree and closing or failed delivery retains the draft [review: engine lead]
- the browser hashes every message before CloudFront signs it and remembers only its own receipts [review: engine lead]
- click alone opens the common sheet without scrolling; dismissal retains and advertises drafts [review: browser walk]
- one lower row and one quieter list behind the page top update their words and active route on every screen [review: browser walk]
- words are acknowledged before pictures start; unfinished pictures stay in the tray and can be selected again from the same receipt [review: browser walk]
CHANGES_WITH:
- MOD-DESK-AWS-TEMPLATE (body digest and extensible envelope)
- MOD-DESK-FEEDBACK (read and addressed receipt fields)
- MOD-DESK-TREE-ADD (shared sender and receipt history)
- MOD-DESK-ATTACHMENTS (upload slots, refusal reasons, limits in words.json)
:END_MODULE_CONTRACT
*/
(async function () {
  if (window.familiarDesk) return;
  window.familiarDesk = true;
  const identity = await window.familiarDeskIdentity;
  const config = await (await fetch('/desk/words.json')).json();
  const words = () => config.languages?.[document.documentElement.lang] || config;
  // A desk page exists in the source language and in each reader language that has its translation.
  const localPage = (page, lang = document.documentElement.lang) =>
    lang !== config.source_language && (config.page_languages?.[page] || []).includes(lang)
      ? `/desk/${page}.${lang}.html` : `/desk/${page}.html`;
  const chosenLanguage = () => {
    const prefix = 'familiar:' + encodeURIComponent(config.family_id) + ':';
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const name = localStorage.key(i);
        if (name.startsWith(prefix) && name.endsWith(':family-language')) return localStorage.getItem(name);
      }
    } catch { /* storage closed: the page keeps its own language */ }
    return '';
  };
  const el = (tag, cls, text) => {
    const n = document.createElement(tag); if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text; return n;
  };
  const key = 'familiar-feedback:' + config.family_id + (identity ? ':' + identity.sub : '');
  const read = (name, fallback) => { try { return JSON.parse(localStorage.getItem(key + name)) || fallback; } catch { return fallback; } };
  const save = (name, value) => { try { localStorage.setItem(key + name, JSON.stringify(value)); } catch { /* received messages remain in the inbox */ } };
  let mine = read(':mine', []), drafts = read(':drafts', {}), receipts = {};
  const waiting = read(':files-waiting', {});
  const saveWaiting = () => save(':files-waiting', waiting);
  // Pictures and scans travel with the words: camera or gallery on a phone, files or a drop on a computer.
  // Only a signed-in relative (personal desk) or the host on loopback can send them.
  const canAttach = (!!identity || /^(127\.0\.0\.1|localhost|.+\.localhost)$/.test(location.hostname))
    && !document.querySelector('meta[name="familiar-static-demo"]');
  const limits = config.attach_limits || {};
  const CLIP = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M20.5 11.2l-8.3 8.3a5 5 0 0 1-7.1-7.1l8.3-8.3a3.3 3.3 0 0 1 4.7 4.7l-8.3 8.3a1.7 1.7 0 0 1-2.4-2.4l7.6-7.6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  function attacher(host, changed = () => {}) {
    const box = {list: []}, tray = el('div', 'desk-attach'), input = el('input'), add = el('button', 'desk-attach-add');
    const fileReceipts = new WeakMap();
    input.type = 'file'; input.multiple = true; input.hidden = true;
    input.accept = 'image/*,.heic,.heif,application/pdf,.pdf';
    add.type = 'button'; add.innerHTML = CLIP; tray.append(add, input); tray.hidden = !canAttach; host.append(tray);
    box.render = () => {
      add.title = words().attach || ''; add.setAttribute('aria-label', add.title);
      tray.querySelectorAll('figure').forEach(node => node.remove());
      box.list.forEach((item, index) => {
        const figure = el('figure', 'desk-thumb'), image = el('img'), remove = el('button', 'desk-thumb-remove', '×');
        figure.dataset.state = item.state || ''; figure.style.setProperty('--sent', item.sent || 0);
        figure.dataset.kind = (item.file.name.split('.').pop() || '').slice(0, 4).toUpperCase();
        image.alt = ''; image.src = item.url; image.onerror = () => image.remove();
        remove.type = 'button'; remove.disabled = !!box.busy;
        remove.setAttribute('aria-label', (words().attach_remove || '×') + ': ' + item.file.name);
        remove.onclick = () => { removeFile(index); box.render(); changed(); };
        figure.append(image, remove); add.before(figure);
      });
    };
    function removeFile(index) {
      const [item] = box.list.splice(index, 1);
      URL.revokeObjectURL(item.url);
      if (!box.list.length) fileReceipts.delete(box.list);
    }
    box.put = files => {
      if (box.busy) return;
      for (const file of files) if (box.list.length < (limits.message_files || 10)) box.list.push({file, url: URL.createObjectURL(file)});
      box.render(); changed();
    };
    box.use = list => { box.list = list; box.render(); };
    box.lock = busy => { box.busy = add.disabled = busy; box.render(); };
    box.mark = (n, state, sent = 0) => { const item = box.list[n - 1]; if (item) { item.state = state; item.sent = sent; } box.render(); };
    box.send = async (details, acknowledged) => {
      const receipt = fileReceipts.get(box.list);
      try {
        const item = await sendFeedback(details, box.list.map(item => item.file), box.mark, acknowledged, receipt);
        if (item.uploadNotice && !receipt) fileReceipts.set(box.list, waiting[item.id].item);
        return item;
      } finally {
        for (let i = box.list.length - 1; i >= 0; i--) if (box.list[i].state === 'sent') removeFile(i);
        box.render(); changed();
      }
    };
    add.onclick = () => input.click();
    input.onchange = () => { box.put(input.files); input.value = ''; };
    for (const name of ['dragover', 'drop']) host.addEventListener(name, event => {
      if (!canAttach || !event.dataTransfer?.types?.includes('Files')) return;
      event.preventDefault(); if (name === 'drop') box.put(event.dataTransfer.files);
    });
    box.render();
    return box;
  }
  window.familiarDeskAttach = attacher;
  const refusal = (body, n = 0) => {
    const w = words(), error = new Error(fmt(w[body?.error] || w.file_failed || w.failed,
      {mb: Math.round((limits.file_bytes || 0) / 1048576), count: limits.message_files || ''}));
    error.file = body?.file || n; return error;
  };
  const hex = buffer => Array.from(new Uint8Array(buffer), x => x.toString(16).padStart(2, '0')).join('');
  const bodyHash = async body => hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(body)));
  const request = async (path, options, timeout) => {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(path, {...options, credentials: 'same-origin', signal: controller.signal});
      return {ok: response.ok, body: await response.json().catch(() => null)};
    } finally { clearTimeout(timer); }
  };
  const post = async (path, value, timeout = 45000, keepalive = false) => {
    const body = JSON.stringify(value);
    return request(path, {method: 'POST', body, keepalive,
      headers: {'Content-Type': 'application/json', 'X-Amz-Content-Sha256': await bodyHash(body)}}, timeout);
  };
  async function carry(slot, blob, progress) {
    const hash = hex(await crypto.subtle.digest('SHA-256', await blob.arrayBuffer()));
    return new Promise(resolve => {
      const xhr = new XMLHttpRequest();
      xhr.open('PUT', slot.url); xhr.timeout = 5 * 60 * 1000;
      xhr.setRequestHeader('Content-Type', 'application/octet-stream');
      xhr.setRequestHeader('X-Amz-Content-Sha256', hash);
      let idle, loaded = 0;
      const watch = () => { clearTimeout(idle); idle = setTimeout(() => xhr.abort(), 45000); };
      xhr.onloadstart = watch;
      xhr.upload.onprogress = event => {
        if (event.loaded <= loaded) return;
        loaded = event.loaded; watch(); progress(loaded);
      };
      xhr.onload = () => {
        let body = null; try { body = JSON.parse(xhr.responseText); } catch { /* failed connection */ }
        resolve({ok: xhr.status >= 200 && xhr.status < 300, body});
      };
      xhr.onerror = xhr.ontimeout = xhr.onabort = () => resolve({ok: false, network: true});
      xhr.onloadend = () => clearTimeout(idle);
      xhr.send(blob);
    });
  }
  const digests = new WeakMap();
  async function upload(item, file, progress) {
    if (file.size > limits.file_bytes) throw refusal({error: 'file_large'});
    if (!digests.has(file)) digests.set(file, hex(await crypto.subtle.digest('SHA-256', await file.arrayBuffer())));
    const head = btoa(String.fromCharCode(...new Uint8Array(await file.slice(0, 64).arrayBuffer())));
    const declared = {n: 1, size: file.size, sha256: digests.get(file), name: file.name};
    const {ok, body: answer} = await post('/api/feedback/files', {id: item.id, single: true, files: [{...declared, head}]});
    if (!ok || !answer) throw refusal(answer);
    if (answer.accepted) return declared;
    const bytes = limits.single_part_bytes || 1048576, parts = answer.uploads;
    const size = slot => Math.min(bytes, file.size - slot.part * bytes);
    let received = file.size - parts.reduce((sum, slot) => sum + size(slot), 0);
    for (const slot of parts) {
      const offset = slot.part * bytes;
      progress('sending', received / file.size);
      const sent = await carry(slot, file.slice(offset, offset + size(slot)),
        loaded => progress('sending', (received + loaded) / file.size));
      if (!sent.ok) throw Object.assign(refusal(sent.body), {network: sent.network});
      received += size(slot);
    }
    const committed = await post('/api/feedback', {...item, files: [declared], file_upload: true}, 65000);
    if (!committed.ok || committed.body?.id !== item.id) throw refusal(committed.body);
    return declared;
  }
  const nav = document.querySelector('#desk-nav');
  const more = document.querySelector('#desk-more');
  const entry = el('button', '', words().remark); entry.type = 'button';
  entry.setAttribute('aria-controls', 'desk-feedback'); entry.setAttribute('aria-expanded', 'false');
  document.querySelector('#desk-feedback-entry').append(entry);
  // On a phone the same entry is the first line of the quieter list, so the lower row keeps its four places.
  const second = el('button', 'desk-more-remark', words().remark_write || words().remark); second.type = 'button';
  second.onclick = () => open({}, true); more?.prepend(second);
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
  const tray = el('div');
  form.append(heading, where, addHint, label, tray, status, send, close); dialog.append(form, myTitle, history); document.body.append(dialog);
  // Each draft keeps its own pictures while the page is open; a picture alone is a whole remark.
  const attached = {}, sheetFiles = attacher(tray, () => { area.required = !sheetFiles.list.length; update(); });
  let context = {}, draftKey = '', pending = null;
  const fmt = (text, values) => Object.entries(values).reduce((s, [k, v]) => s.replaceAll('{' + k + '}', v), text);
  function locate({prefill, ...details} = {}) {
    const w = words(), shell = document.querySelector('[data-feedback-screen]');
    const feed = document.querySelector('.feed-viewer'), panel = document.querySelector('.panel');
    const cardOpen = panel && (!matchMedia('(max-width:800px)').matches || panel.classList.contains('open'));
    const screen = feed ? 'feed' : shell?.dataset.feedbackScreen || (location.pathname.includes('progress') ? 'progress' : 'page');
    const data = {page: location.pathname + location.search + location.hash, screen,
      language: document.documentElement.lang, person: screen === 'tree' && cardOpen ? panel.dataset.feedbackPerson || '' : '',
      feed: feed?.dataset.feedbackFeed || '', step: feed?.dataset.feedbackStep || '', text_mode: feed?.dataset.feedbackTextMode || '',
      selection: String(getSelection() || '').slice(0, 300), viewport: innerWidth + 'x' + innerHeight,
      engine_version: config.engine_version, build: config.build, ...details};
    const person = document.querySelector(`.panel[data-feedback-person="${CSS.escape(data.person || '')}"]`)?.dataset.feedbackPersonLabel || data.person;
    data.where = data.feed ? fmt(w.where_feed, {feed: feed?.dataset.feedbackFeedLabel || data.feed, step: data.step,
      mode: data.text_mode === 'kids' ? w.kids_text : w.full_text})
      : data.person ? fmt(w.where_person, {person}) : w['screen_' + screen] || document.title;
    if (data.question || /^(blank|amendment):/.test(data.subject || '')) data.where += ' · ' + (data.finding || data.question);
    return data;
  }
  function renderHistory() {
    const w = words(); myTitle.textContent = w.my_remarks; history.replaceChildren();
    const recent = mine.filter(item => !waiting[item.id]).slice(-20).reverse();
    const pending = Object.values(waiting).map(row => mine.find(item => item.id === row.item.id) || row.item).reverse();
    if (!recent.length && !pending.length) history.append(el('p', '', w.no_remarks));
    for (const item of [...pending, ...recent]) {
      const queued = waiting[item.id];
      const mark = receipts[item.id] || item.receipt || {status: 'sent'}, row = el('article');
      row.append(el('small', '', item.where || item.page));
      if (item.text) row.append(el('p', '', item.text));
      if (!queued || queued.received) row.append(el('small', 'desk-receipt-state',
        (item.files?.length ? '📎 ' + item.files.length + ' · ' : '') + (w['status_' + mark.status] || w.status_sent)));
      if (mark.reply) row.append(el('p', 'desk-feedback-reply', w.researcher_reply + ': ' + mark.reply));
      if (queued) {
        const input = el('input'), retry = el('button', '', w.files_retry);
        input.type = 'file'; input.multiple = true; input.hidden = true;
        input.accept = 'image/*,.heic,.heif,application/pdf,.pdf';
        retry.type = 'button'; retry.disabled = fileSends.has(item.id);
        retry.onclick = () => input.click();
        input.onchange = () => { if (input.files.length) sendFiles(queued.item, [...input.files], queued.received); };
        row.append(el('p', '', retry.disabled ? w.files_sending : filesNotice(queued.names)), retry, input);
      }
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
    if (!['ask_answer', 'ask_state'].includes(item.kind) && !mine.some(x => x.id === item.id)) {
      mine.push({...item}); save(':mine', mine); renderHistory();
    }
    document.dispatchEvent(new CustomEvent('familiar-feedback-received', {detail: item}));
  }
  const fileSends = new Set();
  const filesNotice = (names, reason = '') => fmt(words().files_pending, {names: names.join(', ')}) + (reason ? ' ' + reason : '');
  const retryContext = (item, received) => {
    if (received && item.kind === 'ask_answer') return {...item, text: '', wants: {}};
    return item;
  };
  async function sendFiles(item, files, received, progress = () => {}) {
    if (fileSends.has(item.id)) return {received, notice: words().files_sending};
    fileSends.add(item.id);
    const names = files.map(file => file.name);
    const row = {item: retryContext(item, received), names, received};
    waiting[item.id] = row; saveWaiting(); renderHistory();
    let reason = '';
    try {
      for (const [index, file] of files.entries()) {
        try {
          const sent = await upload(item, file, (state, part) => progress(index + 1, state, part));
          if (!row.received) { row.received = true; remember(item); }
          const entry = mine.find(x => x.id === item.id);
          if (entry && !entry.files?.some(x => x.sha256 === sent.sha256)) {
            (entry.files ||= []).push(sent); save(':mine', mine);
          }
          names.splice(names.indexOf(file.name), 1);
          saveWaiting(); progress(index + 1, 'sent', 1);
        } catch (error) {
          progress(index + 1, 'refused');
          reason = error.message && 'file' in error ? error.message : words().file_failed;
          if (error.network || error.name === 'AbortError' || error.name === 'TypeError') break;
        }
      }
    } finally {
      if (!names.length) delete waiting[item.id];
      fileSends.delete(item.id); saveWaiting(); renderHistory(); update();
    }
    return {received: row.received, notice: names.length ? filesNotice(names, reason) : ''};
  }
  async function sendFeedback(details, files = [], progress, acknowledged = () => {}, fileReceipt) {
    const item = {kind: 'remark', ...locate(details), id: crypto.randomUUID(), client_time: new Date().toISOString(), ...details};
    let received = false;
    if (!files.length || item.text.trim()) {
      const answer = await post('/api/feedback', item, 45000, true).catch(() => null);
      if (!answer?.ok || answer.body?.id !== item.id) throw new Error(words().failed);
      if (answer.body.duplicate && typeof answer.body.text === 'string' && answer.body.text !== item.text) {
        item.text = answer.body.text; remember(item);
        return {...item, deliveryNotice: words().original_sent};
      }
      received = true; remember(item);
      acknowledged(files.length);
    }
    if (files.length) {
      const result = await sendFiles(fileReceipt || item, files, !!fileReceipt || received, progress);
      if (!result.received) throw new Error(result.notice || words().failed);
      item.uploadNotice = result.notice;
    }
    return item;
  }
  window.familiarDeskSend = sendFeedback;
  const hasDraft = key => drafts[key]?.text?.trim() || attached[key]?.length;
  function keepDraft() {
    if (draftKey) { drafts[draftKey] = {text: area.value, pending, context}; save(':drafts', drafts); }
    if (hasDraft(draftKey)) save(':active-draft', draftKey);
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
    const latest = hasDraft(saved) ? saved : Object.keys(drafts).reverse().find(hasDraft);
    draftKey = resume && latest ? latest
      : JSON.stringify([next.page, next.person, next.question, details.kind || 'remark',
        ...(/^(blank|amendment):/.test(details.subject || '') ? [details.subject] : [])]);
    const draft = drafts[draftKey]; context = hasDraft(draftKey) && draft ? draft.context : next;
    pending = draft?.pending || null; area.value = draft?.text || details.prefill || '';
    sheetFiles.use(attached[draftKey] ||= []); area.required = !sheetFiles.list.length;
    heading.textContent = context.kind === 'name_person' ? w.name_person : ['correction', 'decline'].includes(context.kind) ? w.correct : context.question ? w.answer : w.remark;
    where.textContent = w.attached_to + ': ' + context.where;
    addHint.hidden = !window.familiarDeskAddPerson || !['tree', 'person'].includes(context.screen);
    addHint.firstChild.textContent = w.add_elsewhere + ' '; addLink.textContent = w.add_relative;
    if (label.firstChild?.nodeType === Node.TEXT_NODE) label.firstChild.remove();
    label.prepend(document.createTextNode(w.feedback_label));
    send.textContent = w.send; close.textContent = w.close; status.textContent = '';
    placeSheet(); if (!dialog.open) dialog.show(); entry.setAttribute('aria-expanded', 'true');
    renderHistory(); refreshHistory();
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
  document.addEventListener('pointerdown', event => { if (dialog.open && !dialog.contains(event.target) && ![entry, second].includes(event.target)) hide(); });
  // The place already open scrolls back to its beginning.
  nav.addEventListener('click', event => { if (event.target.closest('[aria-current]')?.hash === location.hash && location.pathname === '/') scrollTo({top: 0, behavior: 'smooth'}); });
  area.oninput = keepDraft;
  form.onsubmit = async event => {
    event.preventDefault(); if ((!area.value.trim() && !sheetFiles.list.length) || send.disabled) return;
    send.disabled = area.readOnly = true; sheetFiles.lock(true);
    status.textContent = words().sending; pending ||= crypto.randomUUID(); keepDraft();
    try {
      const item = await sheetFiles.send({...context, kind: context.kind || 'remark', id: pending, text: area.value}, files => {
          area.value = ''; pending = null; keepDraft();
          if (files) status.textContent = words().words_sent;
        });
      if (!item.deliveryNotice) area.value = '';
      pending = null; keepDraft();
      status.textContent = [item.deliveryNotice || words().received, item.uploadNotice].filter(Boolean).join(' · ');
    } catch (error) {
      if (error.file) sheetFiles.mark(error.file, 'refused');
      status.textContent = error.message || words().failed;
    }
    finally { send.disabled = area.readOnly = false; sheetFiles.lock(false); }
  };
  for (const answer of document.querySelectorAll('.desk-answer')) {
    const pictures = attacher(answer.querySelector('button[type=submit]').parentElement, () => {
      answer.querySelector('textarea').required = !pictures.list.length; });
    answer.onsubmit = async event => {
      event.preventDefault(); const input = answer.querySelector('textarea'), result = answer.querySelector('[role=status]');
      const button = answer.querySelector('button[type=submit]'); if (!input.value.trim() && !pictures.list.length) return;
      if (button.disabled) return;
      button.disabled = input.readOnly = true; pictures.lock(true);
      result.textContent = words().sending; answer.dataset.pending ||= crypto.randomUUID();
      try {
        const item = await pictures.send({...locate({kind: 'answer', question: answer.dataset.question}), text: input.value, id: answer.dataset.pending}, files => {
            if (files) result.textContent = words().words_sent;
          });
        if (!item.deliveryNotice) input.value = '';
        delete answer.dataset.pending;
        result.textContent = [item.deliveryNotice || words().received, item.uploadNotice].filter(Boolean).join(' · ');
      } catch (error) {
        if (error.file) pictures.mark(error.file, 'refused');
        result.textContent = error.message || words().failed;
      }
      finally { button.disabled = input.readOnly = false; pictures.lock(false); }
    };
  }
  function update() {
    // Avoid mutations when unchanged: the reader observer also watches child text.
    const hasDraft = Object.values(drafts).some(draft => draft.text?.trim()) || Object.values(attached).some(list => list.length);
    const label = words().remark + (hasDraft ? ' · ' + words().unsent_draft : '');
    if (entry.textContent !== label) entry.textContent = label;
    entry.title = label; entry.dataset.draft = String(hasDraft);
    for (const node of document.querySelectorAll('.desk-private-label')) if (node.textContent !== words().private_notice) node.textContent = words().private_notice;
    const write = words().remark_write || words().remark;
    if (second.textContent !== write) second.textContent = write;
    const route = new URLSearchParams(location.hash.slice(1));
    const view = route.has('feed') ? 'stories' : route.has('person') ? 'tree' : route.get('view') || 'tree';
    // A document's own page belongs to the papers; a kinship word to the tree it was read in.
    const place = location.pathname.startsWith('/sources/') ? 'papers' : location.pathname !== '/' ? '' : view === 'kinship' ? 'tree' : view;
    for (const link of document.querySelectorAll('#desk-nav a, #desk-more a[data-desk-label]')) {
      const label = words()[link.dataset.deskLabel], text = link.querySelector('span');
      if (text && label !== undefined && text.textContent !== label) text.textContent = label;
      const page = {nav_asks: 'asks', nav_correspondence: 'correspondence', nav_progress: 'progress', nav_search_map: 'search-map'}[link.dataset.deskLabel];
      if (page) {
        const href = localPage(page);
        if (link.getAttribute('href') !== href) link.setAttribute('href', href);
      }
      const active = link.pathname === '/' ? link.hash === '#view=' + place : location.pathname === link.pathname;
      if (active && !link.hasAttribute('aria-current')) link.setAttribute('aria-current', 'page'); else if (!active) link.removeAttribute('aria-current');
    }
  }
  // A desk page shown in one language opens itself in the reader's language when that version exists.
  const here = location.pathname.match(/^\/desk\/(asks|correspondence|progress|search-map)(?:\.[a-z-]+)?\.html$/);
  const chosen = chosenLanguage();
  const target = here && chosen && (config.languages || {})[chosen] && localPage(here[1], chosen);
  if (target && target !== location.pathname) { location.replace(target + location.hash); return; }
  new MutationObserver(update).observe(document.querySelector('#root') || nav, {childList: true, subtree: true});
  new MutationObserver(update).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
  update(); document.dispatchEvent(new Event('familiar-desk-ready'));
  window.addEventListener('hashchange', update);
  window.addEventListener('pagehide', keepDraft);
  window.addEventListener('focus', () => { if (dialog.open) refreshHistory(); });
  window.addEventListener('resize', () => { if (dialog.open) placeSheet(); });
})();
