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
  function fillToday(section, kids = false) {
    const used = new Set();
    const today = reminders.filter(item => {
      const key = item.holder + '\n' + item.occasion;
      if (recent(item.id) || used.has(key) || (kids && !item.child)) return false;
      used.add(key);
      return true;
    }).slice(0, 3);
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
    const today = page.querySelector('.ask-today');
    const modes = page.querySelector('.ask-modes'), cards = page.querySelectorAll('.ask-card');
    const pending = new WeakMap();
    const statusFor = (state, child) => state === 'answered' && child ? 'saved_child' : 'saved_' + state.split(':')[0];
    let kids = false;
    function toggleMode(next) {
      kids = next;
      for (const button of modes.querySelectorAll('button')) {
        button.setAttribute('aria-pressed', String((button.dataset.action === 'kids') === kids));
      }
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
      for (const count of page.querySelectorAll('.ask-mode-count')) count.textContent = count.dataset[kids ? 'kids' : 'adults'];
      fillToday(today, kids);
    }
    function showFeedback(card, state, child) {
      card.querySelector('.ask-status').textContent = words()[statusFor(state, child)];
      const hint = card.querySelector('.ask-next');
      if (state === 'dont_know' && hint.textContent) hint.hidden = false;
      if (state === 'answered' || state === 'private') card.querySelector('.ask-actions').hidden = true;
    }
    async function send(card, fields) {
      const buttons = [...card.querySelectorAll('button')];
      buttons.forEach(button => { button.disabled = true; });
      const status = card.querySelector('.ask-status');
      status.textContent = '';
      const ask = card.dataset.ask, tender = card.dataset.tender === 'true';
      const viaChild = kids && !!card.querySelector('.ask-child');
      const payload = {screen: 'asks', ask_id: ask, subject: ask, ...fields,
        private: tender || fields.private === true, tender, via_child: viaChild, ask_context: card.dataset.context};
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
        const state = fields.ask_state || (payload.private ? 'private' : 'answered');
        responses[ask] = {at: Date.now(), state, child: viaChild, context: card.dataset.context};
        try { localStorage.setItem(key, JSON.stringify(responses)); } catch { /* optional */ }
        for (const form of card.querySelectorAll('form')) { form.reset(); form.hidden = true; }
        showFeedback(card, state, viaChild);
        fillToday(today, kids);
      } catch { status.textContent = config.failed; }
      finally { buttons.forEach(button => { button.disabled = false; }); }
    }
    toggleMode(new URLSearchParams(location.search).get('mode') === 'kids' && !!page.querySelector('.ask-child'));
    modes.hidden = !page.querySelector('.ask-child');
    for (const card of cards) {
      if (!portable) card.querySelector('.ask-actions').hidden = false;
      const saved = responses[card.dataset.ask];
      if (saved?.context === card.dataset.context) showFeedback(card, saved.state, saved.child);
    }
    page.addEventListener('click', event => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const action = button.dataset.action, card = button.closest('.ask-card');
      if (action === 'adults' || action === 'kids') { toggleMode(action === 'kids'); return; }
      const answer = card.querySelector('.ask-answer'), handoff = card.querySelector('.ask-handoff');
      if (action === 'tell' || action === 'handoff') {
        const form = action === 'tell' ? answer : handoff;
        const wasHidden = form.hidden;
        answer.hidden = true;
        if (handoff) handoff.hidden = true;
        form.hidden = !wasHidden;
        if (!form.hidden) form.querySelector('textarea, select').focus();
      } else send(card, {kind: 'ask_state', text: button.textContent,
        ask_state: action, private: action === 'private'});
    });
    page.addEventListener('submit', event => {
      event.preventDefault();
      const form = event.target, card = form.closest('.ask-card');
      if (form.matches('.ask-handoff')) {
        const witness = form.querySelector('select').selectedOptions[0];
        send(card, {kind: 'ask_state', text: words().handoff + ' ' + witness.textContent,
          ask_state: 'will_ask:' + witness.value});
        return;
      }
      const text = form.querySelector('textarea').value;
      if (!text.trim()) { form.querySelector('textarea').focus(); return; }
      const wants = Object.fromEntries([...new FormData(form)].filter(([name, value]) => name !== 'private' && value.trim()));
      send(card, {kind: 'ask_answer', text, wants, private: form.elements.namedItem('private')?.checked === true});
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
          section.append(el('h3', '', w.on_card), ...items.map(item => link(item.id, item.text)));
          const header = body.querySelector('header');
          if (header) header.after(section); else body.prepend(section);
        }
      }
      for (const button of reader.querySelectorAll('.n[data-person]')) {
        const text = links.counts?.[button.dataset.person], old = button.querySelector('.ask-count');
        if (text && old?.textContent !== text) {
          const count = el('small', 'ask-count', text);
          const target = button.querySelector('.tx') || button.querySelector('.dl') || button;
          if (!old) target.append(count); else old.replaceWith(count);
        } else if (!text && old) old.remove();
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
      const tree = reader.querySelector('.tree-body');
      if (tree && !tree.querySelector('.ask-home') && reminders.length) {
        const section = el('details', 'ask-home ask-today');
        section.append(el('summary', '', w.today), el('ul'));
        tree.append(section);
        fillToday(section);
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
