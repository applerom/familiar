'use client';
import {memo,useCallback,useEffect,useLayoutEffect,useMemo,useRef,useState,type CSSProperties,type ReactNode,type RefObject} from 'react';
import {HISTORY_LEVEL,STACK_STEP,layoutTree,type Layout} from './layout';
import {useZoomPan} from './use-zoom-pan';
import {lifeLabel,type Model,type Row} from './model';
import {growthWords} from './growth';

type TileActions = {
  select: (id: string) => void;
  openFamily: (id: string) => void;
};
const uncertain = (status: string) => status === 'hypothesis' || status === 'probable';
// A distant tile shows the whole name once the zoom makes it this large on the screen.
const READABLE = .82;

const TreeTiles = memo(function TreeTiles({layout,model,center,selected,labels,actions,readable}: {
  layout: Layout; model: Model; center: string; selected: string; labels: Row;
  actions: RefObject<TileActions>; readable: number;
}) {
  const lang = labels.languageCode;
  const words = growthWords[lang] || growthWords.en;
  return <>
    <svg className="tree-links" width={layout.width} height={layout.height} aria-hidden="true">
      <g transform={`translate(${layout.linkOffset} 0)`}>{layout.links.map(link =>
        <path key={link.key} d={link.d}
          className={`lk ${link.kind} g${Math.min(link.gen, 4)}${uncertain(link.status) ? ' hyp' : ''}${link.ids.includes(selected) ? ' on' : ''}`}
          style={link.color ? {stroke: `color-mix(in srgb, ${link.color} 58%, var(--tree-paper))`} : undefined}/>
      )}</g>
    </svg>
    {layout.tiles.map(tile => {
      const {id, gen, stackLayers} = tile;
      const distant = gen >= HISTORY_LEVEL;
      const whole = !distant || tile.scale >= readable;
      const style = {
        left: tile.x, top: tile.y, width: tile.w, height: tile.h, '--b': tile.color, '--s': tile.scale,
        '--depth-opacity': distant ? .34 + tile.scale * .66 : 1,
      } as CSSProperties;
      const person = model.info[id];
      const life = !person.connector && (person.birthText || person.deathText) ? lifeLabel(person, labels, lang) : '';
      const year = person.birthText || person.deathText;
      const growth = person.growth;
      const confirmed = growth.confirmed.length > 0;
      const document = growth.documents.length > 0 || growth.hasMedia;
      const title = [person.fullName, life, confirmed ? words.confirmed : growth.treeMemory ? words.tree : growth.memory ? words.memory : growth.found ? words.found : ''].filter(Boolean).join(' · ');
      return <div key={id} className={`tile-position${distant ? ' tile-distant' : ''}${distant && whole ? ' tile-whole' : ''}`} style={style} data-gen={gen}>
        {Array.from({length: stackLayers}, (_, i) => {
          const offset = (stackLayers - i) * STACK_STEP;
          return <span key={i} className="stack-back" aria-hidden="true" style={{translate: `${offset}px ${-offset}px`}}/>;
        })}
        <button data-person={id} className={`tree-tile${uncertain(tile.status) ? ' hyp' : ''}${id === center ? ' tree-centre' : ''}`}
          title={title} aria-label={title} aria-pressed={id === selected}
          onClick={() => actions.current.select(id)} onDoubleClick={() => actions.current.openFamily(id)}>
          <strong>{whole ? person.treeName : person.givenName || person.treeName}</strong>
          {whole ? life && <small className={person.guess ? 'guess' : undefined}>{life}</small>
            : year && !person.connector && <small className={person.guess ? 'guess' : undefined}>{year}</small>}
          {!distant && (confirmed || growth.firmMemory || document) && <span className="tile-provenance" aria-hidden="true">
            {(confirmed || growth.firmMemory) && <i className="growth-confirm">✓</i>}
            {confirmed && <i>▤</i>}
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
  const [size, setSize] = useState({w: 0, h: 0});
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

  const layout = useMemo(() => size.w ? layoutTree(model,id,size.w) : null, [model,id,size.w]);
  content.current = layout ? {w: layout.width, h: layout.height} : {w: 0, h: 0};
  useEffect(() => {
    if (layout) onVisible(layout.visible);
  }, [layout, onVisible]);

  // The wheel and the pinch only scale the picture under the pointer, like a map. Who is drawn changes
  // by choosing a person, never by zooming.
  const {t,setT,moving,zoomBy} = useZoomPan(stage, {min: .45, max: 3.5, content, horizontalWheel: true});
  const fit = useCallback(() => {
    if (!layout || !size.h) return;
    const reserve = size.w < 560 ? 72 : 90;
    const room = size.h - reserve;
    const oldest = layout.horizon ? 0 : layout.box.y0;
    const height = layout.box.y1 - oldest;
    const nearWidth = layout.near.x1 - layout.near.x0;
    const nearFit = size.w >= 820 ? (size.w - 16) / nearWidth : 1;
    const k = Math.min(1.25, Math.max(.84, Math.min((room - 12) / height, nearFit)));
    const nearX = (layout.near.x0 + layout.near.x1) / 2;
    const x = size.w / 2 - (size.w < 560 ? layout.axis : nearX) * k;
    const y = Math.min(Math.max(4, (room - height * k) / 2) - oldest * k, room - layout.familyBottom * k);
    setT({k,x,y});
  }, [layout,size,setT]);
  useLayoutEffect(fit, [fit]);

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
      else if (event.key === '+' || event.key === '=') zoomBy(1.25);
      else if (event.key === '-' || event.key === '_') zoomBy(.8);
      else if (event.key === '0' || event.key === 'Home') fit();
    };
    addEventListener('keydown', key);
    return () => removeEventListener('keydown', key);
  }, [model,id,go,zoomBy,fit]);

  // Only a few distinct values, so the tiles are redrawn when a row becomes readable, not on every wheel step.
  const readable = Math.ceil(READABLE / t.k * 20) / 20;
  return <div className="tree-main">
    <div className="tree-canvas">
      <div ref={stage} className={`stage${moving ? ' moving' : ''}${resizing ? ' resizing' : ''}`}
        role="group" aria-label={labels.graph}>
        {layout && <div className="world" style={{width:layout.width, height:layout.height, transform:`translate(${t.x}px,${t.y}px) scale(${t.k})`}}>
          <TreeTiles layout={layout} model={model} center={id} selected={selected} labels={labels} actions={actions} readable={readable}/>
        </div>}
        <div className="controls" data-pan-ignore>
          <button aria-label={labels.zoomOut} title={labels.zoomOut} onClick={() => zoomBy(.8)}>−</button>
          <button aria-label={labels.zoomIn} title={labels.zoomIn} onClick={() => zoomBy(1.25)}>+</button>
          <button aria-label={labels.recenter} title={labels.recenter} onClick={fit}>⌖</button>
        </div>
        {children}
      </div>
    </div>
  </div>;
}
