'use client';
import {useCallback,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {KinshipExplanation} from '../kinship-words';
import {NEUTRAL,kinPhrase,relationPhrase,lifeLabel,lineTitle,placeLabel,type Model,type Row} from './model';
import {useZoomPan} from './use-zoom-pan';
export type Overview={pos:Map<string,{x:number;y:number}>;links:[string,string][];w:number;h:number;rows:number;axis:{y:number;label:string;major:boolean}[];years:Map<string,number>;estimated:Set<string>;y0:number;y1:number};
const SP=26,PPY=2.6,STEP=28;
/**
 * One picture of the whole connected family on a time scale: the vertical position is the year of birth
 * (estimated from parents, children and partners when unknown), left-to-right order follows the generations.
 */
export function buildOverview(m:Model):Overview|null{
 if(!m.homes.length)return null;
 const ups=(id:string)=>[...m.parents(id).slots.filter(Boolean).map(s=>s!.id),...m.parents(id).extra.map(s=>s.id)];
 // 1. ancestors of the two home people form the crown: each one sits above its child, branches share width by size
 const gen=new Map<string,number>(),at=new Map<string,number>();const weight=new Map<string,number>();
 const wt=(id:string,guard:Set<string>=new Set()):number=>{if(weight.has(id))return weight.get(id)!;if(guard.has(id))return 1;guard.add(id);const w=1+m.parents(id).slots.reduce((s,p)=>s+(p?wt(p.id,guard):0),0);weight.set(id,w);return w};
 const put=(id:string,a:number,b:number,g:number)=>{if(gen.has(id))return;gen.set(id,g);at.set(id,(a+b)/2);const [f,mo]=m.parents(id).slots;const fa=f&&!gen.has(f.id)?f.id:'',ma=mo&&!gen.has(mo.id)?mo.id:'';
  if(fa&&ma){const share=Math.min(.8,Math.max(.2,wt(fa)/(wt(fa)+wt(ma))));const mid=a+(b-a)*share;put(fa,a,mid,g+1);put(ma,mid,b,g+1)}else if(fa||ma)put(fa||ma,a,b,g+1)};
 m.homes.forEach((h,i)=>put(h,i/m.homes.length,(i+1)/m.homes.length,0));
 // 2. everyone else hangs next to the nearest placed relative
 const queue=[...gen.keys()];
 for(let i=0;i<queue.length;i++){const c=queue[i];const g=gen.get(c)!;
  const next:[string,number][]=[...ups(c).map(p=>[p,g+1] as [string,number]),...m.children(c).map(k=>[k,g-1] as [string,number]),...m.spouses(c).map(s=>[s,g] as [string,number])];
  for(const [n,ng] of next){if(!gen.has(n)&&!m.info[n].placeholder){gen.set(n,ng);at.set(n,at.get(c)!);queue.push(n)}}}
 const links:[string,string][]=[];const seen=new Set<string>();for(const id of queue)ups(id).forEach(p=>{if(gen.has(p)&&!seen.has(id+'|'+p)){seen.add(id+'|'+p);links.push([id,p])}});
 // 3. years: a known birth year, otherwise the average of parents + 28, children − 28 and partners, settled over a few passes
 const years=new Map<string,number>();const estimated=new Set<string>();
 // the engine's guess (tree.first_child_age) places people nobody dated; only those without one are settled here
 const free:string[]=[];
 for(const id of queue){const i=m.info[id];const y=i.birth??i.guess?.exact;if(y)years.set(id,y);if(!i.birth)estimated.add(id);if(!y)free.push(id)}
 for(let pass=0;pass<40;pass++){let changed=false;
  for(const id of free){const c:number[]=[];ups(id).forEach(p=>{const y=years.get(p);if(y!==undefined)c.push(y+STEP)});m.children(id).forEach(k=>{const y=years.get(k);if(y!==undefined)c.push(y-STEP)});m.spouses(id).forEach(s=>{const y=years.get(s);if(y!==undefined)c.push(y)});
   if(!c.length)continue;const v=Math.round(c.reduce((a,b)=>a+b,0)/c.length);if(years.get(id)!==v){years.set(id,v);changed=true}}
  if(!changed)break}
 const home0=years.get(m.homes[0])??1970;
 for(const id of queue)if(!years.has(id))years.set(id,home0-gen.get(id)!*STEP);
 for(const [id,y] of years)years.set(id,Math.min(2030,Math.max(1600,y)));
 // 4. left-to-right: generation rows, every child under the midpoint of its parents, neighbours pushed apart
 const rowsMap=new Map<number,string[]>();for(const [id,g] of gen)(rowsMap.get(g)||rowsMap.set(g,[]).get(g)!).push(id);
 const keys=[...rowsMap.keys()].sort((a,b)=>b-a);const widest=Math.max(...keys.map(k=>rowsMap.get(k)!.length));
 for(const k of keys)for(const id of rowsMap.get(k)!){const ps=m.parents(id).slots.filter(Boolean).map(s=>s!.id).filter(p=>gen.get(p)===k+1);if(ps.length)at.set(id,ps.reduce((s,p)=>s+at.get(p)!,0)/ps.length)}
 const W=Math.max(900,widest*SP*1.15);
 const ys=[...years.values()];const y0=Math.floor((Math.min(...ys)-8)/25)*25,y1=Math.ceil((Math.max(...ys)+6)/25)*25;
 const pos=new Map<string,{x:number;y:number}>();
 for(const k of keys){const row=rowsMap.get(k)!.sort((a,b)=>at.get(a)!-at.get(b)!||a.localeCompare(b));const xs=row.map(id=>at.get(id)!*W);
  for(let pass=0;pass<60;pass++){let moved=false;for(let i=1;i<xs.length;i++){const d=xs[i]-xs[i-1];if(d<SP){const push=(SP-d)/2;xs[i-1]-=push;xs[i]+=push;moved=true}}if(!moved)break}
  row.forEach((id,i)=>pos.set(id,{x:xs[i],y:(years.get(id)!-y0)*PPY}))}
 // dots of neighbouring generations can land on the same year: nudge them apart sideways until nobody touches
 const all=[...pos.values()];
 for(let pass=0;pass<14;pass++){all.sort((a,b)=>a.x-b.x);let moved=false;
  for(let i=0;i<all.length;i++)for(let j=i+1;j<all.length&&all[j].x-all[i].x<SP*.9;j++){const A=all[i],B=all[j];if(Math.abs(A.y-B.y)<16){const push=(SP*.9-(B.x-A.x))/2+.5;A.x-=push;B.x+=push;moved=true}}
  if(!moved)break}
 const minX=Math.min(...[...pos.values()].map(p=>p.x));const maxX=Math.max(...[...pos.values()].map(p=>p.x));
 for(const p of pos.values())p.x-=minX;
 const axis:{y:number;label:string;major:boolean}[]=[];for(let y=y0;y<=y1;y+=25)axis.push({y:(y-y0)*PPY,label:String(y),major:y%50===0});
 return {pos,links,w:maxX-minX,h:(y1-y0)*PPY,rows:keys.length,axis,years,estimated,y0,y1};
}
const PAD=30,PADL=78;
function Dots({ov,model,visible,center,selected,onPick,onHover,detail,k,names}:{ov:Overview;model:Model;visible:Set<string>;center:string;selected?:string;onPick?:(id:string)=>void;onHover?:(id:string)=>void;detail:boolean;k:number;names:Set<string>}){
 const col=(id:string)=>model.tone(id)?.color||NEUTRAL;
 // a link carries a line's colour when it runs between two people of that line: full for the ancestor backbone, light for kin
 const homes=new Set(model.homes);
 const linkTone=(child:string,parent:string)=>{const p=model.tone(parent);if(!p)return null;if(!p.kin&&(homes.has(child)||model.tone(child)?.kin===false))return {color:p.color,kin:false};const c=model.tone(child);return c&&c.line===p.line?{color:c.color,kin:true}:null};
 const tones=ov.links.map(([a,b])=>linkTone(a,b));
 const dim=(id:string)=>{const tn=model.tone(id);return tn?(tn.kin?.8:.85):.55};
 const r=detail?7:20;const fs=11/Math.max(k,.3);
 const label=(id:string)=>{const i=model.info[id];if(i.providedName)return i.providedName;const sur=i.short.split(' ').filter(x=>/\p{L}/u.test(x)).slice(-1)[0]||i.short;return k>=3?i.short:k>=1.7?sur.slice(0,10):names.has(id)?i.short:''};
 const grid=detail?ov.axis.filter(a=>a.major||k>=1.8):ov.axis.filter(a=>Number(a.label)%100===0);
 return <>
  <g className="ov-grid">{grid.map(a=><line key={'l'+a.label} x1={-PADL+(detail?6:0)} x2={ov.w+PAD} y1={a.y} y2={a.y} stroke={a.major?'#c9cfbf':'#dde1d4'} strokeWidth={detail?1/Math.max(k,.5):4} strokeDasharray={a.major?undefined:'4 6'}/>)}</g>
  {detail?grid.map(a=><text key={'t'+a.label} x={-PADL+8} y={a.y+fs*.35} fontSize={fs*1.15} fill="#8a9488" fontWeight={a.major?700:500}>{a.label}</text>)
   :grid.map(a=><text key={'t'+a.label} x={-PADL+4} y={a.y-10} fontSize={Math.min(90,ov.h/6)} fill="#8a9488" fontWeight={700}>{a.label}</text>)}
  {[...visible].map(id=>{const p=ov.pos.get(id);return p?<circle key={'g'+id} cx={p.x} cy={p.y} r={detail?26:70} fill="#f0c36b" opacity={detail?.28:.22}/>:null})}
  <g stroke="#9fb39a" strokeWidth={detail?1.4:3} opacity={detail?.35:.5}>{ov.links.map(([a,b],i)=>{if(tones[i])return null;const A=ov.pos.get(a)!,B=ov.pos.get(b)!;return <line key={i} x1={A.x} y1={A.y} x2={B.x} y2={B.y}/>})}</g>
  <g>{ov.links.map(([a,b],i)=>{const tn=tones[i];if(!tn)return null;const A=ov.pos.get(a)!,B=ov.pos.get(b)!;return <line key={i} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={tn.color} strokeWidth={tn.kin?(detail?1.3:3):(detail?1.9:5)} opacity={tn.kin?(detail?.55:.6):(detail?.6:.75)}/>})}</g>
  {/* the part of the tree on screen now: its links drawn bolder in their own line colour, amber where no line runs */}
  <g strokeWidth={detail?2.6:6} opacity=".95">{ov.links.map(([a,b],i)=>{if(!visible.has(a)||!visible.has(b))return null;const A=ov.pos.get(a)!,B=ov.pos.get(b)!;return <line key={i} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={tones[i]&&!tones[i]!.kin?tones[i]!.color:'#e8a63b'}/>})}</g>
  {[...ov.pos].map(([id,p])=>{const on=visible.has(id);const here=id===center;const sel=id===selected;return <circle key={id} cx={p.x} cy={p.y} r={here?r*1.8:sel?r*1.6:on?r*1.25:r*.9} fill={here?'#d98a1f':col(id)} opacity={here||on||sel?1:dim(id)} stroke={sel?'#233a31':here?'#fff':'none'} strokeWidth={detail?2:3} pointerEvents="none">{onPick&&<title>{model.info[id].name+(model.info[id].life?' · '+model.info[id].life:'')}</title>}</circle>})}
  {onPick&&[...ov.pos].map(([id,p])=><circle key={'hit'+id} className="ovdot" cx={p.x} cy={p.y} r={Math.max(22/k,r*1.8)} fill="transparent" role="button" tabIndex={0} aria-label={model.info[id].name} onPointerEnter={e=>{if(e.pointerType==='mouse')onHover?.(id)}} onFocus={()=>onHover?.(id)} onClick={()=>onPick(id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onPick(id)}}}/>)}
  {detail&&[...ov.pos].map(([id,p])=>{const t=label(id);const text=id===selected?[model.info[id].short,model.info[id].life].filter(Boolean).join(' · '):t;return text?<text key={'t'+id} x={p.x} y={p.y+r*2.3+fs*.6} fontSize={fs} textAnchor="middle" fill="#2b4338" fontWeight={id===center||id===selected?700:500} stroke="#f6f3ea" strokeWidth={fs*.35} paintOrder="stroke">{text}</text>:null})}
 </>
}
export function MiniMap({ov,model,visible,center,onOpen,label,caption}:{ov:Overview;model:Model;visible:Set<string>;center:string;onOpen:()=>void;label:string;caption?:string}){
 return <button className="minimap" onClick={onOpen} aria-label={label} title={label}><svg viewBox={`${-PADL} ${-PAD} ${ov.w+PADL+PAD} ${ov.h+PAD*2}`} preserveAspectRatio="xMidYMid meet" aria-hidden="true"><Dots ov={ov} model={model} visible={visible} center={center} detail={false} k={1} names={new Set()}/></svg>{caption&&<small>{caption}</small>}</button>
}
export function OverviewDialog({ov,model,visible,center,go,onClose,labels,language,me}:{ov:Overview;model:Model;visible:Set<string>;center:string;go:(id:string)=>void;onClose:()=>void;labels:Row;language:string;me?:string}){
 const box=useRef<HTMLDivElement>(null);const cw=ov.w+PAD+PADL,ch=ov.h+PAD*2;const content=useRef({w:cw,h:ch});
 const {t,setT,moving,zoomBy}=useZoomPan(box,{min:.3,max:9,content,margin:120});
 const [selected,setSelected]=useState('');
 const fitK=()=>{const el=box.current;return el?Math.min(el.clientWidth/cw,el.clientHeight/ch):1};
 const fit=useCallback(()=>{const el=box.current;if(!el)return;const k=Math.min(el.clientWidth/cw,el.clientHeight/ch);setT({k,x:(el.clientWidth-cw*k)/2,y:(el.clientHeight-ch*k)/2})},[cw,ch,setT]);
 const focusAt=useCallback((id:string,k:number)=>{const el=box.current,p=ov.pos.get(id);if(!el||!p)return;setT({k,x:el.clientWidth/2-(p.x+PADL)*k,y:el.clientHeight/2-(p.y+PAD)*k})},[ov,setT]);
 // wide maps on a narrow screen open on the current person; otherwise show everything at once
 useLayoutEffect(()=>{if(fitK()<.55)focusAt(center,1.1);else fit()},[]);// eslint-disable-line react-hooks/exhaustive-deps
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose()};addEventListener('keydown',key);return()=>removeEventListener('keydown',key)},[onClose]);
 const heads=new Set<string>([center,...model.lines.map(l=>l.id),...model.homes]);
 const focus=(id:string)=>{setSelected(id);focusAt(id,Math.max(t.k,1.4))};
 const pick=(id:string)=>{go(id);onClose()};
 const sel=selected?model.info[selected]:null;const kin=!selected?[]:me&&model.info[me]?[model.relation(me,selected)].filter(Boolean).map(r=>relationPhrase(r!,labels,language)):model.kinship(selected).map(k=>kinPhrase(k,labels,language));
 const role=(l:{id:string;role:string;home:string})=>lineTitle(l,model,labels);
 const when=sel&&!sel.birth&&!sel.death?'≈'+(sel.guess?.year??ov.years.get(selected)):'';
 return <div className="overview" role="dialog" aria-modal="true" aria-label={labels.overviewTitle}>
  <div className="ov-head"><div><h2>{labels.overviewTitle}</h2><p>{labels.overviewHint}</p></div><button className="ov-close" onClick={onClose} aria-label={labels.close}>×</button></div>
  <div className="ov-lines">{model.lines.map(l=><button key={l.id} onClick={()=>focus(l.id)}><i style={{background:l.color}}/><span><b>{model.info[l.id].short}</b><small>{role(l)}</small></span></button>)}</div>
  <div ref={box} className={'ov-stage'+(moving?' moving':'')} onClick={e=>{if((e.target as Element).tagName==='svg'||(e.target as Element).classList.contains('ov-stage'))setSelected('')}}>
   <svg width={cw} height={ch} className="ov-svg" style={{transform:`translate(${t.x}px,${t.y}px) scale(${t.k})`}}><g transform={`translate(${PADL},${PAD})`}><Dots ov={ov} model={model} visible={visible} center={center} selected={selected} detail onPick={pick} onHover={setSelected} k={t.k} names={heads}/></g></svg>
   <div className="controls"><button aria-label={labels.zoomIn} onClick={()=>zoomBy(1.4)}>+</button><button aria-label={labels.zoomOut} onClick={()=>zoomBy(1/1.4)}>−</button><button aria-label={labels.recenter} title={labels.recenter} onClick={()=>focusAt(center,1.4)}>⌖</button><button aria-label={labels.showWhole} title={labels.showWhole} onClick={fit}>⤢</button></div>
   {sel&&<div className="ov-card"><div><strong>{sel.short}</strong><small>{[lifeLabel(sel,labels,language)||sel.note||when,placeLabel(sel,labels)].filter(Boolean).join(' · ')}</small>{selected&&me&&model.relation(me,selected)?<KinshipExplanation relation={model.relation(me,selected)!} model={model} labels={labels} language={language}/>:kin.length>0&&<small className="rel">{kin.join(' · ')}</small>}</div></div>}
  </div>
  <p className="ov-foot">{labels.overviewFoot}</p>
 </div>
}
