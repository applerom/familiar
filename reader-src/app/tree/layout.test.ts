import {expect, test} from 'bun:test';
import {buildModel,type Row} from './model';
import {fitView,layoutTree} from './layout';
import {buildOverview} from './overview';

// On a phone, the old fit clipped the child's tile while the panel listed the child.
test('the tree counts known relatives and fits the central couple with its children', () => {
  const people: Record<string, Row> = {};
  const edges: Row[] = [];
  function add(id: string, birth?: number) {
    people[id] = {id, name: 'Person ' + id, events: birth ? [{tag: 'BIRT', date: String(birth)}] : []};
  }
  function parent(child: string, parent: string, role: string, status = 'export') {
    edges.push({child,parent,role,status});
  }
  add('home',2000);
  add('mate',2001);
  add('child',2024);
  add('mate-child',2025);
  parent('child','home','отец');
  parent('child','mate','мать');
  parent('mate-child','mate','мать');
  for (let i=1; i<=8; i++) {
    add('ancestor'+i,2000-i*28);
    parent(i===1?'home':'ancestor'+(i-1),'ancestor'+i,'отец');
  }
  add('mother',1974);
  parent('home','mother','мать');
  for (const [id,birth] of [['oldest',1996],['earlier-in-tree',undefined],['later-in-tree',undefined]] as const) {
    add(id,birth);
    parent(id,'ancestor1','отец','hypothesis');
    parent(id,'mother','мать');
  }
  for (let i=0; i<286; i++) {
    add('cousin'+i,2020);
    parent('cousin'+i,'oldest','мать');
  }
  add('unrelated');
  const model = buildModel({root:'home',people,edges,families:[{husband:'home',wife:'mate'}]});
  for (const width of [390,1440]) {
    for (const center of ['home','mate']) {
      const tree = layoutTree(model,center,width,5);
      expect(tree.peopleCount).toBe(302);
      expect(tree.tiles.map(tile => tile.id).sort()).toEqual([
        'ancestor1','ancestor2','ancestor3','ancestor4','ancestor5','child','home','mate','mate-child','mother',
      ]);
      expect(tree.links.filter(link => link.kind === 'parent')).toHaveLength(6);
      expect(tree.links.filter(link => link.kind === 'union')).toHaveLength(2);
      expect(tree.tiles.every(tile => tile.w > tile.h && tile.h > 0)).toBe(true);
      expect(tree.tiles.find(tile => tile.id === 'home')?.stackLayers).toBe(3);
      expect(tree.tiles.find(tile => tile.id === 'mate')?.stackLayers).toBe(0);
      const children = tree.tiles.filter(tile => tile.gen < 0);
      expect(children.map(tile => tile.id)).toEqual(['child','mate-child']);
      expect(children.every(tile => tile.y > tree.rootBottom && tile.y === children[0].y)).toBe(true);
      expect(tree.familyBottom).toBe(Math.max(...children.map(tile => tile.y + tile.h)));
    }
  }
});

// A probable branch (0.3–0.5) is drawn above the family's person; missing generations keep their rows; below 0.3 only
// the leading origin of a person with nobody above, as a weak branch, from 0.1; the anchor shows the way down.
test('a possible ancestor stands above missing generations and a weak one is not drawn', () => {
  const people: Record<string, Row> = {};
  for (const [id, birth, sex] of [['home', 1990], ['father', 1960], ['grandfather', 1930], ['elder', 1800], ['elder-father', 1770], ['stranger', 1740], ['faint', 1870], ['found-mother', 1900, 'F'], ['elder-son', 1830]] as [string, number, string?][])
    people[id] = {id, sex: sex || 'M', name: 'Person ' + id, events: [{tag: 'BIRT', date: String(birth)}]};
  const edges: Row[] = [['home', 'father'], ['father', 'grandfather'], ['elder', 'elder-father'], ['elder-son', 'elder']].map(([child, parent]) => ({child, parent, role: 'отец', status: 'export'}));
  // what the engine leaves of a probable identity: the found mother on a junction with the version's weight
  edges.push({child: 'grandfather', parent: 'found-mother', role: 'мать', status: 'hypothesis', weight: .45, identity: 'found-son'});
  const associations = [{type: 'possible_ancestor', from: 'elder', to: 'grandfather', weight: .35, missing: 2, missing_max: 3}, {type: 'possible_parent', from: 'stranger', to: 'elder-father', weight: .2}, {type: 'possible_parent', from: 'faint', to: 'found-mother', weight: .05}];
  const model = buildModel({root: 'home', people, edges, associations});
  expect(model.ancestorsOf('home').get('elder')?.n).toBe(6);
  for (const width of [390, 1440]) {
    const tree = layoutTree(model, 'home', width, 8);
    const gen = (id: string) => tree.tiles.find(tile => tile.id === id)?.gen;
    const haze = tree.tiles.filter(tile => tile.gap);
    // 1930 → 1800: four generations up, so three missing, within the recorded two to three
    expect(haze.map(tile => tile.gen).sort()).toEqual([3, 4, 5]);
    expect([gen('elder'), gen('elder-father'), gen('found-mother'), gen('stranger'), gen('faint')]).toEqual([6, 7, 3, 8, undefined]);
    expect(tree.tiles.find(tile => tile.id === 'stranger')?.status).toBe('weak');
    expect(tree.tiles.filter(tile => ['elder', 'elder-father', 'found-mother'].includes(tile.id)).every(tile => tile.status === 'probable')).toBe(true);
    expect(tree.visible.has(haze[0].id)).toBe(false);
    const down = layoutTree(model, 'elder', width, 2);
    expect([down.tiles.filter(tile => tile.gap).length, down.visible.has('grandfather')]).toEqual([3, true]);
    // The way down through missing generations never hangs straight under one known child.
    const [son, way] = ['elder-son', 'grandfather'].map(id => down.tiles.find(tile => tile.id === id)!);
    expect(Math.abs(son.x - way.x)).toBeGreaterThan(son.w / 2);
  }
});

