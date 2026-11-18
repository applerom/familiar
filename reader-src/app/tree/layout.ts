import type {Model} from './model';

export type Tile = {
  id: string; x: number; y: number; w: number; h: number;
  gen: number; status: string; scale: number; compact: boolean; fade: number; color?: string; stackLayers: number;
};
type Link = {key: string; d: string; gen: number; status: string; kind: 'parent' | 'union' | 'child' | 'more'; color?: string; ids: string[]};
type Box = {x0: number; x1: number; y0: number; y1: number};
export type Layout = {
  tiles: Tile[]; links: Link[]; width: number; height: number; box: Box; near: Box;
  axis: number; rootBottom: number; familyBottom: number; horizon: boolean; cut: boolean; linkOffset: number;
  visible: Set<string>; peopleCount: number; tightest: number;
};
type Ancestor = {id: string; gen: number; status: string; x: number; weight: number; parents: Ancestor[]};
const MAX_LEVEL = 9;
const HISTORY_LEVEL = 3; // The centre is generation one.
const HORIZON_Y = 14;
const PAD = 14;
const STACK_STEP = 4;
const RING = 4.5;
const BASE = 106; // The width a compact tile's scale is measured against.
const PERSPECTIVE = [.8, .66, .55, .47, .41, .36, .32];
const scaleFor = (gen: number) => gen < HISTORY_LEVEL ? 1 : PERSPECTIVE[gen - HISTORY_LEVEL];
const curve = (x1: number, y1: number, x2: number, y2: number) =>
  `M${x1},${y1} C${x1},${(y1 + y2) / 2} ${x2},${(y1 + y2) / 2} ${x2},${y2}`;

function rootsFor(m: Model, center: string) {
  const mate = m.spouses(center).find(id => !m.info[id].placeholder);
  if (!mate) return [center];
  return m.husbands.has(mate) && !m.husbands.has(center) ? [mate, center] : [center, mate];
}

/** Draw a shared ancestor once, at the closest generation; retain each child's link. */
function ancestorRows(m: Model, roots: string[], level: number) {
  const person = (id: string, gen: number, status: string): Ancestor =>
    ({id, gen, status, x: 0, weight: 1, parents: []});
  const rows = [roots.map(id => person(id, 0, 'export'))];
  const people = new Map(rows[0].map(n => [n.id, n]));
  const links: {child: Ancestor; parent: Ancestor; status: string}[] = [];
  for (let gen = 0; gen < rows.length && gen < level; gen++) {
    const next: Ancestor[] = [];
    for (const child of rows[gen]) {
      for (const slot of m.parents(child.id).slots) {
        // A nameless ancestor with nobody above adds no knowledge to the picture.
        if (!slot || m.info[slot.id].connector && !m.parents(slot.id).slots.some(Boolean)) continue;
        const status = m.connectionStatus(slot);
        const existing = people.get(slot.id);
        const parent = existing || person(slot.id, gen + 1, status);
        links.push({child, parent, status});
        if (existing) continue;
        child.parents.push(parent);
        next.push(parent);
        people.set(slot.id, parent);
      }
    }
    if (next.length) rows.push(next);
  }
  return {rows, links};
}

function place(node: Ancestor, a: number, b: number) {
  node.x = (a + b) / 2;
  const weight = (parent: Ancestor) => node.gen === 0 ? 1 : parent.weight + 1;
  const total = node.parents.reduce((sum, parent) => sum + weight(parent), 0);
  let left = a;
  for (const parent of node.parents) {
    const right = left + (b - a) * weight(parent) / total;
    place(parent, left, right);
    left = right;
  }
}

export function depthFor(m: Model, center: string) {
  const deepest = rootsFor(m, center).reduce((depth, id) =>
    Math.max(depth, ...Array.from(m.ancestorsOf(id).values(), a => a.n)), 0);
  return Math.min(MAX_LEVEL, deepest + 1);
}

