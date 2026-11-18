'use client';
import {memo,useCallback,useEffect,useLayoutEffect,useMemo,useRef,useState,type CSSProperties,type ReactNode,type RefObject} from 'react';
import {HISTORY_LEVEL,HORIZON_Y,STACK_STEP,layoutTree,levelRange,type Layout} from './layout';
import {plural} from '../i18n';
import {useZoomPan} from './use-zoom-pan';
import {lifeLabel,type Model,type Row} from './model';
import {growthWords} from './growth';

type TileActions = {
  select: (id: string) => void;
  openFamily: (id: string) => void;
};
const uncertain = (status: string) => status === 'hypothesis' || status === 'probable';

const TreeTiles = memo(function TreeTiles({layout,model,center,selected,labels,actions}: {
  layout: Layout; model: Model; center: string; selected: string; labels: Row;
  actions: RefObject<TileActions>;
}) {
  const lang = labels.languageCode;
  const words = growthWords[lang] || growthWords.en;
  return <>
    <svg className="tree-links" width={layout.width} height={layout.height} aria-hidden="true">
      {layout.horizon && <g className="history-rays">{Array.from({length: 11}, (_, i) => {
        const x = (i - 5) * layout.width / 7;
        return <line key={i} x1={layout.axis + x * .14} y1={HORIZON_Y} x2={layout.axis + x} y2={layout.rootBottom}/>;
      })}</g>}
      <g transform={`translate(${layout.linkOffset} 0)`}>{layout.links.map(link =>
        <path key={link.key} d={link.d}
          className={`lk ${link.kind} g${Math.min(link.gen, 4)}${uncertain(link.status) ? ' hyp' : ''}`}
          style={link.color ? {stroke: `color-mix(in srgb, ${link.color} 58%, var(--tree-paper))`} : undefined}/>
      )}</g>
    </svg>
    {layout.tiles.map(tile => {
      const {id, gen, stackLayers} = tile;
      const distant = gen >= HISTORY_LEVEL;
      const style = {
        left: tile.x, top: tile.y, width: tile.w, height: tile.h, '--b': tile.color,
        '--depth-opacity': distant ? .28 + tile.scale * .63 : 1,
      } as CSSProperties;
      const person = model.info[id];
      const life = !person.connector && (person.birthText || person.deathText) ? lifeLabel(person, labels, lang) : '';
      const growth = person.growth;
      const confirmed = growth.confirmed.length > 0;
      const document = growth.documents.length > 0 || growth.hasMedia;
      const title = [person.fullName, life, confirmed ? words.confirmed : growth.treeMemory ? words.tree : growth.memory ? words.memory : growth.found ? words.found : '',
        !confirmed && document ? words.unconfirmed : ''].filter(Boolean).join(' · ');
      return <div key={id} className={`tile-position${distant ? ' tile-distant' : ''}`} style={style} data-gen={gen}>
        {Array.from({length: stackLayers}, (_, i) => {
          const offset = (stackLayers - i) * STACK_STEP;
          return <span key={i} className="stack-back" aria-hidden="true" style={{translate: `${offset}px ${-offset}px`}}/>;
        })}
        <button data-person={id} className={`tree-tile${uncertain(tile.status) ? ' hyp' : ''}${id === center ? ' tree-centre' : ''}`}
          title={title} aria-label={title} aria-pressed={id === selected}
          onClick={() => actions.current.select(id)} onDoubleClick={() => actions.current.openFamily(id)}>
          <strong>{distant ? person.givenName || person.treeName : person.treeName}</strong>
          {!distant && life && <small className={person.guess ? 'guess' : undefined}>{life}</small>}
          {!distant && (confirmed || growth.firmMemory || document) && <span className="tile-provenance" aria-hidden="true">
            {(confirmed || growth.firmMemory) && <i className="growth-confirm">✓</i>}
            {(confirmed || document) && <i className={confirmed ? undefined : 'doc-open'}>▤</i>}
          </span>}
        </button>
      </div>;
    })}
    {layout.horizon && <div className="history-fog" aria-hidden="true"/>}
  </>;
});

