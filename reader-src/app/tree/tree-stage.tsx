'use client';
import {memo,useCallback,useEffect,useLayoutEffect,useMemo,useRef,useState,type CSSProperties,type ReactNode,type RefObject} from 'react';
import {STACK_STEP,WHOLE,fitView,layoutTree,levelRange,type Layout} from './layout';
import {useZoomPan} from './use-zoom-pan';
import {isPerson,lifeLabel,type Model,type Row} from './model';
import {growthWords} from './growth';
import {Face} from './portrait';

type TileActions = {
  open: (id: string) => void;
  hover: (id: string) => void;
};
const uncertain = (status: string) => status === 'hypothesis' || status === 'probable' || status === 'weak';
// One of the possible branches (the leading origin below 0.3): fainter than a probable line.
const weak = (status: string) => status === 'weak' ? ' weak' : '';
// What a compact tile can carry at its size on the screen: the whole name with the years,
// the given name with a year, an initial, or nothing but its colour.
const SHORT = 40, INITIAL = 13;
// A face rides on a near tile only when the tile is a card a finger can see it on.
const FACE_FROM = 84;
/**
 * Given names for the small tiles of a crowded row, where they fit: shorter names claim their room first, a tile
 * that keeps its initial takes only its own width, and a name never runs into its neighbour or past the picture.
 */
function smallNames(layout: Layout, model: Model, zoom: number) {
  const small = (t: Layout['tiles'][number]) => !t.gap && !model.info[t.id]?.knot && t.compact && t.scale * zoom < WHOLE && t.w * zoom < SHORT;
  const given = (id: string) => (model.info[id]?.givenName || model.info[id]?.treeName || '').split(' ')[0];
  const rows = new Map<number, Layout['tiles']>();
  for (const tile of layout.tiles) if (!tile.gap) rows.set(tile.y, [...rows.get(tile.y) || [], tile]);
  const half = new Map(layout.tiles.map(t => [t.id, t.w / 2]));
  const names = new Map<string, {name: string; font: number; w: number}>();
  const order = layout.tiles.filter(t => small(t) && given(t.id)).sort((a, b) => given(a.id).length - given(b.id).length);
  for (const tile of order) {
    const row = rows.get(tile.y)!.slice().sort((a, b) => a.x - b.x), i = row.indexOf(tile);
    const mid = (t: Layout['tiles'][number]) => t.x + t.w / 2, cx = mid(tile), gap = 4 / zoom;
    const left = i ? cx - mid(row[i - 1]) - half.get(row[i - 1].id)! - gap : cx;
    const right = i < row.length - 1 ? mid(row[i + 1]) - half.get(row[i + 1].id)! - cx - gap : layout.width - cx;
    const name = given(tile.id), room = 2 * Math.min(left, right, 90);
    const font = Math.min(tile.w * .46, 12 / zoom, (room - 10) / (name.length * .64));
    if (font * zoom < 8.5) continue;
    const w = Math.max(tile.w, Math.ceil(name.length * font * .64 + 10));
    half.set(tile.id, w / 2);
    names.set(tile.id, {name, font, w});
  }
  return names;
}

