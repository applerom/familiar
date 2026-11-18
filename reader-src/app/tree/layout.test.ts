import {expect, test} from 'bun:test';
import {buildModel,type Row} from './model';
import {layoutTree} from './layout';

// A count that included siblings hidden by the old layout made the family think
// its tree had lost people. Check that every person has exactly one place in the count.
test('tiles, side branches and distant ancestors account for the connected tree', () => {
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
    const tree = layoutTree(model,'home',width,5);
    const accounted = [...tree.visible,...tree.collateral,...tree.beyond];
    expect(accounted).toHaveLength(300);
    expect(new Set(accounted)).toEqual(model.familyPeople);
    expect(tree.tiles.every(tile => tile.w > tile.h && tile.h > 0)).toBe(true);
    expect(tree.tiles.filter(tile => tile.id === null).length).toBeGreaterThan(0);
    expect(tree.tiles.find(tile => tile.id === 'home')?.siblings)
      .toEqual(['oldest','home','earlier-in-tree','later-in-tree']);
    expect(tree.beyond).toEqual(['ancestor6','ancestor7','ancestor8']);
  }
});