export default function TreeStage({model,id,selected,select,go,jump,labels,onVisible,children}: {
  model: Model; id: string; selected: string; select: (id: string) => void;
  go: (id: string) => void; jump: (id: string) => void; labels: Row;
  onVisible: (visible: Set<string>) => void; children?: ReactNode;
}) {
  const stage = useRef<HTMLDivElement>(null);
  const content = useRef({w: 0, h: 0});
  const baseScale = useRef(1);
  const [size, setSize] = useState({w: 0, h: 0});
  const [bias, setBias] = useState(0);
  const [resizing, setResizing] = useState(false);
  const actions = useRef<TileActions>({select, openFamily: jump});
  actions.current = {select, openFamily: jump};

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

  const trail = useRef<{id: string; bias: number}[]>([]);
  const expected = useRef('');
  const range = useMemo(() => levelRange(model,id), [model,id]);
  const level = Math.min(range.max, Math.max(1, range.auto + bias));
  const layout = useMemo(() => size.w ? layoutTree(model,id,size.w,level) : null, [model,id,size.w,level]);
  content.current = layout ? {w: layout.width, h: layout.height} : {w: 0, h: 0};
  useEffect(() => {
    if (layout) onVisible(layout.visible);
  }, [layout, onVisible]);

  const {t,setT,moving,zoomBy,focal} = useZoomPan(stage, {min: .52, max: 3.5, content, horizontalWheel: true});
  const fit = useCallback(() => {
    if (!layout || !size.h) return;
    const reserve = size.w < 560 ? 72 : 90;
    const room = size.h - reserve;
    const oldest = layout.horizon ? 0 : layout.box.y0;
    const height = layout.box.y1 - oldest;
    const nearWidth = layout.near.x1 - layout.near.x0;
    const nearFit = size.w >= 820 ? (size.w - 16) / nearWidth : 1;
    const k = Math.min(1, Math.max(.84, Math.min((room - 12) / height, nearFit)));
    const nearX = (layout.near.x0 + layout.near.x1) / 2;
    const x = size.w / 2 - (size.w < 560 ? layout.axis : nearX) * k;
    const y = Math.min(Math.max(4, (room - height * k) / 2) - oldest * k, room - layout.familyBottom * k);
    baseScale.current = k;
    setT({k,x,y});
  }, [layout,size,setT]);
  useLayoutEffect(fit, [fit]);

  const moveTo = useCallback((pid: string, want: number) => {
    const next = levelRange(model,pid);
    expected.current = pid;
    setBias(Math.min(next.max, Math.max(1,want)) - next.auto);
    go(pid);
  }, [model,go]);
  const homeward = useMemo(() => {
    const next = new Map<string,{id:string;kind:'down'|'up'|'mate'}>();
    const seen = new Set(model.homes);
    const queue = [...model.homes];
    for (const id of queue) {
      const step = (pid: string, kind: 'down' | 'up' | 'mate') => {
        if (seen.has(pid) || !model.info[pid] || model.info[pid].placeholder) return;
        seen.add(pid);
        next.set(pid, {id,kind});
        queue.push(pid);
      };
      for (const slot of model.parents(id).slots) if (slot) step(slot.id,'down');
      for (const child of model.children(id)) step(child,'up');
      for (const mate of model.spouses(id)) step(mate,'mate');
    }
    return next;
  }, [model]);
  const canWiden = level < range.max || trail.current.length > 0 || homeward.has(id);
  const wider = useCallback(() => {
    if (level < range.max) { setBias(level + 1 - range.auto); return; }
    const back = trail.current.pop();
    if (back) { expected.current = back.id; setBias(back.bias); go(back.id); return; }
    const next = homeward.get(id);
    if (next) moveTo(next.id, next.kind === 'down' ? level + 1 : next.kind === 'up' ? level - 1 : level);
  }, [level,range,go,homeward,id,moveTo]);
  const closer = useCallback(() => {
    if (level > 1) setBias(level - 1 - range.auto);
    else zoomBy(1.25);
  }, [level,range,zoomBy]);

  // Wheel and pinch keep the existing tree navigation. Horizontal scrolling only pans.
  const spent = useRef(false);
  useEffect(() => {
    if (!moving || !focal.current || spent.current || !layout) return;
    const ratio = t.k / baseScale.current;
    if (ratio < .78) wider();
    if (ratio <= 1.32) return;
    const x = (focal.current.x - t.x) / t.k, y = (focal.current.y - t.y) / t.k;
    const hit = layout.tiles.find(tile =>
      x >= tile.x && x <= tile.x + tile.w && y >= tile.y && y <= tile.y + tile.h);
    if (hit?.id && hit.gen !== 0) {
      const next = levelRange(model,hit.id);
      const want = Math.min(next.max, Math.max(1,level - Math.max(0,hit.gen)));
      spent.current = true;
      trail.current.push({id,bias});
      expected.current = hit.id;
      setBias(want - next.auto);
      jump(hit.id);
    } else if (level > 1) closer();
  }, [t.k]); // Evaluate once for each change of the wheel or pinch scale.
  useEffect(() => {
    if (!moving && spent.current) { spent.current = false; fit(); }
  }, [moving,fit]);
  useEffect(() => {
    if (id === expected.current) { expected.current = ''; return; }
    const previous = trail.current.at(-1);
    if (previous?.id === id) { trail.current.pop(); setBias(previous.bias); }
    else { trail.current = []; setBias(0); }
  }, [id]);
  useEffect(() => {
    const key = (event: KeyboardEvent) => {
      const el = event.target as HTMLElement;
      if (event.defaultPrevented || el.closest('input, textarea, select, dialog, .overview, .lightbox') ||
          event.metaKey || event.ctrlKey || event.altKey) return;
      const [father,mother] = model.parents(id).slots;
      const sibs = [...model.siblings(id),id].sort(model.bySeniority);
      const i = sibs.indexOf(id), mate = model.spouses(id)[0];
      const to = event.key === 'ArrowUp' ? (father || mother)?.id : event.key === 'ArrowDown' ? model.children(id)[0] :
        event.key === 'ArrowLeft' ? sibs[i-1] || mate : event.key === 'ArrowRight' ? sibs[i+1] || mate : '';
      if (to) { event.preventDefault(); go(to); }
      else if (event.key === '+' || event.key === '=') closer();
      else if (event.key === '-' || event.key === '_') wider();
      else if (event.key === '0' || event.key === 'Home') fit();
    };
    addEventListener('keydown', key);
    return () => removeEventListener('keydown', key);
  }, [model,id,go,closer,wider,fit]);

  const count = layout?.peopleCount ?? 0;
  return <div className="tree-main">
    <div className="tree-count">{layout && labels.treeCount.replace('{n}',
      `${count} ${plural(count,labels.personsForms,labels.languageCode)}`)}</div>
    <div className="tree-canvas">
      <div ref={stage} className={`stage${moving ? ' moving' : ''}${resizing ? ' resizing' : ''}`}
        role="group" aria-label={labels.graph}>
        {layout && <div className="world" style={{width:layout.width, height:layout.height, transform:`translate(${t.x}px,${t.y}px) scale(${t.k})`}}>
          <TreeTiles layout={layout} model={model} center={id} selected={selected} labels={labels} actions={actions}/>
        </div>}
        <div className="controls" data-pan-ignore>
          <button aria-label={labels.farther} title={labels.farther} onClick={wider} disabled={!canWiden}>−</button>
          <span className="lvl" title={labels.levelTitle} aria-label={`${labels.levelTitle}: ${level}`}><b>{level}</b><i>↑</i></span>
          <button aria-label={labels.closer} title={labels.closer} onClick={closer}>+</button>
          <button aria-label={labels.recenter} title={labels.recenter} onClick={fit}>⌖</button>
        </div>
        {children}
      </div>
    </div>
  </div>;
}