// The family's main line is drawn as a probable line whatever its weight; assumptions above it keep the chain whole.
test('a main line below 0.3 is drawn as the main branch and a chain of assumptions does not break', () => {
  const people: Record<string, Row> = {};
  for (const [id, birth, sex] of [['home', 1990], ['great', 1910], ['p1', 1885], ['p1-mother', 1860, 'F'], ['p2', 1850], ['p3', 1820], ['p3-father', 1790], ['p1-son', 1915]] as [string, number, string?][])
    people[id] = {id, sex: sex || 'M', name: 'Person ' + id, events: [{tag: 'BIRT', date: String(birth)}]};
  const edges: Row[] = [{child: 'home', parent: 'great', role: 'отец', status: 'export'}, {child: 'p1', parent: 'p1-mother', role: 'мать', status: 'export'}, {child: 'p3', parent: 'p3-father', role: 'отец', status: 'export'}, {child: 'p1-son', parent: 'p1', role: 'отец', status: 'export'}];
  const associations = [{type: 'possible_parent', from: 'p1', to: 'great', weight: .1, main_line: true}, {type: 'possible_parent', from: 'p2', to: 'p1', weight: .2}, {type: 'possible_parent', from: 'p3', to: 'p2', weight: .15}];
  const tree = layoutTree(buildModel({root: 'home', people, edges, associations}), 'home', 1440, 6);
  const tile = (id: string) => tree.tiles.find(t => t.id === id);
  expect(['p1', 'p2', 'p3', 'p3-father', 'p1-mother'].map(id => tile(id)?.status)).toEqual(['probable', 'probable', 'probable', 'export', 'export']);
  expect(['p1', 'p2', 'p3', 'p3-father'].map(id => !!tile(id)?.assumed)).toEqual([true, true, true, false]);
  // A possible son with no missing generation stood below his documented brother, read as his son.
  const kids = layoutTree(buildModel({root: 'home', people, edges, associations}), 'p1', 1440, 3).tiles.filter(t => t.gen < 0);
  expect(kids.map(t => [t.id, t.y === kids[0].y, t.status])).toEqual([['great', true, 'probable'], ['p1-son', true, 'export']]);
});

// A revision list's spelling (old letters, the act's case) reached the tiles; the reader's language decides.
test('a tile carries the name in the reader language, else the family name, never the document spelling', () => {
  const names = [{given: 'Fedora', surname: 'Invented', type: 'recorded'}, {given: 'Fedor', surname: 'Invented', type: 'inferred'}];
  const people = {p: {id: 'p', name: 'Fedor Invented', names, namePresentation: {display: 'Fedor Invented', byLanguage: {pl: 'Teodor Invented'}}}};
  const [pl, sv] = ['pl', 'sv'].map(languageCode => buildModel({root: 'p', people, edges: []}, {languageCode}).info.p);
  expect([pl.short, pl.givenName, sv.short, sv.givenName]).toEqual(['Teodor Invented', 'Teodor', 'Fedor Invented', 'Fedor']);
});

