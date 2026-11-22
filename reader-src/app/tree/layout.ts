import type {Model, Slot} from './model';

export type Tile = {
  id: string; x: number; y: number; w: number; h: number;
  gen: number; status: string; scale: number; compact: boolean; fade: number; color?: string; stackLayers: number;
  /** A generation nobody has found yet, between a person and a possible ancestor: drawn as haze, not as a card. */
  gap?: boolean;
  /** On a missing generation: who in the tree may stand there (the possible ancestor's own child of a fitting age). */
  hint?: string;
  /** On the family's main line, reached by an assumption rather than a document: a light haze behind the card. */
  assumed?: boolean;
};
type Link = {key: string; d: string; gen: number; status: string; kind: 'parent' | 'union' | 'child' | 'more'; color?: string; ids: string[]};
type Box = {x0: number; x1: number; y0: number; y1: number};
export type Layout = {
  tiles: Tile[]; links: Link[]; width: number; height: number; box: Box; near: Box;
  /** What the first picture must show whole: the centre, the spouse and the ancestors. A row of children wider than
   * that runs past the edges and pans sideways; it never shrinks the parents to initials. */
  frame: Box;
  axis: number; rootBottom: number; familyBottom: number; horizon: boolean; cut: boolean; linkOffset: number;
  visible: Set<string>; peopleCount: number; tightest: number;
};
type Ancestor = {id: string; gen: number; status: string; x: number; weight: number; parents: Ancestor[]; gap?: boolean; hint?: string; color?: string; main?: boolean; assumed?: boolean};
const DOUBT: Record<string, number> = {probable: 1, hypothesis: 2, weak: 3};
/** A branch is as firm as its weakest link below: ancestors above a probable link stay probable. */
const weaker = (a: string, b: string) => (DOUBT[a] || 0) >= (DOUBT[b] || 0) ? a : b;
const MAX_LEVEL = 9;
const HISTORY_LEVEL = 3; // The centre is generation one.
const HORIZON_Y = 14;
const PAD = 14;
const STACK_STEP = 4;
const RING = 5;
const BASE = 106; // The width a compact tile's scale is measured against.
const GAP_W = 26; // A missing generation is a narrow band of haze.
const PERSPECTIVE = [.8, .66, .55, .47, .41, .36, .32];
const scaleFor = (gen: number) => gen < HISTORY_LEVEL ? 1 : PERSPECTIVE[gen - HISTORY_LEVEL];
const curve = (x1: number, y1: number, x2: number, y2: number) =>
  `M${x1},${y1} C${x1},${(y1 + y2) / 2} ${x2},${(y1 + y2) / 2} ${x2},${y2}`;

