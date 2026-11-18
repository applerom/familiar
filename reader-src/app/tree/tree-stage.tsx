'use client';
import {memo,useCallback,useEffect,useLayoutEffect,useMemo,useRef,useState,type CSSProperties,type ReactNode,type RefObject} from 'react';
import {STACK_STEP,layoutTree,levelRange,type Layout} from './layout';
import {useZoomPan} from './use-zoom-pan';
import {lifeLabel,type Model,type Row} from './model';
import {growthWords} from './growth';

type TileActions = {
  open: (id: string) => void;
  hover: (id: string) => void;
};
const uncertain = (status: string) => status === 'hypothesis' || status === 'probable';
// What a compact tile can carry at its size on the screen: the whole name with the years,
// the given name with a year, an initial, or nothing but its colour.
const WHOLE = .7, SHORT = 40, INITIAL = 13;

const TreeTiles = memo(function TreeTiles({layout,model,center,hot,labels,actions,zoom,drawn}: {
  layout: Layout; model: Model; center: string; hot: string; labels: Row;
  actions: RefObject<TileActions>; zoom: number; drawn: string;
}) {
  const lang = labels.languageCode;
  const words = growthWords[lang] || growthWords.en;
  return <>
    <svg key={drawn} className="tree-links" width={layout.width} height={layout.height} aria-hidden="true">
      <g transform={`translate(${layout.linkOffset} 0)`}>{layout.links.map(link =>
        <path key={link.key} d={link.d}
          className={`lk ${link.kind} g${Math.min(link.gen, 4)}${uncertain(link.status) ? ' hyp' : ''}${link.ids.includes(center) || hot && link.ids.includes(hot) ? ' on' : ''}`}
          style={link.color ? {stroke: `color-mix(in srgb, ${link.color} 58%, var(--tree-paper))`} : undefined}/>
      )}</g>
    </svg>
    {layout.tiles.map(tile => {
      const {id, gen, stackLayers} = tile;
      const distant = tile.compact;
      const whole = !distant || tile.scale * zoom >= WHOLE;
      const mini = !whole && tile.w * zoom < SHORT;
      const style = {
        transform: `translate(${tile.x}px,${tile.y}px)`, width: tile.w, height: tile.h, '--b': tile.color, '--s': tile.scale,
        '--c': Math.min(1.05, Math.max(.62, tile.w / 66)), '--w': tile.w, '--depth-opacity': tile.fade,
      } as CSSProperties;
      const person = model.info[id];
      const life = !person.connector && (person.birthText || person.deathText) ? lifeLabel(person, labels, lang) : '';
      const year = person.birthText || person.deathText;
      const growth = person.growth;
      const confirmed = growth.confirmed.length > 0;
      const title = [person.fullName, life, confirmed ? words.confirmed : growth.treeMemory ? words.tree : growth.memory ? words.memory : growth.found ? words.found : ''].filter(Boolean).join(' · ');
      return <div key={id} className={`tile-position${distant ? ' tile-distant' : ''}${distant && whole ? ' tile-whole' : ''}${mini ? ' tile-mini' : ''}`} style={style} data-gen={gen}>
        {Array.from({length: stackLayers}, (_, i) => {
          const offset = (stackLayers - i) * STACK_STEP;
          return <span key={i} className="stack-back" aria-hidden="true" style={{translate: `${offset}px ${-offset}px`}}/>;
        })}
        <button data-person={id} className={`tree-tile${uncertain(tile.status) ? ' hyp' : ''}${id === center ? ' tree-centre' : ''}`}
          title={title} aria-label={title} aria-current={id === center ? 'true' : undefined}
          onClick={() => actions.current.open(id)}
          onPointerEnter={event => { if (event.pointerType === 'mouse') actions.current.hover(id); }}
          onPointerLeave={() => actions.current.hover('')}>
          {mini ? tile.w * zoom >= INITIAL && <strong>{(person.givenName || person.treeName).slice(0, 1)}</strong>
            : <strong>{whole ? person.treeName : person.givenName || person.treeName}</strong>}
          {mini ? null : whole ? life && <small className={person.guess ? 'guess' : undefined}>{life}</small>
            : year && !person.connector && <small className={person.guess ? 'guess' : undefined}>{year}</small>}
          {!distant && (confirmed || growth.firmMemory) && <span className="tile-provenance" aria-hidden="true">
            <i className="growth-confirm">✓</i>
            {confirmed && <i>▤</i>}
          </span>}
        </button>
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

  // The wheel and the two round buttons move by one generation of ancestors: farther draws one more row,
  // closer drops the oldest one, and the picture fills the screen again. A pinch only scales the picture.
  const step = useCallback((direction: number) => setWant(asked =>
    Math.min(range.max, Math.max(1, Math.min(range.max, asked ?? range.auto) + direction))), [range]);
  const {t,setT,moving} = useZoomPan(stage, {min: .45, max: 3.5, content, horizontalWheel: true, onStep: step});
  const fit = useCallback(() => {
    if (!layout || !size.h) return;
    const oldest = layout.horizon ? 0 : layout.box.y0;
    const height = layout.box.y1 - oldest;
    // The whole drawn tree fills the stage: neither a row nor a generation is left outside.
    const width = layout.box.x1 - layout.box.x0;
    const k = Math.min(size.w < 560 ? 1.25 : 1.45, Math.max(.5, Math.min((room - 12) / height, (size.w - 12) / width)));
    const x = size.w / 2 - (layout.box.x0 + layout.box.x1) / 2 * k;
    const y = Math.min(Math.max(4, (room - height * k) / 2) - oldest * k, room - layout.familyBottom * k);
    setT({k,x,y});
  }, [layout,size,room,setT]);
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
      else if (event.key === '+' || event.key === '=') step(-1);
      else if (event.key === '-' || event.key === '_') step(1);
      else if (event.key === '0' || event.key === 'Home') fit();
    };
    addEventListener('keydown', key);
    return () => removeEventListener('keydown', key);
  }, [model,id,go,step,fit]);

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
          <button aria-label={labels.farther} title={labels.farther} onClick={() => step(1)} disabled={level >= range.max}>−</button>
          <span className="lvl" title={labels.levelTitle} aria-label={`${labels.levelTitle}: ${level}`}><b>{level}</b><i>↑</i></span>
          <button aria-label={labels.closer} title={labels.closer} onClick={() => step(-1)} disabled={level <= 1}>+</button>
          <button aria-label={labels.recenter} title={labels.recenter} onClick={fit}>⌖</button>
        </div>
        {children}
      </div>
    </div>
  </div>;
}
