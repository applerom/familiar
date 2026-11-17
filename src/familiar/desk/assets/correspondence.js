/* PURPOSE: Copy complete letters and send owner marks through the common feedback inbox. */
(() => {
  async function start() {
    if (!window.familiarDeskSend) return;
    const config = await (await fetch('/desk/words.json')).json(), w = config.correspondence;
    if (window.familiarDeskUser?.role === 'reader') return;
    const family = config.family_id + ':' + (window.familiarDeskUser?.sub || 'local');
    for (const card of document.querySelectorAll('[data-correspondence]')) {
      const subject = card.dataset.correspondence, status = card.querySelector('[role=status]');
      const draftKey = 'familiar-correspondence:' + family + ':' + subject;
      let draft = {};
      try { draft = JSON.parse(localStorage.getItem(draftKey)) || {}; } catch { /* storage can be disabled */ }
      const save = () => { try { localStorage.setItem(draftKey, JSON.stringify(draft)); } catch { /* keep the live textarea */ } };
      const move = group => {
        document.getElementById(group).append(card);
        for (const section of document.querySelectorAll('main section')) {
          const empty = section.querySelector('.correspondence-empty');
          if (empty) empty.hidden = Boolean(section.querySelector('article'));
        }
      };
      const markSent = () => {
        card.dataset.state = 'sent';
        const actions = card.querySelector('.correspondence-actions'); if (actions) actions.hidden = true;
        const letter = card.querySelector('.correspondence-letter');
        if (letter && !letter.closest('details')) {
          const details = document.createElement('details'), summary = document.createElement('summary'); summary.textContent = w.letter;
          letter.before(details); details.append(summary, letter);
        }
        card.querySelector('[data-follow]').hidden = false;
        card.querySelector('[data-reply]').hidden = false;
        const info = card.querySelector('[data-sent-info]'); info.hidden = false;
        info.textContent = w.sent_info.replace('{by}', draft.sent_by).replace('{at}', draft.sent_at);
        move('waiting');
      };
      const showReply = item => {
        if (card.querySelector('[data-feedback="' + CSS.escape(item.id) + '"]')) return;
        const reply = document.createElement('div'); reply.className = 'correspondence-reply'; reply.dataset.feedback = item.id;
        const literal = document.createElement('p'); literal.className = 'desk-prose'; literal.textContent = item.text;
        const meaning = document.createElement('p'); meaning.textContent = w.pending_meaning;
        reply.append(literal, meaning); card.querySelector('form')?.before(reply);
        card.querySelector('[data-remark]').hidden = false;
        card.dataset.state = 'answered'; move('answers');
      };
      const send = async (kind, text, button) => {
        const key = kind === 'correspondence_sent' ? 'sent' : 'reply';
        button.disabled = true; status.textContent = w.saving;
        draft[key] ||= crypto.randomUUID(); save();
        try {
          await window.familiarDeskSend({id: draft[key], kind, subject, text,
            page: location.pathname, screen: 'correspondence', where: card.querySelector('h3').textContent,
            client_time: new Date().toISOString(), engine_version: config.engine_version, build: config.build});
          status.textContent = w.saved;
          if (key === 'sent') {
            draft.sent_done = true;
            draft.sent_at = new Date().toLocaleString(document.documentElement.lang);
            draft.sent_by = window.familiarDeskUser?.username || card.querySelector('[data-sent-info]').dataset.sender;
            markSent();
          } else {
            const item = {id: draft.reply, text};
            (draft.received ||= []).push(item); showReply(item);
            card.querySelector('textarea').value = ''; draft.text = ''; delete draft.reply;
            button.disabled = false;
          }
          save();
        } catch { status.textContent = w.failed; button.disabled = false; }
      };
      const copy = card.querySelector('[data-copy]');
      if (copy) copy.onclick = async () => {
        const text = card.querySelector('.correspondence-letter').textContent;
        try { await navigator.clipboard.writeText(text); status.textContent = w.copied; }
        catch {
          const range = document.createRange(); range.selectNodeContents(card.querySelector('.correspondence-letter'));
          const selection = getSelection(); selection.removeAllRanges(); selection.addRange(range); status.textContent = w.copy_manually;
        }
      };
      const sent = card.querySelector('[data-sent]');
      if (sent) {
        if (draft.sent_done) markSent();
        sent.onclick = () => send('correspondence_sent', w.sent, sent);
      }
      const form = card.querySelector('[data-reply]');
      if (form) {
        const area = form.querySelector('textarea'); area.value = draft.text || '';
        area.oninput = () => { draft.text = area.value; delete draft.reply; save(); };
        form.onsubmit = event => { event.preventDefault(); if (area.value.trim()) send('correspondence_reply', area.value, form.querySelector('button')); };
      }
      const remark = card.querySelector('[data-remark]');
      if (remark) remark.onclick = () => window.familiarDeskOpen({subject, screen: 'correspondence', finding: card.querySelector('h3').textContent});
      draft.received = (draft.received || []).filter(item => !card.querySelector('[data-feedback="' + CSS.escape(item.id) + '"]'));
      for (const item of draft.received) showReply(item);
      save();
    }
  }
  if (window.familiarDeskSend) start(); else document.addEventListener('familiar-desk-ready', start, {once: true});
})();