/** Lines a name takes when it breaks between words only. */
function wrapped(name: string, room: number) {
  let lines = 1, used = 0;
  for (const word of name.split(' ')) {
    if (used && used + 1 + word.length > room) { lines++; used = word.length; }
    else used += (used ? 1 : 0) + word.length;
  }
  return lines;
}

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
  const row = (gen: number) => rows[gen] || (rows[gen] = []);
  for (let gen = 0; gen < rows.length && gen < level; gen++) {
    for (const child of rows[gen]) {
      if (child.gap) continue;
      for (const slot of m.parents(child.id).slots) {
        // A nameless ancestor with nobody above adds no knowledge to the picture.
        if (!slot || m.info[slot.id].connector && !m.parents(slot.id).slots.some(Boolean)) continue;
        // A weak branch (the leading origin below 0.3) is 'weak' all the way up.
        // On the family's main line every link keeps its own form: a document solid, an assumption dotted.
        const main = !!(child.main || slot.main);
        const own = slot.main ? m.connectionLevel(slot) === 1 ? m.connectionStatus(slot) : 'probable'
          : slot.weak ? main ? 'probable' : 'weak' : m.connectionStatus(slot);
        const status = gen && !main ? weaker(child.status, own) : own;
        const existing = people.get(slot.id);
        const gap = existing ? 0 : slot.gap || 0;
        // A possible ancestor beyond the drawn generations waits behind the stub into the fog.
        if (gap && gen + 1 + gap > level) continue;
        // Missing generations keep their rows, so the ancestor and everyone above stand at their own generation.
        let below = child;
        const second = m.secondWay(child.id);
        for (let i = 1; i <= gap; i++) {
          const haze: Ancestor = {...person(`gap:${child.id}:${slot.id}:${i}`, gen + i, status), gap: true, color: m.tone(slot.id)?.color, main,
            hint: i === gap && second?.kind === 'between' && second.above === slot.id ? second.via : undefined};
          links.push({child: below, parent: haze, status});
          below.parents.push(haze);
          row(gen + i).push(haze);
          below = haze;
        }
        const parent = existing || {...person(slot.id, gen + 1 + gap, status), main, assumed: main && !gap && own !== 'export' && own !== 'verified'};
        links.push({child: below, parent, status});
        if (existing) continue;
        below.parents.push(parent);
        row(gen + 1 + gap).push(parent);
        people.set(slot.id, parent);
      }
    }
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

  // Two crowns grow from the couple: the husband's ancestors and the wife's; for a centre alone, the father's and
  // the mother's. Each crown recedes towards the horizon above its own root, and the sky between the crowns stays
  // open all the way up: a long line rises alone instead of leaning over the other family.
  const crownLevel = roots.length === 2 ? 0 : 1;
  const crowns = roots.length === 2 ? rows[0] : rows[0][0].parents.length === 2 ? rows[0][0].parents : [];
  if (crownLevel && crowns.length) crowns.forEach((node, i) => place(node, axis - region / 2 + i * region / 2, axis + i * region / 2));
  const up = new Map<string, Ancestor[]>();
  for (const {child, parent} of parentLinks) up.set(child.id, [...up.get(child.id) || [], parent]);
  const reached = crowns.map(root => {
    const seen = new Set([root.id]), queue = [root];
    for (const node of queue) for (const p of up.get(node.id) || []) if (!seen.has(p.id)) { seen.add(p.id); queue.push(p); }
    return seen;
  });
  // 0 the left crown, 1 the right one, 2 an ancestor of both: drawn once, in the sky between them, the one thing there.
  const crownOf = (id: string) => reached.length < 2 ? 0 : reached[0].has(id) ? reached[1].has(id) ? 2 : 0 : 1;
  // Half the sky: as wide as a couple's gap at the crowns' roots, a little wider with every older row.
  const sky = (gen: number) => gen <= crownLevel ? 11 : (narrow ? 10 : 16) + (gen - crownLevel - 1) * (narrow ? 2 : 4);

  // Two parents of one child stand close together; other neighbours keep a wider gap.
  const partner = new Map<string, string>();
  const parentsOf = new Map<string, string[]>();
  for (const {child, parent} of parentLinks) parentsOf.set(child.id, [...parentsOf.get(child.id) || [], parent.id]);
  for (const pair of parentsOf.values()) if (pair.length === 2) { partner.set(pair[0], pair[1]); partner.set(pair[1], pair[0]); }
  const tone = (n: Ancestor) => n.gap ? n.color : m.tone(n.id)?.color;

  const tiles: Tile[] = [];
  const tileById = new Map<string, Tile>();
  // A tile is either a full card of a near generation or a compact one: a card drawn at `scale`,
  // narrower when its row has to share the width of the screen with many others.
  const card = (id: string, gen: number, status: string, w: number, compact = false): Tile => {
    const scale = compact ? Math.min(1.15, w / BASE) : 1;
    const name = m.info[id]?.treeName || '';
    const font = gen === 0 ? 16 : gen === 1 ? 14 : 12.5;
    const base = gen === 0 ? 68 : 58;
    const h = compact ? Math.max(8, Math.round(54 * scale))
      : Math.max(base, wrapped(name, Math.floor((w - 25) / (font * .58))) * font * 1.22 + 33);
    const stackLayers = id && gen >= 0 && w >= 40 ? m.siblingLayers(id) : 0;
    return {id, gen, status, w, h, scale, compact, fade: gen < HISTORY_LEVEL ? 1 : .34 + scaleFor(gen) * .66,
      x: 0, y: 0, stackLayers, color: id ? m.tone(id)?.color : undefined};
  };
  const widths = [narrow ? 152 : 188, narrow ? 126 : 144, narrow ? 104 : BASE];
  let tightest = Infinity;
  // Farther is never larger: an older row does not outgrow the row below it.
  let nearer = Infinity;
  const wide = (tile: Tile) => tile.w + tile.stackLayers * STACK_STEP;
  const fullWidth = (gen: number) => gen < HISTORY_LEVEL ? widths[gen] : Math.max(58, Math.round(widths[2] * scaleFor(gen)));
  // Partners stand close; two lines of different colour keep a clearly wider gap than neighbours within a line.
  const gapsOf = (ordered: Ancestor[], gen: number) => (i: number) => (!i ? 30 : partner.get(ordered[i - 1].id) === ordered[i].id ? 22
    // On a phone the near rows spend that width on names instead.
    : tone(ordered[i - 1]) !== tone(ordered[i]) && !(narrow && gen < HISTORY_LEVEL) ? 52 : 30) * (gen < HISTORY_LEVEL ? 1 : scaleFor(gen));
  const needOf = (ordered: Ancestor[], gen: number) => {
    const fullGap = gapsOf(ordered, gen), full = fullWidth(gen);
    return ordered.reduce((sum, n, i) => sum + (n.gap ? GAP_W : full) + (i ? fullGap(i) : 0) + (n.gap ? 0 : m.siblingLayers(n.id) * STACK_STEP), 0);
  };
  const split = (row: Ancestor[]) => [0, 2, 1].map(crown => row.filter(n => crownOf(n.id) === crown));
  // The sky rises from between the couple (for a centre alone, from the centre's tile); within that window it stands
  // where the two crowns share the width most fairly, so a crown traced far and wide gets the room it needs.
  let seam = NaN;
  const findSeam = (pair: Tile[]) => {
    const [from, to] = pair.length === 2 ? [pair[0].x + wide(pair[0]) + sky(1), pair[1].x - sky(1)] : [pair[0].x + 24, pair[0].x + pair[0].w - 24];
    const needs = rows.slice(crownLevel + 1).map((row, i) => {
      const gen = crownLevel + 1 + i, [l, b, r] = split(row);
      return {clear: sky(gen) + needOf(b, gen) / 2, l: needOf(l, gen), r: needOf(r, gen)};
    });
    let best = axis, score = -1;
    for (let at = Math.ceil(from); at <= to; at += 2) {
      const fair = Math.min(1, ...needs.map(({clear, l, r}) => Math.min(l ? (at - clear - axis + budget / 2) / l : 1, r ? (axis + budget / 2 - at - clear) / r : 1)));
      if (fair > score + 1e-6 || fair > score - 1e-6 && Math.abs(at - axis) < Math.abs(best - axis)) { score = fair; best = at; }
    }
    return best;
  };
  let pair: Tile[] = [];
  const rowTiles = rows.map((row, gen) => {
    const depth = scaleFor(gen);
    const full = fullWidth(gen);
    // Every part of a row fits its room: a crowded crown gets narrower tiles instead of taking the other's half.
    // One generation, one size on both sides: a tile across the sky is never nearer than its own row.
    const sized = (ordered: Ancestor[], room: number) => ordered.length ? Math.floor(full * Math.min(1, Math.max(0, room) / needOf(ordered, gen))) : Infinity;
    const size = (...parts: [Ancestor[], number][]) => {
      const w = gen === 0 ? full : Math.max(9, Math.min(nearer, ...parts.map(([ordered, room]) => sized(ordered, room))));
      nearer = w;
      if (gen) tightest = Math.min(tightest, w);
      return w;
    };
    // Lay one crown's part of the row between lo and hi, receding towards the crown's own vanishing point.
    const lay = (ordered: Ancestor[], w: number, lo: number, hi: number, vanish: number) => {
      if (!ordered.length) return [];
      const fullGap = gapsOf(ordered, gen);
      const fit = w / full;
      const cards = ordered.map(n => {
        const tile = card(n.gap ? '' : n.id, gen, n.status, w, gen >= HISTORY_LEVEL || fit < 1);
        if (n.assumed) tile.assumed = true;
        return n.gap ? {...tile, id: n.id, w: Math.min(w, Math.max(10, Math.round(GAP_W * Math.min(1, depth)))), stackLayers: 0, color: n.color, gap: true, hint: n.hint} : tile;
      });
      // A couple whose parents are drawn stands apart, each under the own parents, so the branches rise evenly;
      // with nobody above, the two stand close.
      const apart = rows.length > 1 && ordered.length > 1;
      const desired = ordered.map((n, i) => gen === 0 && !apart
        ? axis + (i - (ordered.length - 1) / 2) * (w + (narrow ? 35 : 72)) - w / 2
        : vanish + (n.x - vanish) * depth - cards[i].w / 2);
      const gap = (i: number) => Math.max(2, Math.round(fullGap(i) * fit));
      let right = -Infinity;
      cards.forEach((tile, i) => {
        tile.x = Math.max(desired[i], right + gap(i));
        right = tile.x + wide(tile);
      });
      const shift = (cards[0].x - desired[0] + cards.at(-1)!.x - desired.at(-1)!) / 2;
      for (const tile of cards) tile.x -= shift;
      if (gen) {
        let edge = hi;
        for (let i = cards.length - 1; i >= 0; i--) {
          cards[i].x = Math.min(cards[i].x, edge - wide(cards[i]));
          edge = cards[i].x - gap(i);
        }
        edge = lo;
        cards.forEach((tile, i) => {
          tile.x = Math.max(tile.x, edge + (i ? gap(i) : 0));
          edge = tile.x + wide(tile);
        });
      }
      return cards;
    };
    const ordered = [...row].sort((a, b) => a.x - b.x);
    let cards: Tile[];
    // On a phone the near rows (parents, grandparents) keep names readable and share the whole width: the crowns stay
    // in order, the gap between them is the gap between two lines; the sky opens above, in the historical rows.
    const near = narrow && gen < HISTORY_LEVEL && !ordered.some(n => crownOf(n.id) === 2);
    if (gen === 0 || crowns.length < 2 || near) cards = lay(ordered, size([ordered, budget]), axis - budget / 2, axis + budget / 2, crowns[0]?.x ?? axis);
    else {
      if (Number.isNaN(seam)) seam = findSeam(pair);
      const [left, both, right] = split(ordered);
      const room = sky(gen) + needOf(both, gen) / 2;
      const w = size([both, budget / 3], [left, seam - room - axis + budget / 2], [right, axis + budget / 2 - seam - room]);
      // A shared ancestor stands in the middle of the sky, and its branches cross the sky to both crowns.
      const middle = lay(both, w, seam - budget / 6, seam + budget / 6, seam);
      let clear = sky(gen);
      if (middle.length) {
        const x0 = middle[0].x, x1 = middle.at(-1)!.x + wide(middle.at(-1)!);
        for (const tile of middle) tile.x += seam - (x0 + x1) / 2;
        clear += (x1 - x0) / 2;
      }
      cards = [...lay(left, w, axis - budget / 2, seam - clear, crowns[0].x), ...middle, ...lay(right, w, seam + clear, axis + budget / 2, crowns[1].x)];
    }
    if (gen === 0) pair = cards;
    for (const tile of cards) tileById.set(tile.id, tile);
    return cards;
  });

  const last = rowTiles.length - 1;
  // People whose parents wait above the drawn generations: a short dotted stub leads into the fog.
  const cut = rowTiles.flat().filter(tile => !tile.gap && m.parents(tile.id).slots.some(slot =>
    slot && !tileById.has(slot.id) && !(m.info[slot.id].connector && !m.parents(slot.id).slots.some(Boolean))));
  const horizon = last >= HISTORY_LEVEL || cut.length > 0;
  // Cut rows start lower: the haze covers the stubs that lead further up, not the people themselves.
  const top = cut.length ? HORIZON_Y + PAD + 30 : horizon ? HORIZON_Y + PAD : PAD;
  const heights = rowTiles.map(row => Math.max(...row.map(tile => tile.h)));
  // Near rows leave room for the ring of the parents above each child.
  const below = rowTiles.map((_, gen) => gen > HISTORY_LEVEL ? Math.max(12, Math.round(scaleFor(gen) * (narrow ? 32 : 39))) : narrow ? 38 : 44);
  // Rows spread to use the height the screen leaves: the branches between them get room to bend.
  const hasChildren = roots.some(id => m.children(id).length > 0);
  const natural = top + heights.reduce((a, b) => a + b, 0) + below.slice(1).reduce((a, b) => a + b, 0) + (hasChildren ? 118 : 0) + PAD;
  const spread = last && room > natural ? Math.min(56, (room - natural) / last) : 0;
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
  // The couple in the middle is joined by a ring; their children hang from it.
  const knot = (left: Tile, right: Tile) => {
    const from = left.x + left.w + left.stackLayers * STACK_STEP;
    const r = Math.max(1, Math.min(Math.max(2.5, RING * left.scale), (right.x - from) / 2 - .5));
    const x = (from + right.x) / 2;
    const y = left.y + left.h / 2;
    return {x, y: y + r, bottom: Math.max(left.y + left.h, right.y + right.h),
      d: `M${left.x + left.w},${y} H${x - r} M${x + r},${y} H${right.x} M${x - r},${y} a${r},${r} 0 1,0 ${r * 2},0 a${r},${r} 0 1,0 ${-r * 2},0`};
  };
  // Every parent sends an own branch down to the child. Two branches meet in a ring above the child: the same ring
  // that joins the couple in the middle, so a child always hangs from the ring of the parents.
  const byChild = new Map<string, typeof parentLinks>();
  for (const link of parentLinks) byChild.set(link.child.id, [...byChild.get(link.child.id) || [], link]);
  for (const [childId, pair] of byChild) {
    const child = tileById.get(childId)!;
    const above = pair.map(link => tileById.get(link.parent.id)!).filter(to => to.gen > child.gen);
    const fall = above.length === 2 ? child.y - Math.max(...above.map(to => to.y + to.h)) : 0;
    const r = Math.max(3, RING * Math.min(1, child.scale));
    const stem = Math.max(2, Math.round(r * .6));
    // The ring rides above the child's stack of siblings. Rows in the haze keep the plain fork.
    const lift = child.stackLayers * STACK_STEP;
    const ring = child.gen < HISTORY_LEVEL && fall >= lift + stem + r * 2 + 10 ? child.y - lift - stem - r : 0;
    const x = midX(child);
    for (const {parent, status} of pair) {
      const to = tileById.get(parent.id)!;
      const d = to.gen > child.gen ? curve(x, ring ? ring - r : child.y, midX(to), to.y + to.h) : curve(x, child.y, midX(to), to.y);
      links.push({key: JSON.stringify([childId, parent.id]), d, gen: to.gen, status, kind: 'parent', color: to.color, ids: [childId, parent.id]});
      // Son or grandson, drawn as a son: a little haze halfway up the link says who may stand between, by name.
      const second = child.gap || to.gap || to.gen <= child.gen ? undefined : m.secondWay(childId);
      if (second?.kind === 'between' && second.above === parent.id && !tileById.has(second.via)) {
        const top = to.y + to.h, h = Math.min(30, (child.y - top) * .5);
        if (h >= 14) tiles.push({id: `gap-hint:${childId}`, gen: child.gen, status, w: GAP_W, h, scale: child.scale, compact: true, fade: child.fade,
          x: (x + midX(to)) / 2 - GAP_W / 2, y: (top + (ring ? ring - r : child.y)) / 2 - h / 2, stackLayers: 0, color: to.color, gap: true, hint: second.via});
      }
    }
    if (ring) links.push({key: 'ring:' + childId, gen: child.gen + 1, status: 'export', kind: 'union', ids: [childId, ...above.map(to => to.id)],
      d: `M${x - r},${ring} a${r},${r} 0 1,0 ${r * 2},0 a${r},${r} 0 1,0 ${-r * 2},0 M${x},${ring + r} V${child.y}`});
  }
  const rootJoint = roots.length === 2 ? knot(rowTiles[0][0], rowTiles[0][1]) : null;
  if (rootJoint) {
    links.push({key: 'union', d: rootJoint.d, gen: 0, kind: 'union', ids: [...roots],
      status: m.connectionStatus(m.spouseConnection(roots[0], roots[1]))});
  }

  const visible = new Set(tiles.filter(tile => !tile.gap).map(tile => tile.id));
  const extras = m.spouses(center).filter(id => !m.info[id].placeholder);
  // A possible child with no missing generation between is a child: it stands in the row beside the others.
  const children = new Set(roots.flatMap(id => [...m.children(id), ...m.descendantsBelow(id).filter(({slot}) => !slot.gap).map(({id}) => id)]));
  // The form of a child's link, as for a parent's: the main line an assumption at most probable, a weak origin weak.
  const own = (slot: Slot) => slot.main ? m.connectionLevel(slot) === 1 ? m.connectionStatus(slot) : 'probable'
    : slot.weak ? 'weak' : m.connectionStatus(slot);
  const spans: number[][] = [], downs: number[][] = [];
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
      const status = kind === 'union' ? m.connectionStatus(m.spouseConnection(center, id)) : slot ? own(slot) : 'export';
      const tile = card(id, -1, status, w);
      if (slot?.main && kind === 'child' && !['export', 'verified'].includes(status)) tile.assumed = true;
      tile.x = axis + (i - (row.length - 1) / 2) * (w + 18) - w / 2;
      spans.push([tile.x, tile.x + w]);
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
        links.push({key: JSON.stringify([kind, center, id]), d: curve(from.x, from.y, midX(tile), lower), gen: 1, status, kind,
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

  // The way down from a nest's anchor: the missing generations as haze, then the family's person, one tap away.
  const centerTile = tileById.get(center);
  m.descendantsBelow(center).filter(({id}) => !visible.has(id)).forEach(({id, slot}) => {
    if (!centerTile) return;
    const status = own(slot);
    const color = m.tone(id)?.color;
    // Below the children: the line runs behind their row, as it runs through one of them nobody knows which, so the
    // haze never stands straight under one child: it takes the nearest half step between them or beside the row.
    const w = narrow ? 148 : 158;
    const at = (k: number) => midX(centerTile) - w / 2 + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * (w + 18) / 2;
    let k = 0;
    while (spans.some(([a, b]) => at(k) + w / 2 > a - 6 && at(k) + w / 2 < b + 6) || downs.some(([a, b]) => at(k) < b + 18 && at(k) + w > a - 18)) k++;
    const x = at(k);
    downs.push([x, x + w]);
    let from = {x: midX(centerTile), y: centerTile.y + centerTile.h};
    let y = lower;
    const second = m.secondWay(id);
    for (let i = 1; i <= (slot.gap || 0); i++) {
      const haze: Tile = {id: `gap-down:${id}:${i}`, gen: -1, status, w: GAP_W, h: 34, scale: 1, compact: true, fade: 1, x: x + w / 2 - GAP_W / 2, y, stackLayers: 0, color, gap: true,
        hint: i === 1 && second?.kind === 'between' && second.above === center ? second.via : undefined};
      links.push({key: haze.id, d: curve(from.x, from.y, x + w / 2, y), gen: 1, status, kind: 'child', color, ids: [center, id]});
      tiles.push(haze);
      from = {x: x + w / 2, y: y + haze.h};
      y += haze.h + 14;
    }
    const tile = {...card(id, -1, status, w), x, y};
    links.push({key: 'down:' + id, d: curve(from.x, from.y, x + w / 2, y), gen: 1, status, kind: 'child', color, ids: [center, id]});
    tiles.push(tile);
    visible.add(id);
    familyBottom = Math.max(familyBottom, tile.y + tile.h);
  });

  const bounds = (cards: Tile[]): Box => ({
    x0: Math.min(...cards.map(tile => tile.x)),
    x1: Math.max(...cards.map(tile => tile.x + tile.w + tile.stackLayers * STACK_STEP)),
    y0: Math.min(...cards.map(tile => tile.y - tile.stackLayers * STACK_STEP)),
    y1: Math.max(...cards.map(tile => tile.y + tile.h)),
  });
  const box = bounds(tiles);
  const near = bounds(tiles.filter(tile => tile.gen >= 0 && tile.gen < HISTORY_LEVEL));
  const crown = bounds(tiles.filter(tile => tile.gen >= 0));
  // The children's row counts as far as the screen around the axis holds it; the rest of it is panned to.
  const frame = {...box, x0: Math.max(box.x0, Math.min(crown.x0, axis - budget / 2)), x1: Math.min(box.x1, Math.max(crown.x1, axis + budget / 2))};
  const offset = Math.max(0, PAD - box.x0);
  if (offset) {
    // Translate the whole figure once so the pan bounds also include the leftmost tile.
    for (const tile of tiles) tile.x += offset;
    for (const b of [box, near, frame]) { b.x0 += offset; b.x1 += offset; }
  }
  const peopleCount = m.familyPeople.has(center) ? m.familyPeople.size : m.connectedFrom([center]).size;
  return {
    tiles, links, width: Math.max(viewport + offset, box.x1 + PAD), height: box.y1 + PAD,
    box, near, frame, axis: axis + offset, rootBottom, familyBottom, horizon, cut: cut.length > 0, linkOffset: offset, visible, peopleCount, tightest,
  };
}

/** The share of its full size at which a compact tile still carries the whole name. */
export const WHOLE = .7;
const READABLE = .75; // A full card's words stay legible down to this zoom.

/** The first picture: the whole drawn tree, unless that shrinks the centre and the ancestors past their names; then the
 * smallest zoom that keeps them, and the frame (centre, spouse, ancestors) in the middle. */
export function fitView(layout: Layout, w: number, room: number) {
  const oldest = layout.horizon ? 0 : layout.box.y0;
  const height = layout.box.y1 - oldest;
  const most = Math.min(w < 560 ? 1.25 : 1.45, (room - 12) / height);
  const fits = (box: Box) => Math.max(.5, Math.min(most, (w - 12) / (box.x1 - box.x0)));
  const names = Math.max(...layout.tiles.filter(tile => tile.gen >= 0 && tile.gen < HISTORY_LEVEL && !tile.gap)
    .map(tile => tile.compact ? WHOLE / tile.scale : READABLE));
  const all = fits(layout.box);
  const k = all >= Math.min(names, fits(layout.frame)) ? all : Math.min(names, fits(layout.frame));
  const box = k === all ? layout.box : layout.frame;
  const x = w / 2 - (box.x0 + box.x1) / 2 * k;
  const y = Math.min(Math.max(4, (room - height * k) / 2) - oldest * k, room - layout.familyBottom * k);
  return {k, x, y};
}

export {HISTORY_LEVEL, HORIZON_Y, STACK_STEP};
