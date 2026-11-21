/* PURPOSE: Open one letter, copy its fields, and record human actions in the common inbox. */
(() => {
  async function start() {
    if (window.familiarDeskUser?.role === 'reader') return;
    const config = await (await fetch('/desk/words.json')).json();
    const w = (config.languages?.[document.documentElement.lang] || config).correspondence;
    const rows = new Map();
    document.querySelectorAll('[data-letter]').forEach(row => {
      const id = row.dataset.letter;
      if (!rows.has(id)) rows.set(id, []);
      rows.get(id).push(row);
    });
    const pane = document.querySelector('.mail-pane'), wide = matchMedia('(min-width:960px)');
    const recommendations = [...document.querySelectorAll('[data-recommend]')];
    let selected;
    const place = () => { if (selected) (wide.matches ? pane : selected.row.parentElement).append(selected.detail); };
    const close = () => {
      if (!selected) return;
      selected.detail.hidden = true; selected.home.append(selected.detail);
      selected.row.setAttribute('aria-expanded', 'false'); selected = null;
    };
    const refreshRecommendations = () => {
      let visible = 0;
      for (const link of recommendations) {
        const ready = document.getElementById('document-' + link.dataset.recommend).dataset.state === 'ready';
        link.parentElement.hidden = !ready || visible >= 3;
        if (!link.parentElement.hidden) visible++;
      }
      const empty = document.querySelector('.mail-now-empty');
      if (empty) empty.hidden = Boolean(visible);
    };
    for (const link of recommendations) link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const row = rows.get(link.dataset.recommend)[0];
      if (selected?.row !== row) row.click();
      row.focus({preventScroll: true});
      row.scrollIntoView({block: 'nearest'});
    });
    wide.addEventListener('change', place);
    const family = config.family_id + ':' + (window.familiarDeskUser?.sub || 'local');
    for (const [subject, triggers] of rows) {
      const card = document.getElementById('document-' + subject), detail = document.getElementById('letter-' + subject);
      const status = detail.querySelector('[role=status]');
      const label = triggers[0].querySelector('strong').textContent;
      const draftKey = 'familiar-correspondence:' + family + ':' + subject;
      let draft = {};
      try { draft = JSON.parse(localStorage.getItem(draftKey)) || {}; } catch { /* keep the live draft */ }
      const save = () => { try { localStorage.setItem(draftKey, JSON.stringify(draft)); } catch { /* keep the live draft */ } };
      for (const row of triggers) row.onclick = () => {
        const wasSelected = selected?.row === row; close();
        if (!wasSelected) { selected = {home: card, row, detail}; detail.hidden = false; row.setAttribute('aria-expanded', 'true'); place(); }
      };
      const setState = (state, icon) => {
        card.dataset.state = state;
        for (const row of triggers) {
          row.querySelector('.mail-state').dataset.status = state;
          row.querySelector('[data-state-label]').textContent = w['state_' + state];
          row.querySelector('[data-state-icon]').textContent = icon;
        }
      };
      const markSent = () => {
        detail.querySelector('[data-sent]').hidden = true;
        detail.querySelector('[data-follow]').hidden = false; detail.querySelector('[data-reply]').hidden = false;
        const info = detail.querySelector('[data-sent-info]'); info.hidden = false;
        info.textContent = w.sent_info.replace('{by}', draft.sent_by).replace('{at}', draft.sent_at);
        setState('sent', '◷');
      };
      const showReply = item => {
        if (detail.querySelector('[data-feedback="' + CSS.escape(item.id) + '"]')) return;
        const reply = document.createElement('div'); reply.className = 'mail-reply'; reply.dataset.feedback = item.id;
        const literal = document.createElement('p'); literal.className = 'desk-prose'; literal.textContent = item.text;
        const meaning = document.createElement('p'); meaning.textContent = w.pending_meaning;
        reply.append(literal, meaning); detail.querySelector('[data-replies]').append(reply);
        detail.querySelector('[data-remark]').hidden = false; setState('answered', '✓');
      };
      const send = async (action, text, button) => {
        const key = action === 'correspondence_sent' ? 'sent' : 'reply';
        button.disabled = true; status.textContent = w.saving;
        draft[key] ||= crypto.randomUUID(); save();
        try {
          await window.familiarDeskSend({id: draft[key], kind: action, subject, text, page: location.pathname,
            screen: 'correspondence', where: label, client_time: new Date().toISOString(), engine_version: config.engine_version, build: config.build});
          status.textContent = w.saved;
          if (key === 'sent') {
            draft.sent_done = true; draft.sent_at = new Date().toLocaleString(document.documentElement.lang);
            draft.sent_by = window.familiarDeskUser?.username || detail.querySelector('[data-sent-info]').dataset.sender; markSent();
          } else {
            const item = {id: draft.reply, text}; (draft.received ||= []).push(item); showReply(item);
            detail.querySelector('textarea').value = ''; draft.text = ''; delete draft.reply; button.disabled = false;
          }
          save(); refreshRecommendations();
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
      detail.querySelector('[data-remark]').onclick = () => window.familiarDeskOpen({subject, screen: 'correspondence', finding: label});
      if (draft.sent_done && card.dataset.state === 'ready') markSent();
      draft.received = (draft.received || []).filter(item => !detail.querySelector('[data-feedback="' + CSS.escape(item.id) + '"]'));
      if (['sent', 'answered'].includes(card.dataset.state)) for (const item of draft.received) showReply(item);
      save();
    }
    refreshRecommendations();
  }
  if (window.familiarDeskSend) start(); else document.addEventListener('familiar-desk-ready', start, {once: true});
})();