const TreeTiles = memo(function TreeTiles({layout,model,center,hot,labels,actions,zoom,drawn}: {
  layout: Layout; model: Model; center: string; hot: string; labels: Row;
  actions: RefObject<TileActions>; zoom: number; drawn: string;
}) {
  const lang = labels.languageCode;
  const words = growthWords[lang] || growthWords.en;
  const named = useMemo(() => smallNames(layout, model, zoom), [layout, model, zoom]);
  return <>
    <svg key={drawn} className="tree-links" width={layout.width} height={layout.height} aria-hidden="true">
      <g transform={`translate(${layout.linkOffset} 0)`}>{layout.links.map(link =>
        <path key={link.key} d={link.d}
          className={`lk ${link.kind} g${Math.min(link.gen, 4)}${uncertain(link.status) ? ' hyp' : ''}${weak(link.status)}${link.ids.includes(center) || hot && link.ids.includes(hot) ? ' on' : ''}`}
          style={link.color ? {stroke: `color-mix(in srgb, ${link.color} 58%, var(--tree-paper))`} : undefined}/>
      )}</g>
    </svg>
    {layout.tiles.map(tile => {
      const {id, gen, stackLayers} = tile;
      const distant = tile.compact;
      const whole = !distant || tile.scale * zoom >= WHOLE;
      // A small tile carries the given name when its row leaves room for it, widening around its own centre;
      // only where even that does not fit does it fall back to an initial.
      const label = named.get(id);
      const mini = !whole && tile.w * zoom < SHORT && !label;
      const w = label ? label.w : tile.w;
      const style = {
        transform: `translate(${tile.x - (w - tile.w) / 2}px,${tile.y}px)`, width: w, height: tile.h, '--b': tile.color, '--s': tile.scale,
        '--c': Math.min(1.05, Math.max(.62, tile.w / 66)), '--w': tile.w, '--depth-opacity': tile.fade,
        ...(label ? {'--name-font': `${label.font}px`} : {}),
      } as CSSProperties;
      // A generation nobody has found yet: haze with the dotted line running through it, no card and no words.
      // When the tree holds someone of a fitting age for that generation, the haze carries the name, quietly.
      // The generation right below a possible ancestor is a place among the couple's children: haze of a card's size,
      // and a tap on it goes on along the line.
      if (tile.gap) return <div key={id} className={`tile-position tile-gap${tile.place ? ' tile-place' : ''}${weak(tile.status)}`} style={style} data-gen={gen}
        aria-hidden={tile.hint || tile.opens ? undefined : 'true'}>
        {tile.opens ? <button className="tree-gap" title={model.info[tile.opens].short} aria-label={model.info[tile.opens].short} onClick={() => actions.current.open(tile.opens!)}/>
          : <span className="tree-gap"/>}
        {tile.hint && <button className="gap-hint" title={model.info[tile.hint].short} onClick={() => actions.current.open(tile.hint!)}>{model.info[tile.hint].givenName || model.info[tile.hint].short.split(' ')[0]}</button>}
      </div>;
      const person = model.info[id];
      if (person.knot) return <div key={id} className="tile-position" style={style} aria-hidden="true">
        <span className="tree-knot"/>
      </div>;
      const dates = model.tileDates(id);
      const year = dates.birth || dates.death;
      const life = !person.connector && year ? lifeLabel({...person, birthText: dates.birth, deathText: dates.death}, labels, lang) : '';
      const growth = person.growth;
      const confirmed = growth.confirmed.length > 0;
      const title = [person.fullName, life, dates.possible ? labels.sameAs : '', confirmed ? words.confirmed : growth.treeMemory ? words.tree : growth.memory ? words.memory : growth.found ? words.found : ''].filter(Boolean).join(' · ');
      const portrait = !distant && tile.w * zoom >= FACE_FROM ? person.portrait : undefined;
      return <div key={id} className={`tile-position${distant ? ' tile-distant' : ''}${distant && whole ? ' tile-whole' : ''}${mini ? ' tile-mini' : ''}${label ? ' tile-named' : ''}${portrait ? ' tile-with-face' : ''}`} style={style} data-gen={gen}>
        {tile.assumed && <span className="assumed-haze" aria-hidden="true"/>}
        {Array.from({length: stackLayers}, (_, i) => {
          const offset = (stackLayers - i) * STACK_STEP;
          return <span key={i} className="stack-back" aria-hidden="true" style={{translate: `${offset}px ${-offset}px`}}/>;
        })}
        <button data-person={id} className={`tree-tile${uncertain(tile.status) ? ' hyp' : ''}${weak(tile.status)}${id === center ? ' tree-centre' : ''}`}
          title={title} aria-label={title} aria-current={id === center ? 'true' : undefined}
          onClick={() => actions.current.open(id)}
          onPointerEnter={event => { if (event.pointerType === 'mouse') actions.current.hover(id); }}
          onPointerLeave={() => actions.current.hover('')}>
          {mini ? tile.w * zoom >= INITIAL && <strong>{(person.givenName || person.treeName).slice(0, 1)}</strong>
            : label ? <strong>{label.name}</strong>
            : <strong>{whole ? person.treeName : person.givenName || person.treeName}</strong>}
          {mini || label ? null : whole ? life && <small className={person.guess || dates.possible ? 'guess' : undefined}>{life}</small>
            : year && !person.connector && <small className={person.guess || dates.possible ? 'guess' : undefined}>{year}</small>}
          {!distant && (confirmed || growth.firmMemory) && <span className="tile-provenance" aria-hidden="true">
            <i className="growth-confirm">✓</i>
            {confirmed && <i>▤</i>}
          </span>}
        </button>
        {portrait && <span className="tile-face" aria-hidden="true"><Face key={portrait.asset} portrait={portrait}/></span>}
      </div>;
    })}
    {layout.horizon && <div className={`history-fog${layout.cut ? ' cut' : ''}`} aria-hidden="true"/>}
  </>;
});

