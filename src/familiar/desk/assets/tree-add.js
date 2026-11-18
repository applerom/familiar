/*
START_MODULE_CONTRACT: MOD-DESK-TREE-ADD
PURPOSE: Place narrator additions next to their family anchor while retaining them as pending feedback.
  Ghost places belong to the rare builder mode: shown automatically for a family under three people,
  otherwise only after the quiet controls toggle; ordinary tree viewing shows none.
PRD_REF: docs/PRD.md#FAMILY-DESK
INVARIANTS:
- pending cards are browser and feedback state only and never become accepted graph people [review: engine lead]
- ambiguous card names never select a guessed person id [review: engine lead]
CHANGES_WITH:
- MOD-DESK-FEEDBACK (add_person and place envelope)
- MOD-DESK-SHOW (pending and reviewed feedback)
:END_MODULE_CONTRACT
*/
(async () => {
  if (!document.querySelector('#root')) return;
  const identity = await window.familiarDeskIdentity;
  if (identity?.role === 'reader') return;
  const [graph, show, words, profile] = await Promise.all(['/graph.json', '/desk/show.json', '/desk/words.json', '/reader-profile.json']
    .map(async path => (await fetch(path)).json()));
  const w = words.show, people = graph.people || {}, family = profile.family?.id || document.title;
  const storage = 'familiar-desk-pending:' + family;
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; };
  const display = id => {
    const person = people[id], name = person?.names?.[0];
    return name?.display || [name?.given, name?.patronymic, name?.surname].filter(Boolean).join(' ') || w.self;
  };
  const tileSelector = 'button.tree-tile[data-person]';
  const current = () => {
    const tile = document.querySelector('.world .tree-centre[data-person]');
    if (tile) return tile.dataset.person;
    const id = new URLSearchParams(location.hash.slice(1)).get('person');
    return people[id] ? id : graph.defaultViewer || graph.narrator || graph.root || Object.keys(people)[0] || 'self';
  };
  const cardPerson = card => card.dataset.person;
  let local = [];
  try { local = JSON.parse(localStorage.getItem(storage) || '[]'); } catch (_) { /* optional */ }
  const reviewed = new Set(show.reviewed_pending || []);
  let pending = [...new Map([...show.pending, ...local].filter(p => !reviewed.has(p.id)).map(p => [p.id, p])).values()];
  const save = () => { try { localStorage.setItem(storage, JSON.stringify(pending)); } catch (_) { /* server keeps received messages */ } };
  save();
  // One sheet adds one person with plain fields; the summary text stays the readable literal message.
  const dialog = el('dialog', 'desk-add-sheet'), form = el('form'), heading = el('h2');
  const beside = el('p', 'desk-beside', w.add_one_form);
  const whose = el('select', 'desk-whose'); whose.name = 'anchor';
  const year = id => (people[id]?.events || []).find(e => e.type === 'birth')?.date?.match(/\d{4}/)?.[0];
  const label = id => display(id) + (year(id) ? ' · ' + year(id) : '');
  for (const id of Object.keys(people).sort((a, b) => label(a).localeCompare(label(b)))) {
    const option = el('option', '', label(id)); option.value = id; whose.append(option);
  }
  whose.onchange = () => { context.anchor = whose.value; messageId = null; };
  const relations = el('div', 'desk-rel'); relations.setAttribute('role', 'group');
  const field = (key, wide = false) => {
    const box = el('label', wide ? 'desk-field wide' : 'desk-field', w['add_' + key]), input = el('input');
    input.name = key; input.placeholder = w['add_' + key + '_ex'] || ''; input.maxLength = 200; input.autocomplete = 'off';
    box.append(input); return box;
  };
  const choice = (name, options) => {
    const group = el('div', 'desk-choice'); group.setAttribute('role', 'group'); group.dataset.name = name;
    for (const value of options) {
      const button = el('button', '', w['add_' + name + '_' + value]); button.type = 'button'; button.value = value;
      button.setAttribute('aria-pressed', 'false');
      button.onclick = () => {
        const on = button.getAttribute('aria-pressed') !== 'true';
        for (const b of group.children) b.setAttribute('aria-pressed', String(on && b === button));
        sync();
      };
      group.append(button);
    }
    return group;
  };
  const picked = group => [...group.children].find(b => b.getAttribute('aria-pressed') === 'true')?.value || '';
  const kinWords = field('kin_words', true);
  const nameRow = el('div', 'desk-fields'), born = el('div', 'desk-fields'), died = el('div', 'desk-fields'), told = field('told_by', true);
  nameRow.append(field('surname'), field('given'), field('patronymic'), field('maiden_surname'));
  born.append(field('birth'), field('birth_place'));
  died.append(field('death'), field('death_place'));
  const living = choice('living', ['alive', 'dead', 'unknown']), known = choice('known_from', ['memory', 'told', 'document']);
  const note = el('label', 'desk-field wide', w.add_note), text = el('textarea', 'desk-say');
  text.name = 'note'; text.maxLength = 4000; text.rows = 3; text.placeholder = w.add_note_ex; note.append(text);
  const part = (key, ...nodes) => { const box = el('div', 'desk-part'); box.append(el('p', 'desk-part-title', w[key]), ...nodes); return box; };
  const many = el('p', 'desk-many', w.add_many);
  const status = el('p', 'desk-add-status'); status.setAttribute('role', 'status');
  const row = el('div', 'desk-sheet-row'), submit = el('button', 'desk-primary', words.send), close = el('button', '', words.close);
  submit.type = 'submit'; close.type = 'button'; close.onclick = () => dialog.close();
  row.append(submit, close);
  form.append(heading, beside, part('add_whose', whose), part('add_relation', relations, kinWords), nameRow, part('add_born', born),
    part('add_living', living, died), part('add_known_from', known, told), note, status, row, many);
  const sent = el('div', 'desk-add-done'), doneText = el('p', 'desk-add-done-text'), doneRow = el('div', 'desk-sheet-row');
  const more = el('button', 'desk-primary', w.add_more), finish = el('button', '', w.add_finish);
  more.type = 'button'; finish.type = 'button'; doneRow.append(more, finish); sent.append(doneText, doneRow, el('p', 'desk-many', w.add_many));
  sent.hidden = true; dialog.append(form, sent); document.body.append(dialog);
  const inputs = () => [...form.querySelectorAll('input,textarea')];
  let context = {}, relation = '', messageId = null;
  function sync() {
    died.hidden = picked(living) !== 'dead'; told.hidden = picked(known) !== 'told'; kinWords.hidden = relation !== 'relative';
    messageId = null; status.textContent = '';
  }
  function open(anchor, selected = '', place = '') {
    context = {anchor, place}; relation = selected; status.textContent = '';
    for (const input of inputs()) input.value = '';
    whose.value = anchor; whose.closest('.desk-part').hidden = selected === 'self' || !people[anchor];
    for (const group of [living, known]) for (const b of group.children) b.setAttribute('aria-pressed', 'false');
    form.hidden = false; sent.hidden = true; sync();
    close.textContent = ['self', 'mother', 'father', 'mothers_mother', 'mothers_father', 'fathers_mother', 'fathers_father'].includes(place) ? w.dont_know : words.close;
    heading.textContent = w.add_heading; relations.replaceChildren();
    const base = ['father', 'mother', 'sibling', 'child', 'spouse', 'relative'];
    const choices = selected === 'self' ? ['self'] : selected && !base.includes(selected) ? [selected, ...base] : base;
    for (const value of choices) {
      const button = el('button', '', w['add_rel_' + value]); button.type = 'button'; button.setAttribute('aria-pressed', String(value === relation));
      button.onclick = () => { relation = value; for (const b of relations.children) b.setAttribute('aria-pressed', String(b === button)); sync(); };
      relations.append(button);
    }
    sync();
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
    (relation ? form.querySelector('input[name=surname]') : relations.firstChild).focus({preventScroll: true});
  }
  window.familiarDeskAddPerson = (anchor, selected = '') => open(people[anchor] ? anchor : current(), selected);
  more.onclick = () => open(context.anchor);
  finish.onclick = () => dialog.close();
  function summary(person, rel) {
    const name = [person.surname, person.given, person.patronymic].filter(Boolean).join(' ');
    const lines = [(name || w['add_rel_' + rel]) + (person.maiden_surname ? ' (' + w.add_maiden_short + ' ' + person.maiden_surname + ')' : ''),
      (person.kin_words || w['add_rel_' + rel]) + ' · ' + display(context.anchor)];
    const line = (key, ...values) => { const v = values.filter(Boolean).join(', '); if (v) lines.push(w[key] + ': ' + v); };
    line('add_born', person.birth, person.birth_place);
    if (person.death || person.death_place) line('add_died', person.death, person.death_place);
    else if (person.living) lines.push(w['add_living_' + person.living]);
    if (person.known_from) line('add_known_from', w['add_known_from_' + person.known_from], person.told_by);
    if (person.note) lines.push('', person.note);
    return lines.join('\n');
  }
  form.onsubmit = async event => {
    event.preventDefault(); if (!window.familiarDeskSend) return;
    const person = {};
    for (const input of inputs()) if (input.value.trim() && !input.closest('[hidden]')) person[input.name] = input.value.trim();
    for (const group of [living, known]) if (picked(group)) person[group.dataset.name] = picked(group);
    if (!relation && !person.surname && !person.given && !person.kin_words) { status.textContent = w.add_need; return; }
    const rel = relation || 'relative';
    submit.disabled = true; status.textContent = words.sending; messageId ||= crypto.randomUUID();
    try {
      const item = await window.familiarDeskSend({id: messageId, kind: 'add_person', subject: context.anchor,
        ...context, person: context.anchor, where: w.beside_caption.replace('{name}', display(context.anchor)),
        relation: rel, new_person: person, text: summary(person, rel)});
      pending.push({...item, at: item.client_time}); save(); refresh(true);
      doneText.textContent = words.received + '. ' + w.add_done + '\n' + item.text.split('\n')[0];
      form.hidden = true; sent.hidden = false; more.focus({preventScroll: true});
    } catch (error) { status.textContent = error.message || words.failed; }
    finally { submit.disabled = false; }
  };
  form.oninput = () => { messageId = null; };
  let layer = null, fingerprint = '';
  const buildKey = 'familiar-desk-building:' + family;
  let building = false;
  try { building = sessionStorage.getItem(buildKey) === '1'; } catch (_) { /* session only */ }
  const toggle = el('button', 'desk-build');
  toggle.type = 'button';
  toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10" cy="8" r="3.5"/>'
    + '<path d="M3.5 20c.6-4 3.4-6 6.5-6 2.2 0 4.2 1 5.4 2.7"/><path d="M18.5 13.5v7M15 17h7"/></svg>';
  const hint = el('div', 'desk-build-hint'), done = el('button', '', w.build_done);
  done.type = 'button'; hint.append(el('span', '', w.build_hint), done);
  function setBuilding(value) {
    building = value;
    try { value ? sessionStorage.setItem(buildKey, '1') : sessionStorage.removeItem(buildKey); } catch (_) { /* session only */ }
    refresh(true);
  }
  toggle.onclick = () => setBuilding(!building); done.onclick = () => setBuilding(false);
  // One quiet line at the end of the person's card opens the sheet; the tree itself carries no entry but the builder toggle.
  const kin = el('p', 'desk-add-kin'), kinLink = el('button', 'link', '+ ' + w.add_person);
  kinLink.type = 'button'; kinLink.onclick = () => open(kin.dataset.person);
  kin.append(kinLink);
  function panelEntry() {
    const panel = document.querySelector('.panel[data-feedback-person]'), body = panel?.querySelector('.body');
    const id = panel?.dataset.feedbackPerson;
    if (!body || !people[id]) { kin.remove(); return; }
    kin.dataset.person = id;
    if (kin.parentNode !== body || kin.nextSibling) body.append(kin);
  }
  function controls() {
    const stage = document.querySelector('.stage');
    panelEntry();
    const group = document.querySelector('.stage .controls');
    toggle.setAttribute('aria-pressed', String(building));
    toggle.title = building ? w.build_done : w.build_tree; toggle.setAttribute('aria-label', toggle.title);
    if (group && !group.contains(toggle)) group.append(toggle);
    if (building && stage && !stage.contains(hint)) stage.append(hint);
    if (!building) hint.remove();
  }
  function builder(stage) {
    document.querySelector('.desk-builder-scene')?.remove();
    const scene = el('section', 'desk-builder-scene'), family = graph.families || [];
    const parents = id => { const row = family.find(f => f.children?.includes(id)); return [row?.wife, row?.husband]; };
    const self = current(), [mother, father] = parents(self), [mm, mf] = parents(mother), [fm, ff] = parents(father);
    const slots = [['self', self, 50, 80], ['mother', mother, 26, 49], ['father', father, 74, 49],
      ['mothers_mother', mm, 14, 18], ['mothers_father', mf, 38, 18], ['fathers_mother', fm, 62, 18], ['fathers_father', ff, 86, 18]];
    const count = slots.filter(([address, id]) => people[id] || pending.some(p => p.place === address)).length;
    scene.append(el('p', 'desk-builder-status', w.builder + ' · ' + count + ' / 7'));
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 100 100'); svg.setAttribute('preserveAspectRatio', 'none');
    const links = document.createElementNS(svg.namespaceURI, 'path'); links.setAttribute('d', 'M14 18H38M26 18V49M62 18H86M74 18V49M26 49H74M50 49V80'); svg.append(links); scene.append(svg);
    for (const [address, id, x, y] of slots) {
      const item = pending.find(p => p.place === address), known = people[id];
      const card = el(known || item ? 'article' : 'button', known ? 'desk-builder-person' : item ? 'desk-pending-card' : 'desk-ghost');
      card.style.left = x + '%'; card.style.top = y + '%'; card.style.transform = 'translate(-50%,-50%)';
      if (known) card.append(el('b', '', display(id)), el('small', '', w[address]));
      else if (item) card.append(el('b', '', item.text.split(/[\n,]/)[0].slice(0, 120)), el('small', '', w.pending));
      else { card.type = 'button'; card.append(el('span', 'desk-plus', '+'), el('span', '', w[address])); card.onclick = () => open(self, ['self', 'mother', 'father'].includes(address) ? address : 'parent', address); }
      scene.append(card);
    }
    stage.append(scene);
  }
  function coords(card) {
    const tile = card.parentElement;
    return {x: tile.offsetLeft, y: tile.offsetTop, width: tile.offsetWidth, height: tile.offsetHeight};
  }
  function refresh(force = false) {
    const world = document.querySelector('.stage .world');
    if (Object.keys(people).length < 3) {
      const stage = document.querySelector('.stage') || document.querySelector('#root');
      const key = 'builder:' + pending.map(p => p.id).join('|');
      if (!force && fingerprint === key && document.querySelector('.desk-builder-scene')) return;
      fingerprint = key; builder(stage); return;
    }
    if (!world) return;
    controls();
    const me = current(), pendingHere = pending.filter(p => p.anchor === me);
    if (!building && !pendingHere.length) { layer?.remove(); layer = null; return; }
    const cards = [...world.querySelectorAll(tileSelector)], anchor = cards.find(c => cardPerson(c) === me);
    const key = String(building) + world.style.transform + world.closest('.stage').clientHeight
      + cards.map(c => cardPerson(c) + c.parentElement.style.cssText).join('|') + me + pendingHere.map(p => p.id).join('|');
    if (!force && key === fingerprint && layer?.isConnected) return;
    fingerprint = key; layer?.remove(); layer = el('div', 'desk-tree-add-layer'); world.append(layer);
    const base = anchor ? coords(anchor) : {x: 240, y: 260, width: 150, height: 70};
    const centre = base.x + base.width / 2;
    const stage = world.closest('.stage'), camera = new DOMMatrix(world.style.transform), scale = camera.a || 1;
    const bounds = {left: -camera.e / scale + 8, top: -camera.f / scale + 24,
      right: (stage.clientWidth - camera.e) / scale - 8, bottom: (stage.clientHeight - camera.f - 65) / scale};
    const occupied = cards.map(coords);
    const overlaps = rect => occupied.some(o => rect.x < o.x + o.width + 10 && rect.x + rect.width + 10 > o.x
      && rect.y < o.y + o.height + 10 && rect.y + rect.height + 10 > o.y);
    function place(anchorId, relationName, address, x, y, item = null, title = null, openAs = relationName, narrow = null) {
      const phone = stage.clientWidth < 600;
      const width = narrow || Math.min(phone ? 80 : 150, bounds.right - bounds.left), height = item ? 100 : phone ? 85 : 90;
      const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
      const alternatives = [[x, y], [base.x, base.y + base.height + 30], [base.x - width - 25, base.y],
        [base.x + base.width + 25, base.y], [base.x, base.y - height - 25]];
      for (let py = bounds.top; py + height < bounds.bottom; py += 24)
        for (let px = bounds.left; px + width <= bounds.right; px += 24) alternatives.push([px, py]);
      const candidates = alternatives.map(([px, py]) => ({x: clamp(px, bounds.left, bounds.right - width),
        y: clamp(py, bounds.top, bounds.bottom - height), width, height}))
        // Nearest free spot to the intended place first, so a crowded row keeps the place beside the person.
        .sort((a, b) => Math.hypot(a.x - x, a.y - y) - Math.hypot(b.x - x, b.y - y));
      const preferred = candidates.find(r => !overlaps(r)
          && (relationName !== 'child' || r.y >= base.y + base.height + 20)
          && (relationName !== 'parent' || r.y + height <= base.y - 20)
          && (!sides[relationName] || endOfRow(r, sides[relationName])))
        || (sides[relationName] && candidates.find(r => !overlaps(r) && endOfRow(r, sides[relationName] === 'right' ? 'left' : 'right')));
      // Never between people of the same row: there it would read as a marriage or a missing child.
      // A parent place stays above the person even when the free room there is off the visible part.
      const location = preferred || (relationName === 'parent'
        ? {x: clamp(x, bounds.left, bounds.right - width), y: base.y - height - 45, width, height}
        : candidates.find(r => !overlaps(r) && !(sides[relationName] && inRow(r))));
      if (!location && !item) return;
      const spot = location || {x: clamp(x, bounds.left, bounds.right - width), y: clamp(y, bounds.top, bounds.bottom - height), width, height};
      x = spot.x; y = spot.y; occupied.push(spot);
      const card = el(item ? 'article' : 'button', item ? 'desk-pending-card' : 'desk-ghost');
      card.dataset.relation = relationName;
      card.style.left = x + 'px'; card.style.top = y + 'px'; card.style.width = width + 'px';
      card.onpointerdown = event => event.stopPropagation();
      if (item) { card.append(el('b', '', item.text.split(/[\n,]/)[0].slice(0, 120)), el('small', '', w['add_rel_' + item.relation] || item.relation), el('span', '', w.pending)); }
      else { card.type = 'button'; card.title = title || w['ghost_' + relationName] || w[relationName]; card.setAttribute('aria-label', card.title);
        // In a tight row the place is a plain plus; its name shows on hover and to screen readers.
        if (width < 100) { card.classList.add('compact'); card.append(el('span', 'desk-plus', '+')); } else card.append(el('span', 'desk-plus', '+'), el('span', '', card.title));
        card.onclick = () => open(anchorId, openAs, address); }
      layer.append(card);
      if (!preferred && relationName !== 'parent') return;
      const wire = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); wire.classList.add('desk-ghost-wire');
      const line = document.createElementNS(wire.namespaceURI, 'path');
      // Row places sit at the end of the row; a wire across other cards would mislead.
      if (sides[relationName]) return;
      const parent = relationName === 'parent', startY = parent ? base.y : base.y + base.height;
      const endY = parent ? y + height : y, endX = x + width / 2, middle = (startY + endY) / 2;
      line.setAttribute('d', `M${centre} ${startY}V${middle}H${endX}V${endY}`); wire.append(line); layer.prepend(wire);
    }
    // A spouse place goes on the free side, never between the person and an existing spouse;
    // a sibling place takes the other end of the same row.
    const row = occupied.filter(o => o.y < base.y + base.height && o.y + o.height > base.y);
    const spouseIds = (graph.families || []).flatMap(f => f.husband === current() ? [f.wife] : f.wife === current() ? [f.husband] : []);
    const spouseCard = cards.find(c => spouseIds.includes(cardPerson(c)));
    const spouseSide = spouseCard && coords(spouseCard).x > base.x ? 'left' : 'right';
    const sides = {spouse: spouseSide, sibling: spouseSide === 'right' ? 'left' : 'right'};
    const inRow = r => r.y < base.y + base.height && r.y + r.height > base.y;
    function endOfRow(r, side) {
      if (!inRow(r)) return false;
      return side === 'right' ? row.every(o => r.x >= o.x + o.width) : row.every(o => r.x + r.width <= o.x);
    }
    if (anchor) {
      const live = e => !['rejected', 'disproved'].includes(e.status);
      const sexOf = id => String(people[id]?.sex || '').toLowerCase();
      // Reader edges carry parent/child without a type; the missing parent is named by the known one's sex.
      const ups = (graph.edges || []).filter(e => live(e) && (e.child || e.to) === me && (e.parent || e.from)).map(e => e.parent || e.from);
      const hasFather = ups.some(id => sexOf(id) === 'm'), hasMother = ups.some(id => sexOf(id) === 'f');
      const parentAs = ups.length >= 2 || (hasFather && hasMother) ? '' : hasFather ? 'mother' : hasMother ? 'father' : 'parent';
      const spouseWord = sexOf(me) === 'm' ? w.ghost_wife : sexOf(me) === 'f' ? w.ghost_husband : null;
      // A new child joins the end of the row of children already drawn under the person.
      const kidIds = new Set((graph.edges || []).filter(e => live(e) && (e.parent || e.from) === me).map(e => e.child || e.to));
      const kids = cards.filter(c => kidIds.has(cardPerson(c))).map(coords).filter(r => r.y > base.y + base.height);
      const kidRight = kids.length ? Math.max(...kids.map(r => r.x + r.width)) : 0, kidLeft = kids.length ? Math.min(...kids.map(r => r.x)) : 0;
      // A full row still takes the place at its freer end: the place narrows rather than drops below the row.
      const wide = stage.clientWidth < 600 ? 80 : 150, roomy = bounds.right - kidRight - 25 >= wide, gap = roomy ? 25 : 12;
      const rightFree = bounds.right - kidRight - gap, leftFree = kidLeft - gap - bounds.left;
      const kidW = kids.length && !roomy ? Math.max(44, Math.min(wide, rightFree >= 44 ? rightFree : Math.max(rightFree, leftFree))) : null;
      const kidX = !kids.length ? base.x - 55 : kidW && rightFree < 44 && leftFree > rightFree ? kidLeft - gap - kidW : kidRight + gap;
      const kidY = kids.length ? Math.min(...kids.map(r => r.y)) : base.y + base.height + 55;
      const beside = side => side === 'right' ? base.width + 45 : -205;
      const slots = [['child', kidX - base.x, kidY - base.y, null, 'child'], ['spouse', beside(sides.spouse), 0, spouseWord, 'spouse'],
        ['sibling', beside(sides.sibling), 0, null, 'sibling'],
        ...(parentAs ? [['parent', -55, -135, w['add_rel_' + parentAs], parentAs]] : [])];
      for (const [rel, dx, dy, title, openAs] of slots) {
        const existing = pendingHere.some(p => rel === 'parent' ? ['father', 'mother', 'parent'].includes(p.relation) : p.relation === rel);
        if (building && !existing) place(me, rel, rel, base.x + dx, base.y + dy, null, title, openAs, rel === 'child' ? kidW : null);
      }
      let n = 0;
      for (const item of pendingHere) {
        const rel = ['father', 'mother', 'parent'].includes(item.relation) ? 'parent' : ['spouse', 'sibling'].includes(item.relation) ? item.relation : 'child';
        const x = sides[rel] ? base.x + (sides[rel] === 'right' ? base.width + 45 : -205) : rel === 'parent' ? base.x - 55 : kidX + n++ * 165;
        const y = rel === 'parent' ? base.y - 135 : ['spouse', 'sibling'].includes(rel) ? base.y : kidY;
        place(me, rel, item.place || rel, x, y, item);
      }
    }
  }
  let timer = null;
  document.addEventListener('contextmenu', event => {
    const card = event.target.closest('.world ' + tileSelector); if (!card) return;
    const id = cardPerson(card); if (!id) return; event.preventDefault(); open(id);
  });
  document.addEventListener('pointerdown', event => {
    // A second finger makes it a pinch, never a long press.
    clearTimeout(timer); if (!event.isPrimary) return;
    const card = event.target.closest('.world ' + tileSelector); if (!card || event.pointerType === 'mouse') return;
    const id = cardPerson(card); if (id) timer = setTimeout(() => open(id), 550);
  });
  for (const type of ['pointerup', 'pointercancel', 'pointermove']) document.addEventListener(type, () => clearTimeout(timer));
  const observer = new MutationObserver(() => refresh());
  observer.observe(document.querySelector('#root'), {subtree: true, childList: true, attributes: true, attributeFilter: ['style', 'data-feedback-person']});
  window.addEventListener('hashchange', () => refresh(true)); refresh();
  window.addEventListener('resize', () => refresh(true));
  document.addEventListener('transitionend', event => { if (event.target.matches('.world')) refresh(true); });
})();