// One vanishing point for both sides made a wife's long line lean over the husband's short one, as if kin.
test('the husband and the wife grow two crowns with open sky between them, crossed only by a shared ancestor', () => {
  const people: Record<string, Row> = {};
  const edges: Row[] = [];
  const add = (id: string, birth: number, sex = 'M') => { people[id] = {id, sex, name: 'Person ' + id, events: [{tag: 'BIRT', date: String(birth)}]}; };
  const parent = (child: string, id: string, role: string) => edges.push({child, parent: id, role, status: 'export'});
  add('he', 1985); add('she', 1987, 'F'); add('kid', 2015);
  parent('kid', 'he', 'отец'); parent('kid', 'she', 'мать');
  const husband = ['he'], wife = ['she'];
  for (const [id, child, role] of [['he-f', 'he', 'отец'], ['he-m', 'he', 'мать'], ['he-ff', 'he-f', 'отец'], ['he-mf', 'he-m', 'отец'], ['he-mm', 'he-m', 'мать']]) {
    add(id, 1960 - (id.length - 4) * 28, role === 'мать' ? 'F' : 'M'); parent(child, id, role); husband.push(id);
  }
  // The wife's side is traced eight generations up, two people in every row.
  for (let g = 1, child = 'she'; g <= 8; g++) {
    const f = 'she-f' + g, mo = 'she-m' + g;
    add(f, 1987 - g * 28); add(mo, 1987 - g * 28, 'F');
    parent(child, f, 'отец'); parent(child, mo, 'мать');
    wife.push(f, mo);
    child = f;
  }
  // Husband and wife are distant cousins: one ancestor of both, drawn once.
  add('common', 1880);
  parent('he-ff', 'common', 'отец'); parent('she-m3', 'common', 'отец');
  const model = buildModel({root: 'he', people, edges, families: [{husband: 'he', wife: 'she'}]});
  for (const width of [390, 1440]) for (const center of ['he', 'she']) {
    const tree = layoutTree(model, center, width, 9);
    const drawn = (ids: string[], from = 1) => tree.tiles.filter(tile => ids.includes(tile.id) && tile.gen >= from);
    expect(drawn(wife).length).toBe(16);
    // In every row the husband's side stands wholly left of the wife's, a line's gap between them at least.
    for (let gen = 1; gen <= 9; gen++) {
      const row = (ids: string[]) => drawn(ids).filter(tile => tile.gen === gen);
      if (row(husband).length && row(wife).length)
        expect(Math.min(...row(wife).map(tile => tile.x)) - Math.max(...row(husband).map(tile => tile.x + tile.w + tile.stackLayers * 4))).toBeGreaterThan(8);
    }
    // The sky: a vertical band between the crowns, rising from between the couple, that no tile of either side enters.
    // On a phone the near rows share the whole width to keep names readable; the sky opens in the historical rows.
    const from = width < 560 ? 3 : 1;
    const skyFrom = Math.max(...drawn(husband, from).map(tile => tile.x + tile.w + tile.stackLayers * 4));
    const skyTo = Math.min(...drawn(wife, from).map(tile => tile.x));
    const [he, she] = ['he', 'she'].map(id => tree.tiles.find(tile => tile.id === id)!);
    expect(skyTo - skyFrom).toBeGreaterThan(8);
    expect(Math.min(skyTo, she.x) - Math.max(skyFrom, he.x + he.w)).toBeGreaterThan(8);
    const common = tree.tiles.filter(tile => tile.id === 'common');
    expect(common).toHaveLength(1);
    expect(common[0].x < skyTo && common[0].x + common[0].w > skyFrom).toBe(true);
    // One generation, one size on both sides of the sky.
    for (const gen of [1, 2, 3]) expect(new Set(drawn([...husband, ...wife]).filter(tile => tile.gen === gen).map(tile => tile.w)).size).toBe(1);
  }
  // The map of the whole family on the time scale keeps the same halves: the seam holds the child and the shared one.
  const ov = buildOverview(model)!;
  const xs = (ids: string[]) => ids.map(id => ov.pos.get(id)!.x);
  expect(Math.max(...xs(husband))).toBeLessThan(ov.pos.get('kid')!.x);
  expect(Math.min(...xs(wife))).toBeGreaterThan(ov.pos.get('kid')!.x);
  expect(ov.pos.get('common')!.x).toBeGreaterThan(Math.max(...xs(husband)));
  expect(ov.pos.get('common')!.x).toBeLessThan(Math.min(...xs(wife)));
  // A crowded line keeps to its own band: a cousin's large family never lies over the mother's line beside it.
  const nest = ['he-ff', 'he-f', 'u'];
  add('u', 1934); parent('u', 'he-ff', 'отец');
  for (let i = 0; i < 6; i++) for (let j = 0; j < 3; j++) {
    const c = 'u' + i, g = c + '-' + j;
    if (!j) { add(c, 1955 + i * 3); parent(c, 'u', 'отец'); nest.push(c); }
    add(g, 1975 + i * 3 + j); parent(g, c, 'отец'); nest.push(g);
  }
  const crowded = buildOverview(buildModel({root: 'he', people, edges, families: [{husband: 'he', wife: 'she'}]}))!;
  const at = (ids: string[]) => ids.map(id => crowded.pos.get(id)!.x);
  expect(Math.max(...at(nest))).toBeLessThan(Math.min(...at(['he-m', 'he-mf', 'he-mm'])));
  expect(Math.max(...at([...nest, 'he-m', 'he-mf', 'he-mm']))).toBeLessThan(crowded.pos.get('kid')!.x);
});

