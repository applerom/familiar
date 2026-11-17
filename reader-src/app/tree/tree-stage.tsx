'use client';
import {useCallback,useEffect,useLayoutEffect,useMemo,useRef,useState,type CSSProperties,type ReactNode} from 'react';
import {layoutTree,levelRange,type Layout,type Node} from './layout';
import {useZoomPan} from './use-zoom-pan';
import {lifeLabel,type Model} from './model';
import {growthWords} from './growth';
type Row=Record<string,any>;
function Person({n,model,go,labels,lang}:{me?:string;n:Node;model:Model;go:(id:string)=>void;labels:Row;lang:string}){
 const p=model.info[n.id];const b=n.color||undefined;
 const style={transform:`translate(${n.x}px,${n.y}px)`,width:n.w,height:n.h,'--b':b} as CSSProperties;
 if(n.size==='ring')return <span className="n ring" style={style} aria-hidden="true">⚭</span>;
 const life=!p.connector&&(p.birthText||p.deathText)?lifeLabel(p,labels,lang):'';
 const place=!p.connector&&p.placeRole==='birth'?p.place:'';
 const w=growthWords[lang]||growthWords.en; const g=p.growth;const docMark=g.confirmed.length>0;
 const title=[p.treeName,life,place,docMark?w.confirmed:g.treeMemory?w.tree:g.memory?w.memory:g.found?w.found:'',!docMark&&(g.documents.length>0||g.hasMedia)?w.unconfirmed:''].filter(Boolean).join(' · ');
 if(n.size==='dot'||n.size==='tiny')return <button data-person={n.id} className={`n ${n.size} ${n.kin?'line-kin':''}`} style={style} title={title} aria-label={title} onClick={()=>go(n.id)}><span className="c" style={{width:n.w,height:n.w}}>{n.size==='dot'?p.treeName.slice(0,1):''}</span>{n.label&&<span className="dl" style={{maxWidth:Math.max(56,n.w*1.9)}}>{n.label}</span>}</button>;
 if(n.size==='kids'||n.size==='up')return <button data-person={n.id} className={'n '+n.size} style={style} aria-label={`${p.treeName}: ${n.count}`} title={title} onClick={()=>go(n.id)}>{n.size==='kids'?'▾':'▴'} {n.count}</button>;
 if(n.size==='pill')return <button data-person={n.id} className="n pill" style={style} title={title} onClick={()=>go(n.id)}>{p.treeName}</button>;
 return <button data-person={n.id} className={`n card ${n.size} ${n.kin?'line-kin':''} ${n.w<200?'tight':''} ${n.center?'center':''}`} style={style} title={title} aria-current={n.center?'true':undefined} onClick={()=>go(n.id)}>
  <span className="growth-icons" aria-hidden="true">{(docMark||g.firmMemory)&&<i className="growth-confirm">✓</i>}{(docMark||g.documents.length>0||g.hasMedia)&&<i className={docMark?undefined:'doc-open'}>▤</i>}</span><span className="tx"><strong>{p.treeName}</strong>{life&&<small className={p.guess?'guess':undefined}>{life}</small>}{place&&<small className="pl">{place}</small>}</span>
 </button>
}
export default function TreeStage({model,id,go,jump,onUse,labels,onLayout,children,me}:{me?:string;model:Model;id:string;go:(id:string)=>void;jump?:(id:string)=>void;onUse?:()=>void;labels:Row;onLayout?:(l:Layout)=>void;children?:ReactNode}){
 const lang=labels.languageCode||'ru';
 const stage=useRef<HTMLDivElement>(null);const content=useRef({w:0,h:0});const baseK=useRef(1);const [size,setSize]=useState({w:0,h:0});const [bias,setBias]=useState(0);const [resizing,setResizing]=useState(false);
 // while the window is being resized the tree follows the new size at once; the glide animation would otherwise chase every intermediate size
 useLayoutEffect(()=>{const el=stage.current;if(!el)return;let timer:ReturnType<typeof setTimeout>|undefined;let first=true;
  const measure=()=>{setSize(s=>s.w===el.clientWidth&&s.h===el.clientHeight?s:{w:el.clientWidth,h:el.clientHeight});if(first){first=false;return}setResizing(true);clearTimeout(timer);timer=setTimeout(()=>setResizing(false),260)};
  measure();const o=new ResizeObserver(measure);o.observe(el);return()=>{o.disconnect();clearTimeout(timer)}},[]);
 const reserve=size.w<820?68:82;const room=size.h-reserve;
 // semantic zoom: "level" is how many generations of ancestors are drawn; zooming out pulls more of the tree in
 const range=useMemo(()=>size.w?levelRange(model,id,size.w,room):{max:1,auto:1},[model,id,size.w,room]);
 const level=Math.min(range.max,Math.max(1,range.auto+bias));
 const layout=useMemo(()=>size.w?layoutTree(model,id,size.w,level):null,[model,id,size.w,level]);
 content.current=layout?{w:layout.width,h:layout.height}:{w:0,h:0};
 useEffect(()=>{if(layout)onLayout?.(layout)},[layout]);// eslint-disable-line react-hooks/exhaustive-deps
 const {t,setT,moving,zoomBy,focal}=useZoomPan(stage,{min:.3,max:3.5,content});
 // fill the stage: scale the drawn part (not the empty page) up or down to fit
 const fit=useCallback(()=>{if(!layout||!size.h)return;const b=layout.box;const bw=b.x1-b.x0,bh=b.y1-b.y0;const kmax=size.w<560?1.25:1.45;
  const k=Math.max(.42,Math.min(kmax,(size.w-16)/bw,(room-10)/bh));baseK.current=k;setT({k,x:(size.w-bw*k)/2-b.x0*k,y:Math.max(4,(room-bh*k)/2)-b.y0*k})},[layout,size.h,size.w,room,setT]);
 useEffect(()=>{fit()},[fit]);
 const farther=useCallback(()=>{if(level<range.max)setBias(level+1-range.auto)},[level,range]);
 const closer=useCallback(()=>{if(level>1)setBias(level-1-range.auto);else zoomBy(1.25)},[level,range,zoomBy]);
 // Zooming like a map, in people instead of pixels. While a wheel or pinch gesture runs, every step away from the fitted
 // scale changes what is drawn. Inwards over a person moves the tree to that person and keeps the branch that was
 // visible above them; inwards elsewhere drops a generation. Outwards adds a generation; once all are open it goes back
 // the way the wheel came in, and with no such way (a click, a #person= link) one step along the kinship path to the
 // family's home people, so the wheel always leads back to the wide tree. Clicks and the wheel never exclude each
 // other; the whole-family view opens from the corner miniature alone.
 const spent=useRef(false);
 // the way back for the wheel: each person a gesture zoomed away from, with the generations open there
 const trail=useRef<{id:string;bias:number}[]>([]);const expected=useRef('');
 const homeward=useMemo(()=>{const next=new Map<string,{id:string;kind:'down'|'up'|'mate'}>();const seen=new Set(model.homes);const q=[...model.homes];
  for(let i=0;i<q.length;i++){const x=q[i];const step=(y:string,kind:'down'|'up'|'mate')=>{if(!seen.has(y)&&model.info[y]&&!model.info[y].placeholder){seen.add(y);next.set(y,{id:x,kind});q.push(y)}};
   model.parents(x).slots.forEach(sl=>sl&&step(sl.id,'down'));model.children(x).forEach(c=>step(c,'up'));model.spouses(x).forEach(m=>step(m,'mate'))}
  return next},[model]);
 const moveTo=useCallback((pid:string,want:number)=>{const next=levelRange(model,pid,size.w,room);expected.current=pid;setBias(Math.min(next.max,Math.max(1,want))-next.auto);go(pid)},[model,size.w,room,go]);
 const outward=useCallback(()=>{const back=trail.current.pop();if(back){expected.current=back.id;setBias(back.bias);go(back.id);return}
  const nx=homeward.get(id);if(nx)moveTo(nx.id,nx.kind==='down'?level+1:nx.kind==='up'?level-1:level)},[homeward,id,level,go,moveTo]);
 const canWiden=level<range.max||trail.current.length>0||homeward.has(id);
 const wider=useCallback(()=>{if(level<range.max)farther();else outward()},[level,range,farther,outward]);
 const personAt=(p:{x:number;y:number}):Node|null=>{if(!layout)return null;const x=(p.x-t.x)/t.k,y=(p.y-t.y)/t.k;let best:Node|null=null,bd=24/t.k;
  for(const n of layout.nodes){if(n.size==='ring')continue;const d=Math.hypot(Math.max(n.x-x,0,x-n.x-n.w),Math.max(n.y-y,0,y-n.y-n.h));if(d<bd){bd=d;best=n}}return best};
 useEffect(()=>{if(!moving||!focal.current||spent.current||!layout)return;const r=t.k/baseK.current;
  if(r<.78)wider();
  else if(r>1.32){const hit=personAt(focal.current);
   if(hit&&hit.gen!==0){const next=levelRange(model,hit.id,size.w,room);const want=Math.min(next.max,Math.max(1,hit.gen>0?level-hit.gen:level));spent.current=true;trail.current.push({id,bias});expected.current=hit.id;setBias(want-next.auto);(jump||go)(hit.id)}
   else if(level>1)closer()}},[t.k]);// eslint-disable-line react-hooks/exhaustive-deps
 // a gesture that already moved the tree elsewhere leaves the new picture fitted
 useEffect(()=>{if(moving)onUse?.();else if(spent.current){spent.current=false;fit()}},[moving]);// eslint-disable-line react-hooks/exhaustive-deps
 // a person reached by the wheel keeps the way back; the back button returns along it with the generations open
 // there; any other choice of a person (a click, a link, the search) starts a new way
 useEffect(()=>{if(id===expected.current){expected.current='';return}const top=trail.current[trail.current.length-1];
  if(top&&top.id===id){trail.current.pop();setBias(top.bias)}else trail.current=[]},[id]);
 // keyboard: up = parents, down = children, left / right = brothers and sisters, then partner
 useEffect(()=>{const key=(e:KeyboardEvent)=>{const el=e.target as HTMLElement;if(/INPUT|TEXTAREA|SELECT/.test(el.tagName)||e.metaKey||e.ctrlKey||e.altKey)return;
   const [f,mo]=model.parents(id).slots;const kids=model.children(id);const sibs=[...model.siblings(id),id].sort((a,b)=>(model.info[a].birth??9999)-(model.info[b].birth??9999));const i=sibs.indexOf(id);const mate=model.spouses(id)[0];
   const to=e.key==='ArrowUp'?(f||mo)?.id:e.key==='ArrowDown'?kids[0]:e.key==='ArrowLeft'?(sibs[i-1]||mate):e.key==='ArrowRight'?(sibs[i+1]||mate):'';
   if(to){e.preventDefault();go(to)}else if(e.key==='+'||e.key==='=')closer();else if(e.key==='-'||e.key==='_')wider();else if(e.key==='0'||e.key==='Home')fit()};
  addEventListener('keydown',key);return()=>removeEventListener('keydown',key)},[model,id,go,closer,wider,fit]);
 return <div ref={stage} className={'stage'+(moving?' moving':'')+(resizing?' resizing':'')} role="group" aria-label={labels.graph}>
  {layout&&<div className="world" style={{width:layout.width,height:layout.height,transform:`translate(${t.x}px,${t.y}px) scale(${t.k})`}}>
   <svg className="links" width={layout.width} height={layout.height} key={id+':'+layout.width+':'+level} aria-hidden="true">
    {layout.links.map(l=><path key={l.key} d={l.d} className={`lk ${l.kind} g${Math.min(l.gen,4)} ${l.status==='hypothesis'?'hyp':''} ${l.color?'tone':''}`} style={l.color?{'--lb':l.color} as CSSProperties:undefined}/>)}
    {layout.fogs.map((f,i)=><path key={'f'+i} d={`M${f.x},${f.y} L${f.x},${f.y-26}`} className="lk fog"/>)}
   </svg>
   {layout.nodes.map(n=><Person me={me} key={n.key} n={n} model={model} go={go} labels={labels} lang={lang}/>)}
  </div>}
  <div className="veil" aria-hidden="true"/>
  <div className="controls"><button aria-label={labels.farther} title={labels.farther} onClick={wider} disabled={!canWiden}>−</button><span className="lvl" title={labels.levelTitle} aria-label={`${labels.levelTitle}: ${level}`}><b>{level}</b><i>↑</i></span><button aria-label={labels.closer} title={labels.closer} onClick={closer}>+</button><button aria-label={labels.recenter} title={labels.recenter} onClick={fit}>⌖</button></div>
  {children}
 </div>
}
