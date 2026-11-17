/* PURPOSE: Open one letter, copy its fields, and record human actions in the common inbox. */
(() => {
  async function start() {
    if (window.familiarDeskUser?.role === 'reader') return;
    const config = await (await fetch('/desk/words.json')).json(), w = config.correspondence;
    const cards = [...document.querySelectorAll('[data-correspondence]')];
    const pane = document.querySelector('.mail-pane'), wide = matchMedia('(min-width:960px)');
    let group = 'ready', kind = 'all', selected;
    const place = () => { if (selected) (wide.matches ? pane : selected.card).append(selected.detail); };
    const close = () => {
      if (!selected) return;
      selected.detail.hidden = true; selected.card.append(selected.detail);
      selected.card.querySelector('.mail-row').setAttribute('aria-expanded', 'false'); selected = null;
    };
    const refresh = () => {
      for (const card of cards) card.hidden = card.dataset.mailGroup !== group || (kind !== 'all' && card.dataset.mailKind !== kind);
      if (selected?.card.hidden) close();
      document.querySelector('.mail-empty').hidden = cards.some(card => !card.hidden);
      for (const button of document.querySelectorAll('[data-group]')) {
        button.setAttribute('aria-pressed', String(button.dataset.group === group));
        button.querySelector('[data-count]').textContent = cards.filter(card => card.dataset.mailGroup === button.dataset.group && (kind === 'all' || card.dataset.mailKind === kind)).length;
      }
      for (const button of document.querySelectorAll('[data-kind]')) button.setAttribute('aria-pressed', String(button.dataset.kind === kind));
    };
    document.querySelectorAll('[data-group]').forEach(button => button.onclick = () => { group = button.dataset.group; refresh(); });
    document.querySelectorAll('[data-kind]').forEach(button => button.onclick = () => { kind = button.dataset.kind; refresh(); });
    wide.addEventListener('change', place);
    const family = config.family_id + ':' + (window.familiarDeskUser?.sub || 'local');
    for (const card of cards) {
      const detail = card.querySelector('.mail-detail'), status = detail.querySelector('[role=status]'), row = card.querySelector('.mail-row');
      const subject = card.dataset.correspondence, draftKey = 'familiar-correspondence:' + family + ':' + subject;
      let draft = {};
      try { draft = JSON.parse(localStorage.getItem(draftKey)) || {}; } catch { /* keep the live draft */ }
      const save = () => { try { localStorage.setItem(draftKey, JSON.stringify(draft)); } catch { /* keep the live draft */ } };
      row.onclick = () => {
        const wasSelected = selected?.card === card; close();
        if (!wasSelected) { selected = {card, detail}; detail.hidden = false; row.setAttribute('aria-expanded', 'true'); place(); }
      };
      const move = (state, target, navigate) => {
        card.dataset.state = state; card.dataset.mailGroup = target;
        row.querySelector('.mail-state').textContent = w['state_' + state];
        if (navigate) group = target;
      };
      const markSent = navigate => {
        detail.querySelector('[data-sent]').hidden = true;
        detail.querySelector('[data-follow]').hidden = false; detail.querySelector('[data-reply]').hidden = false;
        const info = detail.querySelector('[data-sent-info]'); info.hidden = false;
        info.textContent = w.sent_info.replace('{by}', draft.sent_by).replace('{at}', draft.sent_at);
        move('sent', 'waiting', navigate);
      };
      const showReply = (item, navigate) => {
        if (detail.querySelector('[data-feedback="' + CSS.escape(item.id) + '"]')) return;
        const reply = document.createElement('div'); reply.className = 'mail-reply'; reply.dataset.feedback = item.id;
        const literal = document.createElement('p'); literal.className = 'desk-prose'; literal.textContent = item.text;
        const meaning = document.createElement('p'); meaning.textContent = w.pending_meaning;
        reply.append(literal, meaning); detail.querySelector('[data-replies]').append(reply);
        detail.querySelector('[data-remark]').hidden = false; move('answered', 'answers', navigate);
      };
      const send = async (action, text, button) => {
        const key = action === 'correspondence_sent' ? 'sent' : 'reply';
        button.disabled = true; status.textContent = w.saving;
        draft[key] ||= crypto.randomUUID(); save();
        try {
          await window.familiarDeskSend({id: draft[key], kind: action, subject, text, page: location.pathname,
            screen: 'correspondence', where: row.querySelector('strong').textContent, client_time: new Date().toISOString(), engine_version: config.engine_version, build: config.build});
          status.textContent = w.saved;
          if (key === 'sent') {
            draft.sent_done = true; draft.sent_at = new Date().toLocaleString(document.documentElement.lang);
            draft.sent_by = window.familiarDeskUser?.username || detail.querySelector('[data-sent-info]').dataset.sender; markSent(true);
          } else {
            const item = {id: draft.reply, text}; (draft.received ||= []).push(item); showReply(item, true);
            detail.querySelector('textarea').value = ''; draft.text = ''; delete draft.reply; button.disabled = false;
          }
          save(); refresh();
        } catch { status.textContent = w.failed; button.disabled = false; }
      };
      detail.querySelectorAll('[data-copy]').forEach(button => button.onclick = async () => {
        const value = detail.querySelector('[data-value="' + button.dataset.copy + '"]');
        try { await navigator.clipboard.writeText(value.textContent); status.textContent = w.copied; }
        catch { const range = document.createRange(); range.selectNodeContents(value); const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range); status.textContent = w.copy_manually; }
      });
      detail.querySelector('[data-sent]').onclick = event => send('correspondence_sent', w.sent, event.currentTarget);
      const form = detail.querySelector('[data-reply]'), area = form.querySelector('textarea');
      area.value = draft.text || ''; area.oninput = () => { draft.text = area.value; delete draft.reply; save(); };
      form.onsubmit = event => { event.preventDefault(); if (area.value.trim()) send('correspondence_reply', area.value, form.querySelector('button')); };
      detail.querySelector('[data-remark]').onclick = () => window.familiarDeskOpen({subject, screen: 'correspondence', finding: row.querySelector('strong').textContent});
      if (draft.sent_done && card.dataset.state === 'ready') markSent(false);
      draft.received = (draft.received || []).filter(item => !detail.querySelector('[data-feedback="' + CSS.escape(item.id) + '"]'));
      if (['sent', 'answered'].includes(card.dataset.state)) for (const item of draft.received) showReply(item, false);
      save();
    }
    refresh();
  }
  if (window.familiarDeskSend) start(); else document.addEventListener('familiar-desk-ready', start, {once: true});
})();
