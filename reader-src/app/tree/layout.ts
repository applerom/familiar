import type {Model} from './model';

export type Tile = {
  id: string | null; key: string; x: number; y: number; w: number; h: number;
  gen: number; status: string; scale: number; color?: string; siblings: string[];
};
type Link = {key: string; d: string; gen: number; status: string; kind: 'parent' | 'union' | 'child'; color?: string};
type Box = {x0: number; x1: number; y0: number; y1: number};
export type Layout = {
  tiles: Tile[]; links: Link[]; width: number; height: number; box: Box; near: Box;
  axis: number; rootBottom: number; horizon: boolean; linkOffset: number;
  visible: Set<string>; collateral: string[]; beyond: string[];
};
type Ancestor = {id: string | null; key: string; gen: number; status: string; x: number; weight: number; parents: Ancestor[]};
const MAX_LEVEL = 9;
const HISTORY_LEVEL = 3; // The centre is generation one.
const DEFAULT_LEVEL = 5;
const HORIZON_Y = 18;
const PAD = 14;
const PERSPECTIVE = [.74, .56, .42, .38, .35, .32, .3];
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
    ({id, key: id, gen, status, x: 0, weight: 1, parents: []});
  const rows = [roots.map(id => person(id, 0, 'export'))];
  const people = new Map(rows[0].map(n => [n.id!, n]));
  const links: {child: Ancestor; parent: Ancestor; status: string}[] = [];
  for (let gen = 0; gen < rows.length && gen < level; gen++) {
    const next: Ancestor[] = [];
    for (const child of rows[gen]) {
      if (child.id === null) continue;
      m.parents(child.id).slots.forEach((slot, i) => {
        const status = slot ? m.connectionStatus(slot) : 'unknown';
        const existing = slot && people.get(slot.id);
        const parent = existing || (slot ? person(slot.id, gen + 1, status) : {
          id: null, key: JSON.stringify([child.id, i]), gen: gen + 1, status, x: 0, weight: 1, parents: [],
        });
        links.push({child, parent, status});
        if (existing) return;
        child.parents.push(parent);
        next.push(parent);
        if (slot) people.set(slot.id, parent);
      });
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

export function levelRange(m: Model, center: string) {
  const deepest = rootsFor(m, center).reduce((depth, id) =>
    Math.max(depth, ...Array.from(m.ancestorsOf(id).values(), a => a.n)), 0);
  const max = Math.min(MAX_LEVEL, deepest + 1);
  return {max, auto: Math.min(DEFAULT_LEVEL, max)};
}

/** Project older rows towards the horizon, then give overlapping tiles room horizontally. */
export function layoutTree(m: Model, center: string, viewport: number, level: number): Layout {
  const roots = rootsFor(m, center);
  const {rows, links: parentLinks} = ancestorRows(m, roots, level);
  const narrow = viewport < 560;
  const axis = viewport / 2;
  const region = Math.min(viewport - PAD * 2, 900);
  const lane = region / roots.length;
  for (const row of rows.slice().reverse())
    for (const node of row) node.weight = Math.max(1, node.parents.reduce((sum, p) => sum + p.weight, 0));
  rows[0].forEach((node, i) => place(node, axis - region / 2 + i * lane, axis - region / 2 + (i + 1) * lane));

  const tiles: Tile[] = [];
  const tileByKey = new Map<string, Tile>();
  const card = (id: string | null, key: string, gen: number, status: string, w: number): Tile => {
    const scale = scaleFor(gen);
    const name = id === null ? '' : m.info[id].treeName;
    const font = gen === 0 ? 16 : gen === 1 ? 14 : 12.5;
    const base = gen === 0 ? 68 : 58;
    const h = gen < HISTORY_LEVEL
      ? Math.max(base, Math.ceil(name.length * font * .56 / (w - 25)) * font * 1.22 + 33)
      : Math.max(24, Math.round(52 * scale));
    const siblings = id !== null && gen >= 0 ? m.siblingDeck(id) : [];
    return {id, key, gen, status, w, h, scale, x: 0, y: 0, siblings, color: id === null ? undefined : m.tone(id)?.color};
  };
  const widths = [narrow ? 152 : 188, narrow ? 126 : 144, narrow ? 104 : 106];
  const halo = (tile: Tile) => tile.siblings.length > 1 ? 16 : 0;
  const rowTiles = rows.map((row, gen) => {
    const scale = scaleFor(gen);
    const w = gen < HISTORY_LEVEL ? widths[gen] : Math.max(44, Math.round(widths[2] * scale));
    const ordered = [...row].sort((a, b) => a.x - b.x);
    const cards = ordered.map(n => card(n.id, n.key, gen, n.status, w));
    const desired = ordered.map((n, i) => gen === 0
      ? axis + (i - (ordered.length - 1) / 2) * (w + (narrow ? 35 : 72)) - w / 2
      : axis + (n.x - axis) * scale - w / 2);
    const gap = gen < HISTORY_LEVEL ? 17 : Math.max(9, Math.round(18 * scale));
    let right = -Infinity;
    cards.forEach((tile, i) => {
      tile.x = Math.max(desired[i], right + gap);
      right = tile.x + w;
    });
    const shift = (cards[0].x - desired[0] + cards.at(-1)!.x - desired.at(-1)!) / 2;
    for (const tile of cards) {
      tile.x -= shift;
      tileByKey.set(tile.key, tile);
    }
    return cards;
  });

  const last = rowTiles.length - 1;
  const horizon = last >= HISTORY_LEVEL;
  let y = horizon ? HORIZON_Y + 26 : PAD;
  for (let gen = last; gen >= 0; gen--) {
    const row = rowTiles[gen];
    const height = Math.max(...row.map(tile => tile.h));
    for (const tile of row) {
      tile.y = y + (height - tile.h) / 2;
      tiles.push(tile);
    }
    y += height + (gen >= HISTORY_LEVEL ? Math.max(12, Math.round(scaleFor(gen) * (narrow ? 32 : 39))) : narrow ? 26 : 34);
  }
  const rootBottom = Math.max(...rowTiles[0].map(tile => tile.y + tile.h));

  const links: Link[] = [];
  const midX = (tile: Tile) => tile.x + tile.w / 2;
  const parentPath = (child: Tile, parent: Tile) => parent.gen > child.gen
    ? curve(midX(child), child.y, midX(parent), parent.y + parent.h)
    : curve(midX(child), child.y, midX(parent), parent.y);
  for (const {child, parent, status} of parentLinks) {
    const from = tileByKey.get(child.key)!;
    const to = tileByKey.get(parent.key)!;
    links.push({key: JSON.stringify([child.key, parent.key]), d: parentPath(from, to), gen: parent.gen,
      status, kind: 'parent', color: to.color});
  }
  if (roots.length === 2) {
    const [a, b] = rowTiles[0];
    links.push({key: 'union', d: `M${a.x + a.w},${a.y + a.h / 2} L${b.x},${b.y + b.h / 2}`,
      gen: 0, status: m.connectionStatus(m.spouseConnection(roots[0], roots[1])), kind: 'union'});
  }

  const visible = new Set(tiles.flatMap(tile => tile.id === null ? [] : [tile.id]));
  const extras = m.spouses(center).filter(id => !visible.has(id) && !m.info[id].placeholder);
  const children = m.children(center).filter(id => !visible.has(id));
  let lower = rootBottom + 40;
  // Keep the closer part of each row readable on a phone; wider families can pan to the remaining children.
  for (const [ids, kind] of [[extras, 'union'], [children, 'child']] as const) {
    const row = ids.filter(id => !visible.has(id)).sort(m.bySeniority);
    const w = narrow ? 148 : 158;
    const wideChildren = new Map<string, {x: number; y: number; status: string; stops: number[]}>();
    row.forEach((id, i) => {
      const parents = m.parents(id);
      const slot = [...parents.slots, ...parents.extra].find(p => p?.id === center);
      const status = m.connectionStatus(kind === 'union' ? m.spouseConnection(center, id) : slot || {status: 'export'});
      const tile = card(id, id, -1, status, w);
      tile.x = axis + (i - (row.length - 1) / 2) * (w + 18) - w / 2;
      tile.y = lower;
      const focus = tileByKey.get(center)!;
      const shared = kind === 'child' && roots.length === 2 && roots.every(pid => parents.slots.some(p => p?.id === pid));
      const x = shared ? axis : midX(focus);
      const y = shared ? focus.y + focus.h / 2 : focus.y + focus.h;
      if (kind === 'child' && row.length > 12) {
        const key = JSON.stringify([x, status]);
        if (!wideChildren.has(key)) wideChildren.set(key, {x, y, status, stops: []});
        wideChildren.get(key)!.stops.push(midX(tile));
      } else {
        links.push({key: JSON.stringify([kind, center, id]), d: curve(x, y, midX(tile), lower), gen: 1, status, kind});
      }
      tiles.push(tile);
      visible.add(id);
    });
    // Share the long horizontal part of a wide sibling row. Each parent anchor
    // and level of certainty still gets its own path and one drop per child.
    let joint = lower - 12;
    for (const [key, {x, y, status, stops}] of wideChildren) {
      const left = Math.min(x, stops[0]), right = Math.max(x, stops.at(-1)!);
      const drops = stops.map(stop => `M${stop},${joint} V${lower}`).join(' ');
      const d = stops.length === 1 ? curve(x, y, stops[0], lower) :
        `M${x},${y} V${joint} M${left},${joint} H${right} ${drops}`;
      links.push({key: 'children:' + key, d, gen: 1, status, kind: 'child'});
      joint -= 3;
    }
    if (row.length) lower = Math.max(...tiles.map(tile => tile.y + tile.h)) + 26;
  }

  const bounds = (cards: Tile[]): Box => ({
    x0: Math.min(...cards.map(tile => tile.x)),
    x1: Math.max(...cards.map(tile => tile.x + tile.w + halo(tile))),
    y0: Math.min(...cards.map(tile => tile.y - (tile.siblings.length > 1 ? 14 : 0))),
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
  const scope = m.familyPeople.has(center) ? m.familyPeople : m.connectedFrom([center]);
  const farther = new Set(roots.flatMap(id => Array.from(m.ancestorsOf(id)).filter(([, a]) => a.n > level).map(([pid]) => pid)));
  const collateral: string[] = [], beyond: string[] = [];
  for (const id of scope) {
    if (visible.has(id)) continue;
    (farther.has(id) ? beyond : collateral).push(id);
  }
  return {
    tiles, links, width: Math.max(viewport + offset, box.x1 + PAD), height: box.y1 + PAD,
    box, near, axis: axis + offset, rootBottom, horizon, linkOffset: offset, visible, collateral, beyond,
  };
}

export {HISTORY_LEVEL, HORIZON_Y};
