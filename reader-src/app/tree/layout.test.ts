import {expect, test} from 'bun:test';
import {buildModel,type Row} from './model';
import {layoutTree} from './layout';

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
      expect(tree.links.filter(link => link.kind === 'parent')).toHaveLength(5);
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
