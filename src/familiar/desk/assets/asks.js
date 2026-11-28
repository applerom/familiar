/* Family conversation controls and links on the checked desk reader. */
(async function () {
  const page = document.querySelector('.ask-page'), reader = document.querySelector('#root');
  const portable = !!document.querySelector('meta[name="familiar-static-demo"]');
  const path = name => (portable ? 'desk/' : '/desk/') + name;
  const json = async (name, fallback) => {
    try {
      const response = await fetch(path(name));
      return response.ok ? await response.json() : fallback;
    } catch { return fallback; }
  };
  const config = await json('words.json', {});
  // The conversation in the reader's language when the build made one; otherwise the family's own.
  const suffixOf = lang => lang !== config.source_language && (config.asks_languages || []).includes(lang) ? '.' + lang : '';
  let suffix = suffixOf(document.documentElement.lang);
  let [links, reminders, user] = await Promise.all([
    reader ? json(`asks-links${suffix}.json`, {}) : {},
    json(`asks-reminders${suffix}.json`, []), window.familiarDeskIdentity
  ]);
  const words = () => (config.languages?.[document.documentElement.lang] || config).asks;
  if (!words()) return;
  const key = `familiar-asks:${config.family_id}${user?.sub ? ':' + user.sub : ''}`;
  let responses = {};
  try { responses = JSON.parse(localStorage.getItem(key)) || {}; } catch { /* optional */ }
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  };
  const link = (id, text, kids = false) => {
    const node = el('a', '', text);
    node.href = path(`asks${suffix}.html`) + (kids ? '?mode=kids' : '') + '#ask-' + encodeURIComponent(id);
    return node;
  };
  const recent = id => Date.now() - (responses[id]?.at || 0) < 7 * 86400000;
  function todayItems(kids) {
    const used = new Set();
    return reminders.filter(item => {
      const key = item.holder + '\n' + item.occasion;
      if (recent(item.id) || used.has(key) || (kids && !item.child)) return false;
      used.add(key);
      return true;
    });
  }
  function fillToday(section, kids = false) {
    const today = todayItems(kids).slice(0, 3);
    const items = today.map(item => {
      const row = el('li');
      const question = kids ? item.child : item.question;
      const witness = link(item.id, item.name, kids);
      witness.title = question;
      witness.setAttribute('aria-label', item.name + ' · ' + question);
      row.append(witness, document.createTextNode(' · ' + item.occasion));
      return row;
    });
    section.querySelector('ul').replaceChildren(...items);
    section.hidden = !items.length;
  }

  if (page) {
    // One quiet line, only when there is an occasion: the occasion itself leads to its question.
    const today = page.querySelector('.ask-today');
    const modes = page.querySelector('.ask-modes'), cards = page.querySelectorAll('.ask-card');
    const pendingKey = key + ':pending';
    let pending = {};
    try { pending = JSON.parse(localStorage.getItem(pendingKey)) || {}; } catch { /* optional */ }
    const savePending = () => { try { localStorage.setItem(pendingKey, JSON.stringify(pending)); } catch { /* optional */ } };
    const tokenKey = card => card.dataset.ask + ':' + card.dataset.context;
    const sending = new WeakSet();
    const statusFor = (state, child) => state === 'answered' && child ? 'saved_child' : 'saved_' + state.split(':')[0];
    let kids = false;
    function fillLine() {
      const item = todayItems(kids)[0];
      today.replaceChildren(...(item ? [link(item.id, item.occasion, kids)] : []));
      today.hidden = !item;
    }
    function toggleMode(next) {
      kids = next;
      modes.querySelector('button').setAttribute('aria-pressed', String(kids));
      for (const card of cards) {
        const child = card.querySelector('.ask-child');
        card.hidden = kids && !child;
        card.classList.toggle('ask-kids', kids && !!child);
        if (child) {
          child.hidden = !kids;
          card.querySelector('.ask-adult').hidden = kids;
        }
      }
      for (const holder of page.querySelectorAll('.ask-holder')) holder.hidden = !holder.querySelector('.ask-card:not([hidden])');
      fillLine();
    }
    function showFeedback(card, state, child) {
      const text = words()[statusFor(state, child)];
      if (text) card.querySelector('.ask-status').textContent = text;
      if (state === 'answered' || state === 'private') card.querySelector('.ask-answer').hidden = true;
    }
    function openTarget() {
      if (!location.hash.startsWith('#ask-')) return;
      const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target?.matches('.ask-card')) { target.open = true; target.scrollIntoView({block: 'start'}); }
    }
    async function send(card, fields) {
      if (sending.has(card)) return;
      sending.add(card);
      const buttons = [...card.querySelectorAll('button')];
      buttons.forEach(button => { button.disabled = true; });
      const files = pictures.get(card);
      files?.lock(true);
      const input = card.querySelector('textarea');
      input.readOnly = true;
      const status = card.querySelector('.ask-status');
      status.textContent = '';
      const ask = card.dataset.ask, tender = card.dataset.tender === 'true';
      const viaChild = kids && !!card.querySelector('.ask-child');
      const payload = {screen: 'asks', ask_id: ask, subject: ask, ...fields,
        private: tender, tender, via_child: viaChild, ask_context: card.dataset.context};
      try {
        const token = pending[tokenKey(card)] ||= {id: crypto.randomUUID(), client_time: new Date().toISOString()};
        savePending();
        if (!window.familiarDeskSend) throw new Error('feedback unavailable');
        const details = {...payload, id: token.id, client_time: token.client_time};
        const received = files ? await files.send(details, count => {
          if (count) status.textContent = (config.languages?.[document.documentElement.lang] || config).words_sent;
        }) : await window.familiarDeskSend(details);
        if (!received.deliveryNotice) card.querySelector('.ask-answer').reset();
        const notices = [received.deliveryNotice, received.uploadNotice].filter(Boolean);
        if (notices.length) status.textContent = notices.join(' · ');
        else showFeedback(card, payload.private ? 'private' : 'answered', viaChild);
      } catch (error) {
        if (error.file) pictures.get(card)?.mark(error.file, 'refused');
        status.textContent = error.message || config.failed;
      }
      finally {
        buttons.forEach(button => { button.disabled = false; });
        files?.lock(false); input.readOnly = false; sending.delete(card);
      }
    }
    document.addEventListener('familiar-feedback-received', ({detail}) => {
      if (detail.kind !== 'ask_answer') return;
      const card = [...cards].find(card => card.dataset.ask === detail.ask_id && card.dataset.context === detail.ask_context);
      if (!card) return;
      const state = detail.private ? 'private' : 'answered';
      responses[detail.ask_id] = {at: Date.now(), state, child: detail.via_child, context: detail.ask_context};
      try { localStorage.setItem(key, JSON.stringify(responses)); } catch { /* optional */ }
      delete pending[tokenKey(card)]; savePending();
      if (!sending.has(card)) showFeedback(card, state, detail.via_child);
      fillLine();
    });
    toggleMode(new URLSearchParams(location.search).get('mode') === 'kids' && !!page.querySelector('.ask-child'));
    modes.hidden = !page.querySelector('.ask-child');
    for (const card of cards) {
      if (portable) card.querySelector('.ask-answer').hidden = true;
      const saved = responses[card.dataset.ask];
      if (saved?.context === card.dataset.context) showFeedback(card, saved.state, saved.child);
    }
    // A photograph or a scan can be the whole answer; the attach control comes from the desk sender.
    const pictures = new WeakMap();
    const attachAll = () => {
      for (const card of cards) {
        const form = card.querySelector('.ask-answer');
        if (portable || pictures.has(card) || !window.familiarDeskAttach) continue;
        const box = window.familiarDeskAttach(form.querySelector('.ask-send'), () => {
          form.querySelector('textarea').required = !box.list.length;
        });
        pictures.set(card, box);
      }
    };
    if (window.familiarDeskAttach) attachAll(); else document.addEventListener('familiar-desk-ready', attachAll, {once: true});
    openTarget();
    addEventListener('hashchange', openTarget);
    page.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button) return;
      if (button.dataset.action === 'kids') { toggleMode(!kids); return; }
      if (!button.matches('.ask-hint')) return;
      // A hint is our guess put into the field; the person corrects or adds to it.
      const card = button.closest('.ask-card'), field = card.querySelector('textarea');
      // An open hint ends in an ellipsis on the button; in the field it is a sentence to continue.
      const start = text => text.replace(/\s*(…|\.\.\.)$/, ' ');
      const hints = [...card.querySelectorAll('.ask-hint')].map(hint => start(hint.dataset.hint).trim());
      const current = field.value.trim();
      field.value = !current || hints.includes(current) ? start(button.dataset.hint) : current + '\n' + start(button.dataset.hint);
      for (const hint of card.querySelectorAll('.ask-hint')) hint.setAttribute('aria-pressed', String(hint === button));
      field.focus();
      field.setSelectionRange(field.value.length, field.value.length);
    });
    page.addEventListener('submit', event => {
      event.preventDefault();
      const form = event.target, card = form.closest('.ask-card');
      const text = form.querySelector('textarea').value;
      if (!text.trim() && !pictures.get(card)?.list.length) { form.querySelector('textarea').focus(); return; }
      send(card, {kind: 'ask_answer', text, wants: {}});
    });
  }

  if (reader) {
    let scheduled = false;
    // What a thin card lacks: an unfilled line of the card itself, one tap from the remark form; our guess answers in one tap.
    const saidKey = key + ':blanks';
    let said = {};
    try { said = JSON.parse(localStorage.getItem(saidKey)) || {}; } catch { /* optional */ }
    document.addEventListener('familiar-feedback-received', ({detail}) => {
      if (!/^(blank|amendment):/.test(detail.subject || '')) return;
      said[detail.subject + (detail.amendment_revision || '')] = Date.now();
      try { localStorage.setItem(saidKey, JSON.stringify(said)); } catch { /* optional */ }
      reader.querySelector('.card-blanks')?.remove(); schedule();
    });
    function blankSlot(item, person, w) {
      const slot = el('div', 'blank-slot'), about = {screen: 'person', person, subject: item.subject,
        finding: item.label + (item.guess ? ': ' + item.guess : ''), ...(item.version ? {question: item.version} : {}),
        ...(item.amendment_revision ? {amendment_revision: item.amendment_revision} : {})};
      const tell = kind => window.familiarDeskOpen?.({...about, kind, prefill: item.start});
      slot.append(el('b', '', item.label));
      if (item.told) slot.append(el('small', '', item.told));
      if (said[item.subject + (item.amendment_revision || '')]) { slot.append(el('span', 'blank-sent', w.sent)); return slot; }
      if (!item.guess) {
        if (portable) { slot.append(el('i')); return slot; }
        const button = el('button', 'blank-slot');
        button.type = 'button'; button.append(...slot.childNodes, el('i'));
        button.onclick = () => tell('correction');
        return button;
      }
      slot.classList.add('blank-guess');
      slot.append(el('span', 'blank-think', w.think.replace('{value}', item.guess)));
      if (portable) return slot;
      const row = el('span', 'blank-answer'), yes = el('button', 'blank-yes', w.yes), no = el('button', '', w.no);
      yes.type = no.type = 'button';
      yes.onclick = async () => {
        if (yes.disabled || !window.familiarDeskSend) return;
        yes.disabled = no.disabled = true;
        try { await window.familiarDeskSend({...about, kind: 'confirm', text: item.yes}); }
        catch (error) { yes.disabled = no.disabled = false; row.append(el('small', '', error.message || config.failed)); }
      };
      no.onclick = () => tell('decline');
      row.append(yes, no); slot.append(row);
      return slot;
    }
    function showBlanks(body, person, all) {
      const items = links.blanks?.[person], old = body.querySelector('.card-blanks');
      const current = old && old.dataset.person === person && old.dataset.suffix === suffix;
      if (old && (!items || !current)) old.remove();
      if (!items || current) return;
      const w = all.blanks, section = el('section', 'card-blanks group');
      section.dataset.person = person; section.dataset.suffix = suffix;
      if (items.some(item => item.subject.endsWith(':name'))) section.dataset.name = 'true';
      section.append(el('h3', '', w.title));
      const slots = el('div', 'blank-slots');
      slots.append(...items.map(item => blankSlot(item, person, w)));
      section.append(slots);
      // Under who this is and the papers: the card first shows what is there, then asks for what is missing.
      const after = body.querySelector(':scope > .card-papers') || body.querySelector(':scope > .kin:not(.kin-viewer)') || body.querySelector(':scope > header');
      if (after) after.after(section); else body.prepend(section);
    }
    function showFeedAsks(feed, w) {
      const body = feed?.querySelector('.feed-text');
      if (!body) return;
      const feedId = feed.dataset.feedbackFeed;
      const kids = feed.dataset.feedbackTextMode === 'kids';
      for (const [slot, step] of [['chapter', feed.dataset.feedbackStep], ['end', feed.dataset.feedbackLast ? 'end' : null]]) {
        const items = links.steps?.[feedId]?.[step] || [];
        const found = links.child_steps?.[feedId]?.includes(step);
        const old = body.querySelector(`.ask-in-feed[data-slot="${slot}"]`);
        const signature = JSON.stringify([items, found, kids, suffix]);
        if (old?.dataset.ask === signature) continue;
        old?.remove();
        if (!items.length && !found) continue;
        const aside = el('aside', 'ask-in-feed');
        aside.dataset.slot = slot;
        aside.dataset.ask = signature;
        for (const item of items) {
          const child = kids && !!item.child;
          aside.append(link(item.id, child ? item.child : item.text, child));
        }
        if (found) aside.append(el('span', 'ask-child-mark', w.child_mark));
        const story = slot === 'chapter' && [...body.children].filter(node => node.classList.contains('feed-simple')).at(-1);
        if (story) story.after(aside); else body.append(aside);
      }
    }
    function update() {
      scheduled = false;
      const w = words();
      const panel = reader.querySelector('.panel[data-feedback-person]');
      if (panel) {
        const body = panel.querySelector('.body'), person = panel.dataset.feedbackPerson;
        const old = body?.querySelector('.ask-on-card');
        const items = links.cards?.[person];
        const all = config.languages?.[document.documentElement.lang] || config;
        if (body && all.blanks) showBlanks(body, person, all);
        const kin = panel.dataset.askKin || '';
        const shown = old && old.dataset.person === person && old.dataset.suffix === suffix && old.dataset.kin === kin;
        if (old && (!items || !shown)) old.remove();
        if (body && items && !shown) {
          const section = el('section', 'ask-on-card group');
          section.dataset.person = person;
          section.dataset.suffix = suffix;
          section.dataset.kin = kin;
          // Two asks are an invitation; the whole list lives on the relatives page.
          section.append(el('h3', '', w.on_card), ...items.slice(0, 2).map(item => link(item.id,
            item.own_question ? (kin && w.prompt_kin ? w.prompt_kin.replace('{kin}', kin).replace('{question}', item.own_question) : item.own_question) : item.text)));
          if (items.length > 2) { const all = link(items[2].id, w.title + ' →'); all.className = 'ask-all'; section.append(all); }
          // After the person and the family, before the folded details: the card first tells, then asks.
          const next = body.querySelector(':scope > .card-more, :scope > .kin-viewer, :scope > section.group.ask');
          if (next) next.before(section); else body.append(section);
        }
      }
      showFeedAsks(reader.querySelector('[data-feedback-feed]'), w);
    }
    const schedule = () => {
      if (scheduled) return;
      scheduled = true;
      queueMicrotask(update);
    };
    new MutationObserver(schedule).observe(reader, {childList: true, subtree: true, attributes: true,
      attributeFilter: ['data-feedback-feed', 'data-feedback-step', 'data-feedback-last', 'data-feedback-text-mode', 'data-feedback-person', 'data-person', 'data-ask-kin']});
    // The reader switched language: the same asks in that language, when the build made them.
    new MutationObserver(async () => {
      const next = suffixOf(document.documentElement.lang);
      if (next === suffix) return;
      const loaded = await json(`asks-links${next}.json`, null);
      if (!loaded) return;
      [links, suffix] = [loaded, next];
      schedule();
    }).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
    update();
  }
})();