export default function TreeStage({model,id,go,labels,onVisible,children}: {
  model: Model; id: string; go: (id: string) => void; labels: Row;
  onVisible: (visible: Set<string>) => void; children?: ReactNode;
}) {
  const stage = useRef<HTMLDivElement>(null);
  const content = useRef({w: 0, h: 0});
  const [size, setSize] = useState({w: 0, h: 0});
  const [resizing, setResizing] = useState(false);
  const [hot, setHot] = useState('');
  // How many generations of ancestors the reader asked for; until they ask, the screen decides.
  const [want, setWant] = useState<number | null>(null);
  const actions = useRef<TileActions>({open: go, hover: setHot});
  actions.current = {open: go, hover: setHot};

  useLayoutEffect(() => {
    const el = stage.current;
    if (!el) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let first = true;
    const measure = () => {
      setSize(s => s.w === el.clientWidth && s.h === el.clientHeight ? s : {w: el.clientWidth, h: el.clientHeight});
      if (first) { first = false; return; }
      setResizing(true);
      clearTimeout(timer);
      timer = setTimeout(() => setResizing(false), 260);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, []);

  const room = size.h - (size.w < 560 ? 72 : 90);
  const range = useMemo(() => size.w ? levelRange(model,id,size.w,room) : {max: 1, auto: 1}, [model,id,size.w,room]);
  const level = Math.min(range.max, Math.max(1, want ?? range.auto));
  const layout = useMemo(() => size.w ? layoutTree(model,id,size.w,level,room) : null, [model,id,size.w,level,room]);
  content.current = layout ? {w: layout.width, h: layout.height} : {w: 0, h: 0};
  useEffect(() => {
    if (layout) onVisible(layout.visible);
  }, [layout, onVisible]);
  useEffect(() => setHot(''), [id]);

  const wheel = useRef<(direction: number, at: {x: number; y: number}) => void>(() => {});
  const {t,setT,moving,focal} = useZoomPan(stage, {min: .45, max: 3.5, content, horizontalWheel: true,
    onStep: (direction, at) => wheel.current(direction, at)});
  const base = useRef(1);
  const fit = useCallback(() => {
    if (!layout || !size.h) return;
    // Every generation fills the stage; a row of children wider than the screen pans sideways instead of shrinking it.
    const {k, x, y} = fitView(layout, size.w, room);
    base.current = k;
    setT({k,x,y});
  }, [layout,size,room,setT]);
  useLayoutEffect(fit, [fit]);

  // Zooming like a map, in people instead of pixels: one turn of the wheel, one pinch or one press of a round
  // button is one step. Outwards draws one more generation of ancestors; once all of them are open it goes back the
  // way the reader came, and with no such way one step along the kinship towards the family's home people, so
  // outwards always leads back to the wide tree. Inwards over a person moves the tree to that person and keeps the
  // branch that stood above them; inwards elsewhere drops the oldest generation.
  const trail = useRef<{id: string; want: number | null}[]>([]);
  const expected = useRef('');
  const here = useRef({id, want});
  useEffect(() => {
    const from = here.current;
    here.current = {id, want};
    if (from.id === id) return;
    if (expected.current === id) { expected.current = ''; return; }
    // A person chosen any other way (a click, the search, the browser's Back) joins the same way back.
    const back = trail.current.at(-1);
    if (back?.id === id) { trail.current.pop(); setWant(back.want); }
    else trail.current = [...trail.current.slice(-39), from];
  });
  const homeward = useMemo(() => {
    const next = new Map<string, {id: string; kind: 'down' | 'up' | 'mate'}>();
    const seen = new Set(model.homes), queue = [...model.homes];
    for (const at of queue) {
      const reach = (other: string, kind: 'down' | 'up' | 'mate') => {
        if (seen.has(other) || !model.info[other] || model.info[other].placeholder) return;
        seen.add(other); next.set(other, {id: at, kind}); queue.push(other);
      };
      model.parents(at).slots.forEach(slot => slot && reach(slot.id, 'down'));
      model.children(at).forEach(child => reach(child, 'up'));
      model.spouses(at).forEach(mate => reach(mate, 'mate'));
    }
    return next;
  }, [model]);
  const move = useCallback((to: string, asked: number | null) => {
    expected.current = to;
    setWant(asked === null ? null : Math.max(1, asked));
    go(to);
  }, [go]);
  const [bumped, setBumped] = useState(0);
  const farther = useCallback(() => {
    if (level < range.max) return setWant(level + 1);
    const back = trail.current.pop();
    if (back) return move(back.id, back.want);
    let home = homeward.get(id);
    while (home && model.info[home.id].knot) home = homeward.get(home.id);
    if (home) move(home.id, home.kind === 'down' ? level + 1 : home.kind === 'up' ? level - 1 : level);
    else setBumped(n => n + 1);
  }, [level,range,homeward,id,move,model]);
  const closer = useCallback((at?: {x: number; y: number}) => {
    const hit = at && layout?.tiles.reduce<{tile: Layout['tiles'][number] | null; far: number}>((best, tile) => {
      const x = (at.x - t.x) / t.k, y = (at.y - t.y) / t.k;
      const far = Math.hypot(Math.max(tile.x - x, 0, x - tile.x - tile.w), Math.max(tile.y - y, 0, y - tile.y - tile.h));
      return far < best.far ? {tile, far} : best;
    }, {tile: null, far: 24 / t.k}).tile;
    if (hit && isPerson(model.info[hit.id]) && hit.gen !== 0) {
      trail.current.push({id, want});
      move(hit.id, hit.gen > 0 ? level - hit.gen : level);
    } else if (level > 1) setWant(level - 1);
    else setBumped(n => n + 1);
  }, [layout,t,id,want,level,move,model]);
  const canWiden = level < range.max || trail.current.length > 0 || homeward.has(id);
  wheel.current = (direction, at) => direction > 0 ? farther() : closer(at);
  // A pinch scales the picture under the fingers; past a fair stretch it becomes the same single step.
  const spent = useRef(false);
  useEffect(() => {
    if (!moving || !focal.current || spent.current) return;
    const stretch = t.k / base.current;
    if (stretch > .78 && stretch < 1.32) return;
    spent.current = true;
    if (stretch < 1) farther(); else closer(focal.current);
  }, [t.k]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!moving && spent.current) { spent.current = false; fit(); }
  }, [moving]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      const el = event.target as HTMLElement;
      if (event.defaultPrevented || el.closest('input, textarea, select, dialog, .overview, .lightbox') ||
          event.metaKey || event.ctrlKey || event.altKey) return;
      const [father,mother] = model.parents(id).slots;
      const selectable = (pid: string) => isPerson(model.info[pid]);
      const sibs = [...model.siblings(id).filter(selectable),id].sort(model.bySeniority);
      const i = sibs.indexOf(id), mate = model.spouses(id).find(selectable);
      const to = event.key === 'ArrowUp' ? [father,mother].find(slot=>slot&&selectable(slot.id))?.id : event.key === 'ArrowDown' ? model.children(id).find(selectable) :
        event.key === 'ArrowLeft' ? sibs[i-1] || mate : event.key === 'ArrowRight' ? sibs[i+1] || mate : '';
      if (to) { event.preventDefault(); go(to); }
      else if (event.key === '+' || event.key === '=') closer();
      else if (event.key === '-' || event.key === '_') farther();
      else if (event.key === '0' || event.key === 'Home') fit();
    };
    addEventListener('keydown', key);
    return () => removeEventListener('keydown', key);
  }, [model,id,go,farther,closer,fit]);

  // Only a few distinct values, so the tiles are redrawn when a row becomes readable, not on every pinch step.
  const zoom = Math.round(t.k * 10) / 10;
  return <div className="tree-main">
    <div className="tree-canvas">
      <div ref={stage} className={`stage${moving ? ' moving' : ''}${resizing ? ' resizing' : ''}`}
        role="group" aria-label={labels.graph}>
        {layout && <div className="world" style={{width:layout.width, height:layout.height, transform:`translate(${t.x}px,${t.y}px) scale(${t.k})`}}>
          <TreeTiles layout={layout} model={model} center={id} hot={hot} labels={labels} actions={actions} zoom={zoom}
            drawn={`${id}:${level}:${layout.width}`}/>
        </div>}
        <div className="controls" data-pan-ignore>
          <button aria-label={labels.farther} title={labels.farther} onClick={farther} disabled={!canWiden}>−</button>
          <span key={bumped} className={`lvl${bumped ? ' bump' : ''}`} title={labels.levelTitle} aria-label={`${labels.levelTitle}: ${level}`}><b>{level}</b><i>↑</i></span>
          <button aria-label={labels.closer} title={labels.closer} onClick={() => closer()} disabled={level <= 1}>+</button>
          <button aria-label={labels.recenter} title={labels.recenter} onClick={fit}>⌖</button>
        </div>
        {children}
      </div>
    </div>
  </div>;
}