// A phone drew a couple with seven children so small that their parents turned to initials.
test('a wide row of children pans sideways and never shrinks the parents to initials', () => {
  const people: Record<string, Row> = {};
  const edges: Row[] = [];
  const add = (id: string, birth: number, sex = 'M') => { people[id] = {id, sex, name: 'Person ' + id, events: [{tag: 'BIRT', date: String(birth)}]}; };
  add('he', 1815); add('she', 1820, 'F');
  for (const [id, child, role] of [['hf', 'he', 'отец'], ['hm', 'he', 'мать'], ['sf', 'she', 'отец'], ['sm', 'she', 'мать']]) {
    add(id, 1790, role === 'мать' ? 'F' : 'M'); edges.push({child, parent: id, role, status: 'export'});
  }
  const kids = (n: number) => {
    for (let i = 0; i < 9; i++) delete people['k' + i];
    edges.splice(4);
    for (let i = 0; i < n; i++) { add('k' + i, 1840 + i * 2); edges.push({child: 'k' + i, parent: 'he', role: 'отец', status: 'export'}, {child: 'k' + i, parent: 'she', role: 'мать', status: 'export'}); }
    return buildModel({root: 'he', people, edges, families: [{husband: 'he', wife: 'she'}]});
  };
  const fit = (n: number) => { const tree = layoutTree(kids(n), 'he', 390, 2, 700); return {tree, ...fitView(tree, 390, 700)}; };
  const wide = fit(8);
  expect(wide.tree.box.x1 - wide.tree.box.x0).toBeGreaterThan(390);
  const parents = wide.tree.tiles.filter(tile => tile.gen === 1);
  expect(parents).toHaveLength(4);
  for (const tile of parents) expect(tile.scale * wide.k).toBeGreaterThanOrEqual(.7);
  // One or two children, or a wide screen with room for all: the whole drawn family is in the picture, as before.
  const few = fit(2);
  expect(few.tree.frame).toEqual(few.tree.box);
  const tree = layoutTree(kids(6), 'he', 1040, 2, 760), all = fitView(tree, 1040, 760);
  expect(all.k).toBeCloseTo(Math.min(1.45, (760 - 12) / (tree.box.y1 - tree.box.y0), (1040 - 12) / (tree.box.x1 - tree.box.x0)));
});

// A line copied link by link from one book (0.7 each) was drawn as firm as a line of records all the way up.
test('the whole tree fades a line by every link on the way down; records stay firm', () => {
  const people: Record<string, Row> = {}, edges: Row[] = [];
  const add = (id: string, birth: number) => { people[id] = {id, sex: 'M', name: 'Person ' + id, events: [{tag: 'BIRT', date: String(birth)}]}; };
  add('home', 1990);
  for (let i = 1; i <= 12; i++) {
    add('b' + i, 1990 - i * 30); add('r' + i, 1990 - i * 30);
    edges.push({child: i === 1 ? 'home' : 'b' + (i - 1), parent: 'b' + i, role: 'отец', status: 'export', weight: .7});
  }
  for (let i = 1; i <= 12; i++) edges.push({child: i === 1 ? 'b0' : 'r' + (i - 1), parent: 'r' + i, role: i === 1 ? 'мать' : 'отец', status: 'verified'});
  add('b0', 1992); edges.push({child: 'b0', parent: 'home', role: 'отец', status: 'verified'});
  const ov = buildOverview(buildModel({root: 'b0', people, edges}))!;
  // 0.98 · 0.7 = 0.69 firm; · 0.7 = 0.48 probable; four links down 0.24: our version
  expect(['b1', 'b2', 'b4', 'b12'].map(id => ov.hold.get(id))).toEqual([1, 2, 3, 3]);
  expect(ov.hold.get('r12')).toBe(1);
});
