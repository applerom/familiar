/*
START_MODULE_CONTRACT: MOD-DESK-SHOW-CLIENT
PURPOSE: Show recorded research shifts, every alternative and work volume with dateless client pagination.
PRD_REF: docs/PRD.md#FAMILY-DESK
INVARIANTS:
- research lines and narrator replies are rendered literally without fabricated activity [review: engine lead]
- question feedback carries the original safe question ID to the common inbox [review: engine lead]
CHANGES_WITH:
- MOD-DESK-SHOW (show.json)
- MOD-DESK-CLIENT (literal answer delivery)
:END_MODULE_CONTRACT
*/
(async () => {
  const root = new URL('../', document.currentScript.src);
  const [data, words, profile] = await Promise.all(['desk/show.json', 'desk/words.json', 'reader-profile.json']
    .map(async path => (await fetch(new URL(path, root))).json()));
  const interactive = !document.querySelector('meta[name="familiar-static-demo"]');
  const w = words.show, language = document.documentElement.lang;
  const el = (tag, cls, text) => {
    const node = document.createElement(tag); if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text; return node;
  };
  const fmt = (key, values) => Object.entries(values).reduce((s, [k, v]) => s.replaceAll('{' + k + '}', v), w[key]);
  const number = n => n.toLocaleString(language);
  // A caption counted with a number carries its forms as "one|few|many" (or "one|other") and agrees with it.
  const counted = (text, n) => {
    const forms = text.split('|'), rule = new Intl.PluralRules(language).select(n);
    return forms[rule === 'one' ? 0 : forms.length > 2 && rule !== 'few' ? 2 : Math.min(1, forms.length - 1)];
  };
  const heat = value => `color-mix(in oklab,var(--ember) ${Math.round(value * 100)}%,var(--version))`;
  const word = v => {
    if (v.state === 'firm') return w.firm;
    if (v.state === 'confirmed') return w.confirmed_pending;
    if (v.state === 'dropped') return w.dropped;
    const earlier = (v.series || []).slice(0, -1);
    const fell = earlier.some(x => x >= v.w + .05), rose = earlier.some(x => x <= v.w - .05);
    if (v.w < .2) return fell ? w.weakened : w.unlikely;
    if (v.w < .5) return w.possible;
    if (v.w < .9) return rose ? w.strengthened : w.probable;
    return w.near_certain;
  };
  const lanes = new Map(data.lanes.map((l, i) => [l.id, {...l, x: 10 + (i === 0 ? 0 : 12 + ((i - 1) % 4) * 12)}]));
  const shifts = document.querySelector('#show-shifts');
  for (const shift of data.shifts) {
    const row = el('li'), lane = lanes.get(shift.lane);
    row.append(el('strong', '', lane.title), el('span', '', shift.label + ' · ' + word({state: shift.state,
      w: shift.w_to, series: [shift.w_from, shift.w_to]})),
      el('small', '', `${Math.round(shift.w_from * 100)} → ${Math.round(shift.w_to * 100)}`));
    shifts.append(row);
  }
  if (!data.shifts.length) shifts.append(el('li', 'sub', w.no_shifts));
  // Narrator additions wait for the researcher; this browser's sends show before the next build.
  let local = [];
  try { local = JSON.parse(localStorage.getItem('familiar-desk-pending:' + (profile.family?.id || document.title)) || '[]'); } catch (_) { /* optional */ }
  const reviewed = new Set(data.reviewed_pending || []);
  const additions = [...new Map([...(data.pending || []), ...local].filter(p => !reviewed.has(p.id)).map(p => [p.id, p])).values()];
  for (const item of additions) {
    const row = el('li'); row.append(el('p', '', item.text), el('small', '', w.pending));
    document.querySelector('#show-added-list').append(row);
  }
  document.querySelector('#show-added').hidden = !additions.length;
  for (const [key, value] of Object.entries(data.summary)) {
    if (!value) continue;
    const cell = el('div'); cell.append(el('b', '', number(value)), el('span', '', counted(w['total_' + key], value)));
    document.querySelector('#show-summary').append(cell);
  }
  const coverage = values => ['zero', 'gap'].filter(key => values[key] > 0)
    .map(key => fmt('volume_' + key, {n: number(values[key])}));
  const volume = document.querySelector('#show-volume');
  volume.textContent = [...Object.entries(data.counters)
    .filter(([, value]) => value > 0)
    .map(([key, value]) => fmt('volume_' + key, {n: number(value)})), ...coverage(data.outcomes)].join(' · ');
  volume.hidden = !volume.textContent;
  const summary = document.querySelector('#show-summary');
  summary.hidden = !summary.children.length;
  summary.style.setProperty('--counter-count', Math.max(1, summary.children.length));
  const searched = data.search_coverage;
  if (searched) {
    document.querySelector('#show-searched').hidden = false;
    const fill = (id, key, values) => { document.querySelector(id).textContent = fmt(key, values); };
    fill('#searched-sources', 'searched_sources', {known: number(searched.known), checked: number(searched.checked)});
    fill('#searched-growth', 'searched_growth', {n: number(searched.new), days: searched.recent_days});
    document.querySelector('#searched-growth').hidden = !searched.new;
    fill('#searched-repeat', 'searched_repeat', {n: number(searched.repeated)});
    document.querySelector('#searched-repeat').hidden = !searched.repeated;
    fill('#searched-requests', searched.days ? 'searched_requests' : 'searched_requests_undated',
      {n: number(searched.requests), days: number(searched.days)});
    const peak = Math.max(1, ...searched.daily);
    searched.daily.forEach((count, index) => {
      const label = fmt('searched_day', {n: index + 1}), item = el('div', 'searched-day');
      const description = `${label}: ${number(count)}`;
      item.setAttribute('role', 'listitem'); item.setAttribute('aria-label', description); item.title = description;
      const bar = el('i'); bar.style.setProperty('--day-volume', `${100 * count / peak}%`); bar.setAttribute('aria-hidden', 'true');
      item.append(el('small', '', number(count)), bar, el('span', '', String(index + 1)));
      document.querySelector('#searched-days').append(item);
    });
    document.querySelector('#searched-days').setAttribute('aria-label', w.searched_days);
    if (searched.undated) {
      fill('#searched-undated', 'searched_undated', {n: number(searched.undated)});
      document.querySelector('#searched-undated').hidden = false;
    }
  }
  const categories = searched?.categories || {};
  const max = Math.max(1, ...Object.values(categories));
  for (const [kind, count] of Object.entries(categories)) {
    const row = el('div', 'source-volume'), bar = el('span', 'source-bar');
    bar.style.setProperty('--volume', 100 * count / max + '%'); bar.setAttribute('aria-hidden', 'true');
    row.append(el('span', '', w['searched_' + kind]), bar, el('b', '', number(count)));
    document.querySelector('#show-sources').append(row);
  }
  function gutter(row, event) {
    const lane = lanes.get(event.lane) || lanes.get('tree'), g = el('span', 'g');
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('viewBox', '0 0 66 100'); svg.setAttribute('preserveAspectRatio', 'none');
    const positions = new Set();
    for (const l of lanes.values()) {
      if (l.x > lane.x || positions.has(l.x)) continue;
      positions.add(l.x);
      const path = document.createElementNS(svg.namespaceURI, 'path');
      path.setAttribute('d', `M${l.x} 0V100`); path.setAttribute('stroke', l.id === 'tree' ? 'var(--act)' : 'var(--version)');
      path.setAttribute('opacity', l.id === event.lane ? '.8' : '.23'); svg.append(path);
    }
    g.append(svg);
    const node = el('i', 'node ' + (['find', 'settle'].includes(event.kind) ? 'gem' : event.kind === 'ask' ? 'asknode' : event.kind === 'fork' ? '' : 'fill'));
    node.style.left = lane.x + 'px'; node.style.setProperty('--h', event.kind === 'cool' ? 'var(--version)' : heat(event.w_to ?? .5));
    g.append(node); row.append(g);
  }
  for (const ask of data.asks) {
    const row = el('li', 'ask-row'), card = el('article', 'askcard'); gutter(row, {...ask, kind: 'ask'});
    const prompt = el('a', '', ask.text);
    prompt.href = 'desk/asks.html#ask-' + encodeURIComponent(ask.id);
    if (!document.querySelector('meta[name="familiar-static-demo"]')) prompt.href = '/' + prompt.getAttribute('href');
    card.append(el('span', 'lbl', ask.holder), el('p', '', ''));
    card.lastChild.append(prompt);
    row.append(card); document.querySelector('#show-asks').append(row);
  }
  const log = document.querySelector('#show-log'), pagination = document.querySelector('#show-pagination');
  let current = 0;
  function renderPage() {
    log.replaceChildren(); pagination.replaceChildren();
    for (const event of data.event_pages[current] || []) {
      const row = el('li', event.kind); gutter(row, event);
      const text = el('div', 't'); text.append(el('p', '', event.line)); row.append(text);
      const label = lanes.get(event.lane)?.title;
      if (label) row.append(el('small', '', label + (event.w_from != null ? ` · ${Math.round(event.w_from * 100)} → ${Math.round(event.w_to * 100)}` : '')));
      if (event.kind === 'work') row.append(el('small', '',
        [w['source_' + event.source_kind.replace('-', '_')], ...coverage(event)].join(' · ')));
      log.append(row);
    }
    if (!data.event_pages.length) log.append(el('li', 'start', w.no_events));
    if (data.event_pages.length < 2) return;
    for (const [delta, label] of [[-1, w.newer], [1, w.older]]) {
      const button = el('button', '', label); button.type = 'button';
      button.disabled = current + delta < 0 || current + delta >= data.event_pages.length;
      button.onclick = () => { current += delta; renderPage(); log.scrollIntoView({block: 'start'}); };
      pagination.append(button);
    }
    const status = el('span', '', fmt('page_n', {n: current + 1, total: data.event_pages.length}));
    status.setAttribute('aria-live', 'polite'); pagination.insertBefore(status, pagination.lastChild);
  }
  renderPage();
  for (const lane of data.lanes) {
    const versions = data.versions.filter(v => v.lane === lane.id); if (!versions.length) continue;
    const card = el('article', 'q'); card.append(el('h3', '', lane.title));
    for (const v of versions) {
      const row = el('div', 'v heat ' + v.state); row.style.setProperty('--w', (v.w * 100) + '%');
      const label = el('div', 'lw'); label.append(el('span', 'lab', v.label), el('span', 'word', word(v) + ' · ' + Math.round(v.w * 100)));
      const bar = el('div', 'bar'); bar.append(el('i')); row.append(label, bar);
      if (v.state === 'dropped' && v.reason) row.append(el('p', 'version-reason', v.reason));
      card.append(row);
    }
    if (lane.open && interactive) {
      const know = el('button', 'know-link', w.know_question); know.type = 'button';
      know.onclick = () => window.familiarDeskOpen?.({kind: 'remark', subject: lane.question,
        question: lane.question, finding: lane.title, where: w.progress + ' · ' + lane.title});
      card.append(know);
    }
    document.querySelector('#show-versions').append(card);
  }
})().catch(() => {
  const target = document.querySelector('#show-shifts');
  if (target) target.textContent = document.documentElement.lang === 'ru'
    ? 'Не удалось загрузить расследование. Обновите страницу.' : 'Could not load the investigation. Reload the page.';
});