/** How many generations of ancestors can be drawn, and how many the screen shows comfortably at first. */
export function levelRange(m: Model, center: string, viewport: number, room: number) {
  const max = Math.max(1, depthFor(m, center) - 1);
  // The first picture keeps every drawn row readable: names, not initials.
  let auto = 1;
  for (let level = Math.min(max, 5); level > 1; level--) {
    const drawn = layoutTree(m, center, viewport, level, room);
    if (drawn.tightest >= 44 && drawn.height * .7 <= room) { auto = level; break; }
  }
  return {max, auto: Math.max(auto, Math.min(2, max))};
}

/** Project older rows towards the horizon, then give overlapping tiles room horizontally. */
export function layoutTree(m: Model, center: string, viewport: number, level = depthFor(m, center), room = 0): Layout {
  const roots = rootsFor(m, center);
  const {rows, links: parentLinks} = ancestorRows(m, roots, level);
  const narrow = viewport < 560;
  const axis = viewport / 2;
  const budget = viewport - PAD * 2;
  const region = Math.min(budget, 900);
  const lane = region / roots.length;
  for (const row of rows.slice().reverse())
    for (const node of row) node.weight = Math.max(1, node.parents.reduce((sum, p) => sum + p.weight, 0));
  rows[0].forEach((node, i) => place(node, axis - region / 2 + i * lane, axis - region / 2 + (i + 1) * lane));

  // Two parents of one child stand close together; other neighbours keep a wider gap.
  const partner = new Map<string, string>();
  const parentsOf = new Map<string, string[]>();
  for (const {child, parent} of parentLinks) parentsOf.set(child.id, [...parentsOf.get(child.id) || [], parent.id]);
  for (const pair of parentsOf.values()) if (pair.length === 2) { partner.set(pair[0], pair[1]); partner.set(pair[1], pair[0]); }

  const tiles: Tile[] = [];
  const tileById = new Map<string, Tile>();
  // A tile is either a full card of a near generation or a compact one: a card drawn at `scale`,
  // narrower when its row has to share the width of the screen with many others.
  const card = (id: string, gen: number, status: string, w: number, compact = false): Tile => {
    const scale = compact ? Math.min(1.15, w / BASE) : 1;
    const name = m.info[id].treeName;
    const font = gen === 0 ? 16 : gen === 1 ? 14 : 12.5;
    const base = gen === 0 ? 68 : 58;
    const h = compact ? Math.max(8, Math.round(54 * scale))
      : Math.max(base, Math.ceil(name.length * font * .56 / (w - 25)) * font * 1.22 + 33);
    const stackLayers = gen >= 0 && w >= 40 ? m.siblingLayers(id) : 0;
    return {id, gen, status, w, h, scale, compact, fade: gen < HISTORY_LEVEL ? 1 : .34 + scaleFor(gen) * .66,
      x: 0, y: 0, stackLayers, color: m.tone(id)?.color};
  };
  const widths = [narrow ? 152 : 188, narrow ? 126 : 144, narrow ? 104 : BASE];
  let tightest = Infinity;
  let nearer = Infinity;
  let shared = false;
  const rowTiles = rows.map((row, gen) => {
    const depth = scaleFor(gen);
    const full = gen < HISTORY_LEVEL ? widths[gen] : Math.max(58, Math.round(widths[2] * depth));
    const ordered = [...row].sort((a, b) => a.x - b.x);
    const fullGap = (i: number) => (i && partner.get(ordered[i - 1].id) === ordered[i].id ? 22 : 30) * (gen < HISTORY_LEVEL ? 1 : depth);
    // Every row fits the width of the screen: a crowded row gets narrower tiles instead of running off the edge.
    const need = ordered.reduce((sum, n, i) => sum + full + (i ? fullGap(i) : 0) + m.siblingLayers(n.id) * STACK_STEP, 0);
    const share = gen === 0 ? 1 : Math.min(1, budget / need);
    if (share < 1) shared = true;
    // Farther is never larger: an older row does not outgrow the row below it.
    const w = Math.max(9, Math.min(nearer, Math.floor(full * share)));
    nearer = w;
    const fit = w / full;
    if (gen) tightest = Math.min(tightest, w);
    const cards = ordered.map(n => card(n.id, gen, n.status, w, gen >= HISTORY_LEVEL || fit < 1));
    const desired = ordered.map((n, i) => gen === 0
      ? axis + (i - (ordered.length - 1) / 2) * (w + (narrow ? 35 : 72)) - w / 2
      : axis + (n.x - axis) * depth - w / 2);
    const gap = (i: number) => Math.max(2, Math.round(fullGap(i) * fit));
    const wide = (tile: Tile) => tile.w + tile.stackLayers * STACK_STEP;
    let right = -Infinity;
    cards.forEach((tile, i) => {
      tile.x = Math.max(desired[i], right + gap(i));
      right = tile.x + wide(tile);
    });
    const shift = (cards[0].x - desired[0] + cards.at(-1)!.x - desired.at(-1)!) / 2;
    for (const tile of cards) tile.x -= shift;
    if (gen) {
      let edge = axis + budget / 2;
      for (let i = cards.length - 1; i >= 0; i--) {
        cards[i].x = Math.min(cards[i].x, edge - wide(cards[i]));
        edge = cards[i].x - gap(i);
      }
      edge = axis - budget / 2;
      cards.forEach((tile, i) => {
        tile.x = Math.max(tile.x, edge + (i ? gap(i) : 0));
        edge = tile.x + wide(tile);
      });
    }
    for (const tile of cards) tileById.set(tile.id, tile);
    return cards;
  });

  const last = rowTiles.length - 1;
  // People whose parents wait above the drawn generations: a short dotted stub leads into the fog.
  const cut = rowTiles.flat().filter(tile => m.parents(tile.id).slots.some(slot =>
    slot && !tileById.has(slot.id) && !(m.info[slot.id].connector && !m.parents(slot.id).slots.some(Boolean))));
  const horizon = last >= HISTORY_LEVEL || cut.length > 0;
  // Cut rows start lower: the haze covers the stubs that lead further up, not the people themselves.
  const top = cut.length ? HORIZON_Y + PAD + 30 : horizon ? HORIZON_Y + PAD : PAD;
  const heights = rowTiles.map(row => Math.max(...row.map(tile => tile.h)));
  const below = rowTiles.map((_, gen) => gen >= HISTORY_LEVEL ? Math.max(12, Math.round(scaleFor(gen) * (narrow ? 32 : 39))) : narrow ? 26 : 34);
  // When the width of the screen sets the size, the rows spread to use its height as well.
  const hasChildren = roots.some(id => m.children(id).length > 0);
  const natural = top + heights.reduce((a, b) => a + b, 0) + below.slice(1).reduce((a, b) => a + b, 0) + (hasChildren ? 118 : 0) + PAD;
  const spread = shared && last && room > natural ? Math.min(44, (room - natural) / last) : 0;
  let y = top;
  for (let gen = last; gen >= 0; gen--) {
    for (const tile of rowTiles[gen]) {
      tile.y = y + (heights[gen] - tile.h) / 2;
      tiles.push(tile);
    }
    y += heights[gen] + below[gen] + spread;
  }
  const rootBottom = Math.max(...rowTiles[0].map(tile => tile.y + tile.h));

  const links: Link[] = [];
  const midX = (tile: Tile) => tile.x + tile.w / 2;
  for (const tile of cut) {
    const rise = Math.max(10, Math.round(22 * tile.scale));
    links.push({key: 'more:' + tile.id, d: `M${midX(tile)},${tile.y} v${-rise}`, gen: tile.gen, status: 'hypothesis',
      kind: 'more', color: tile.color, ids: [tile.id]});
  }
  // A couple is joined by a ring; their child hangs from the ring, not from each parent separately.
  const knot = (left: Tile, right: Tile) => {
    const from = left.x + left.w + left.stackLayers * STACK_STEP;
    const r = Math.max(1, Math.min(Math.max(2.5, RING * left.scale), (right.x - from) / 2 - .5));
    const x = (from + right.x) / 2;
    const y = left.y + left.h / 2;
    return {x, y: y + r, bottom: Math.max(left.y + left.h, right.y + right.h),
      d: `M${left.x + left.w},${y} H${x - r} M${x + r},${y} H${right.x} M${x - r},${y} a${r},${r} 0 1,0 ${r * 2},0 a${r},${r} 0 1,0 ${-r * 2},0`};
  };
  const drop = (from: {x: number; y: number; bottom: number}, x: number, y: number) =>
    `M${from.x},${from.y} V${from.bottom} C${from.x},${(from.bottom + y) / 2} ${x},${(from.bottom + y) / 2} ${x},${y}`;
  const uncertain = (status: string) => status === 'hypothesis' || status === 'probable';
  const byChild = new Map<string, typeof parentLinks>();
  for (const link of parentLinks) byChild.set(link.child.id, [...byChild.get(link.child.id) || [], link]);
  const couples = new Set<string>();
  for (const [childId, pair] of byChild) {
    const child = tileById.get(childId)!;
    const [a, b] = pair.map(link => tileById.get(link.parent.id)!).sort((p, q) => p.x - q.x);
    const row = b && a.gen === b.gen && a.gen === child.gen + 1 ? rowTiles[a.gen] : null;
    if (pair.length === 2 && row && row.indexOf(b) - row.indexOf(a) === 1) {
      const joint = knot(a, b);
      const key = JSON.stringify([a.id, b.id]);
      if (!couples.has(key)) {
        couples.add(key);
        links.push({key: 'couple:' + key, d: joint.d, gen: a.gen, status: 'export', kind: 'union', ids: [a.id, b.id]});
      }
      const status = pair.find(link => uncertain(link.status))?.status || pair[0].status;
      links.push({key: JSON.stringify([childId, a.id, b.id]), d: drop(joint, midX(child), child.y), gen: a.gen,
        status, kind: 'parent', color: child.color, ids: [childId, a.id, b.id]});
      continue;
    }
    for (const {parent, status} of pair) {
      const to = tileById.get(parent.id)!;
      const d = to.gen > child.gen ? curve(midX(child), child.y, midX(to), to.y + to.h) : curve(midX(child), child.y, midX(to), to.y);
      links.push({key: JSON.stringify([childId, parent.id]), d, gen: to.gen, status, kind: 'parent', color: to.color, ids: [childId, parent.id]});
    }
  }
  const rootJoint = roots.length === 2 ? knot(rowTiles[0][0], rowTiles[0][1]) : null;
  if (rootJoint) {
    links.push({key: 'union', d: rootJoint.d, gen: 0, kind: 'union', ids: [...roots],
      status: m.connectionStatus(m.spouseConnection(roots[0], roots[1]))});
  }

  const visible = new Set(tiles.map(tile => tile.id));
  const extras = m.spouses(center).filter(id => !m.info[id].placeholder);
  const children = new Set(roots.flatMap(id => m.children(id)));
  let lower = rootBottom + (narrow ? 30 : 40);
  let familyBottom = rootBottom;
  // Keep the closer part of each row readable on a phone; wider families can pan to the remaining children.
  for (const [ids, kind] of [[children, 'child'], [extras, 'union']] as const) {
    // Children of the left parent alone stand left, shared ones in the middle: the lines never cross.
    const side = (id: string) => {
      const mine = [...m.parents(id).slots, ...m.parents(id).extra].map(p => p?.id);
      const [a, b] = roots.map(pid => mine.includes(pid));
      return kind !== 'child' || roots.length < 2 || a === b ? 1 : a ? 0 : 2;
    };
    const row = [...ids].filter(id => !visible.has(id)).sort((a, b) => side(a) - side(b) || m.bySeniority(a, b));
    const w = narrow ? 148 : 158;
    const wideChildren = new Map<string, {x: number; y: number; status: string; stops: number[]}>();
    row.forEach((id, i) => {
      const parents = m.parents(id);
      const parentSlots = [...parents.slots, ...parents.extra];
      const slot = parentSlots.find(p => p?.id === center) || parentSlots.find(p => p && roots.includes(p.id));
      const status = m.connectionStatus(kind === 'union' ? m.spouseConnection(center, id) : slot || {status: 'export'});
      const tile = card(id, -1, status, w);
      tile.x = axis + (i - (row.length - 1) / 2) * (w + 18) - w / 2;
      tile.y = lower;
      const focus = tileById.get(kind === 'child' && slot ? slot.id : center)!;
      const shared = kind === 'child' && roots.length === 2 && roots.every(pid => parents.slots.some(p => p?.id === pid));
      const from = shared && rootJoint ? rootJoint : {x: midX(focus), y: focus.y + focus.h, bottom: focus.y + focus.h};
      const x = from.x, y = from.y;
      if (kind === 'child' && row.length > 12) {
        const key = JSON.stringify([x, status]);
        if (!wideChildren.has(key)) wideChildren.set(key, {x, y, status, stops: []});
        wideChildren.get(key)!.stops.push(midX(tile));
      } else {
        links.push({key: JSON.stringify([kind, center, id]), d: drop(from, midX(tile), lower), gen: 1, status, kind,
          ids: shared ? [id, ...roots] : [id, focus.id]});
      }
      tiles.push(tile);
      visible.add(id);
      if (kind === 'child') familyBottom = Math.max(familyBottom, tile.y + tile.h);
    });
    // Share the long horizontal part of a wide sibling row. Each parent anchor
    // and level of certainty still gets its own path and one drop per child.
    let joint = lower - 12;
    for (const [key, {x, y, status, stops}] of wideChildren) {
      const left = Math.min(x, stops[0]), right = Math.max(x, stops.at(-1)!);
      const drops = stops.map(stop => `M${stop},${joint} V${lower}`).join(' ');
      const d = stops.length === 1 ? curve(x, y, stops[0], lower) :
        `M${x},${y} V${joint} M${left},${joint} H${right} ${drops}`;
      links.push({key: 'children:' + key, d, gen: 1, status, kind: 'child', ids: []});
      joint -= 3;
    }
    if (row.length) lower = familyBottom + 26;
  }

  const bounds = (cards: Tile[]): Box => ({
    x0: Math.min(...cards.map(tile => tile.x)),
    x1: Math.max(...cards.map(tile => tile.x + tile.w + tile.stackLayers * STACK_STEP)),
    y0: Math.min(...cards.map(tile => tile.y - tile.stackLayers * STACK_STEP)),
    y1: Math.max(...cards.map(tile => tile.y + tile.h)),
  });
  const box = bounds(tiles);
  const near = bounds(tiles.filter(tile => tile.gen >= 0 && tile.gen < HISTORY_LEVEL));
  const offset = Math.max(0, PAD - box.x0);
  if (offset) {
    // Translate the whole figure once so the pan bounds also include the leftmost tile.
    for (const tile of tiles) tile.x += offset;
    for (const b of [box, near]) { b.x0 += offset; b.x1 += offset; }
  }
  const peopleCount = m.familyPeople.has(center) ? m.familyPeople.size : m.connectedFrom([center]).size;
  return {
    tiles, links, width: Math.max(viewport + offset, box.x1 + PAD), height: box.y1 + PAD,
    box, near, axis: axis + offset, rootBottom, familyBottom, horizon, cut: cut.length > 0, linkOffset: offset, visible, peopleCount, tightest,
  };
}

export {HISTORY_LEVEL, HORIZON_Y, STACK_STEP};
