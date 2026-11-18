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
  const [config, links, reminders, user] = await Promise.all([
    json('words.json', {}), reader ? json('asks-links.json', {}) : {},
    json('asks-reminders.json', []), window.familiarDeskIdentity
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
    node.href = path('asks.html') + (kids ? '?mode=kids' : '') + '#ask-' + encodeURIComponent(id);
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
    const pending = new WeakMap();
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
      const buttons = [...card.querySelectorAll('button')];
      buttons.forEach(button => { button.disabled = true; });
      const status = card.querySelector('.ask-status');
      status.textContent = '';
      const ask = card.dataset.ask, tender = card.dataset.tender === 'true';
      const viaChild = kids && !!card.querySelector('.ask-child');
      const payload = {screen: 'asks', ask_id: ask, subject: ask, ...fields,
        private: tender, tender, via_child: viaChild, ask_context: card.dataset.context};
      const fingerprint = JSON.stringify(payload);
      try {
        let token = pending.get(card);
        if (!token || token.fingerprint !== fingerprint) {
          token = {fingerprint, id: crypto.randomUUID(), client_time: new Date().toISOString()};
          pending.set(card, token);
        }
        if (!window.familiarDeskSend) throw new Error('feedback unavailable');
        await window.familiarDeskSend({...payload, id: token.id, client_time: token.client_time});
        pending.delete(card);
        const state = payload.private ? 'private' : 'answered';
        responses[ask] = {at: Date.now(), state, child: viaChild, context: card.dataset.context};
        try { localStorage.setItem(key, JSON.stringify(responses)); } catch { /* optional */ }
        card.querySelector('.ask-answer').reset();
        showFeedback(card, state, viaChild);
        fillLine();
      } catch { status.textContent = config.failed; }
      finally { buttons.forEach(button => { button.disabled = false; }); }
    }
    toggleMode(new URLSearchParams(location.search).get('mode') === 'kids' && !!page.querySelector('.ask-child'));
    modes.hidden = !page.querySelector('.ask-child');
    for (const card of cards) {
      if (portable) card.querySelector('.ask-answer').hidden = true;
      const saved = responses[card.dataset.ask];
      if (saved?.context === card.dataset.context) showFeedback(card, saved.state, saved.child);
    }
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
      if (!text.trim()) { form.querySelector('textarea').focus(); return; }
      send(card, {kind: 'ask_answer', text, wants: {}});
    });
  }

  if (reader) {
    let scheduled = false;
    function update() {
      scheduled = false;
      const w = words();
      const panel = reader.querySelector('.panel[data-feedback-person]');
      if (panel) {
        const body = panel.querySelector('.body'), person = panel.dataset.feedbackPerson;
        const old = body?.querySelector('.ask-on-card');
        const items = links.cards?.[person];
        if (old && (!items || old.dataset.person !== person)) old.remove();
        if (body && items && (!old || old.dataset.person !== person)) {
          const section = el('section', 'ask-on-card group');
          section.dataset.person = person;
          // Two asks are an invitation; the whole list lives on the relatives page.
          section.append(el('h3', '', w.on_card), ...items.slice(0, 2).map(item => link(item.id, item.text)));
          if (items.length > 2) { const all = link(items[2].id, w.title + ' →'); all.className = 'ask-all'; section.append(all); }
          // After the person and the family, before the folded details: the card first tells, then asks.
          const next = body.querySelector(':scope > .card-more, :scope > .kin-viewer, :scope > section.group.ask');
          if (next) next.before(section); else body.append(section);
        }
      }
      const feed = reader.querySelector('[data-feedback-feed]');
      const body = feed?.querySelector('.feed-text');
      if (body) {
        const feedId = feed.dataset.feedbackFeed, step = feed.dataset.feedbackStep;
        const item = links.steps?.[feedId]?.[step];
        const found = links.child_steps?.[feedId]?.includes(step);
        const kids = feed.dataset.feedbackTextMode === 'kids' && !!item?.child;
        const text = kids ? item.child : item?.text;
        const old = body.querySelector('.ask-in-feed');
        const signature = JSON.stringify([item?.id, text, found]);
        if (old && old.dataset.ask !== signature) old.remove();
        if ((item || found) && (!old || !old.isConnected)) {
          const aside = el('aside', 'ask-in-feed');
          aside.dataset.ask = signature;
          if (item) aside.append(link(item.id, text, kids));
          if (found) aside.append(el('span', 'ask-child-mark', w.child_mark));
          const story = [...body.children].filter(node => node.classList.contains('feed-simple')).at(-1);
          if (story) story.after(aside); else body.append(aside);
        }
      }
    }
    const schedule = () => {
      if (scheduled) return;
      scheduled = true;
      queueMicrotask(update);
    };
    new MutationObserver(schedule).observe(reader, {childList: true, subtree: true, attributes: true,
      attributeFilter: ['data-feedback-feed', 'data-feedback-step', 'data-feedback-text-mode', 'data-feedback-person', 'data-person']});
    update();
  }
})();
