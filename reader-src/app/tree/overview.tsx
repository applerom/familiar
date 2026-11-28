'use client';
import {useCallback,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {KinshipExplanation} from '../kinship-words';
import {SecondWay} from './second-way';
import {isPerson,NEUTRAL,kinPhrase,relationPhrase,lifeLabel,lineTitle,placeLabel,type Model,type Row} from './model';
import {useZoomPan} from './use-zoom-pan';
/** How firmly a link or a person holds to the family: 1 records or family memory, 2 probable, 3 our version. */
export type Hold=1|2|3;
export type Overview={pos:Map<string,{x:number;y:number}>;links:[string,string][];
 /** each link by its own weight, with the same thresholds 0.5 and 0.3 as the whole engine */
 level:Hold[];
 /** each person by all the links on the way down to the family, their weights multiplied (the best way of several) */
 hold:Map<string,Hold>;
 /** the next step down to the family: a link index (-1 across a marriage) and what that step weighs */
 down:Map<string,{to:string;link:number;f:number}>;
 /** a second way up that the data admit (model.second), person and the one who may be the parent instead: drawn thin and pale */
 seconds:[string,string][];
 /** one band of width per ancestor line, the home people's own kin and the couple's children in between */
 lanes:{key:string;x0:number;x1:number}[];
 w:number;h:number;rows:number;axis:{y:number;label:string;major:boolean}[];years:Map<string,number>;estimated:Set<string>;y0:number;y1:number};
const SP=26,PPY=2.6,STEP=28,GAP=SP*1.7;
export const holdOf=(v:number):Hold=>v>=.5?1:v>=.3?2:3;
/** What a link weighs on the way down: its own weight, else by status: a record 0.98, an imported tree or family memory 0.95,
 *  a probable version 0.4, an assumption 0.2. */
export const LINK_DEFAULT={verified:.98,firm:.95,probable:.4,assumed:.2};
export const linkFactor=(s:{status?:string;weight?:number},l:Hold)=>typeof s.weight==='number'?Math.min(1,Math.max(0,s.weight)):l===1?s.status==='verified'?LINK_DEFAULT.verified:LINK_DEFAULT.firm:l===2?LINK_DEFAULT.probable:LINK_DEFAULT.assumed;
/**
 * One picture of the whole connected family on a time scale: the vertical position is the year of birth
 * (estimated from parents, children and partners when unknown), left-to-right every ancestor line keeps a band of its own.
 * `aspect` (width to height of the screen it opens on) lets a wide screen spread the bands out instead of leaving margins.
 */
export function buildOverview(m:Model,opt:{aspect?:number}={}):Overview|null{
 if(!m.homes.length)return null;
 const ups=(id:string)=>[...m.parents(id).slots.filter(Boolean).map(s=>s!.id),...m.parents(id).extra.map(s=>s.id)];
 // 1. ancestors of the two home people form the crown: each one sits above its child, branches share width by size
 const gen=new Map<string,number>(),at=new Map<string,number>();const weight=new Map<string,number>();
 const wt=(id:string,guard:Set<string>=new Set()):number=>{if(weight.has(id))return weight.get(id)!;if(guard.has(id))return 1;guard.add(id);const w=1+m.parents(id).slots.reduce((s,p)=>s+(p?wt(p.id,guard):0),0);weight.set(id,w);return w};
 // a side for every person: 0 the husband's, 1 the wife's, 2 the seam (the couple's children, an ancestor of both)
 const two=m.homes.length===2;const side=new Map<string,number>();
 const put=(id:string,a:number,b:number,g:number,s=0)=>{if(gen.has(id)){if(side.get(id)!==s)side.set(id,2);return}gen.set(id,g);side.set(id,s);m.parents(id).slots.forEach(p=>{if(p&&gen.has(p.id)&&side.get(p.id)!==s)side.set(p.id,2)});at.set(id,(a+b)/2);const [f,mo]=m.parents(id).slots;const fa=f&&!gen.has(f.id)?f.id:'',ma=mo&&!gen.has(mo.id)?mo.id:'';
  if(fa&&ma){const share=Math.min(.8,Math.max(.2,wt(fa)/(wt(fa)+wt(ma))));const mid=a+(b-a)*share;put(fa,a,mid,g+1,s);put(ma,mid,b,g+1,s)}else if(fa||ma)put(fa||ma,a,b,g+1,s)};
 m.homes.forEach((h,i)=>put(h,i/m.homes.length,(i+1)/m.homes.length,0,i));
 // the ancestors of an ancestor of both belong to both as well: they stand on the seam
 const onSeam=[...side].filter(([,s])=>s===2).map(([id])=>id);
 for(let i=0;i<onSeam.length;i++)m.parents(onSeam[i]).slots.forEach(p=>{if(p&&gen.has(p.id)&&side.get(p.id)!==2){side.set(p.id,2);onSeam.push(p.id)}});
 for(const id of onSeam)at.set(id,.5);
 // 2. everyone else hangs next to the nearest placed relative
 const queue=[...gen.keys()];const from=new Map<string,string>();
 for(let i=0;i<queue.length;i++){const c=queue[i];const g=gen.get(c)!;
  const next:[string,number][]=[...ups(c).map(p=>[p,g+1] as [string,number]),...m.children(c).map(k=>[k,g-1] as [string,number]),...m.spouses(c).map(s=>[s,g] as [string,number])];
  for(const [n,ng] of next){if(!gen.has(n)&&!m.info[n].placeholder){gen.set(n,ng);at.set(n,at.get(c)!);queue.push(n);from.set(n,c);
   // a child of the couple stands on the seam; everyone else on the side of the relative they hang next to
   side.set(n,two&&m.homes.every(h=>ups(n).includes(h))?2:side.get(c)!)}}}
 const links:[string,string][]=[];const level:Hold[]=[];const factor:number[]=[];const seen=new Set<string>();
 for(const id of queue){const ps=m.parents(id);for(const s of [...ps.slots,...ps.extra]){if(!s||!gen.has(s.id)||seen.has(id+'|'+s.id))continue;seen.add(id+'|'+s.id);links.push([id,s.id]);
  // every link counts by its weight: a line copied link after link from one book fades with its length, a line of records
  // (0.98 a link) stays firm for some thirty generations; a link without a weight by its status
  const l=m.connectionLevel(s) as Hold;level.push(l);factor.push(linkFactor(s,l))}}
 // how firmly each person holds: the best way down to a home person, the weights of its links multiplied
 const adj=new Map<string,{to:string;f:number;link:number}[]>();const edge=(a:string,e:{to:string;f:number;link:number})=>(adj.get(a)||adj.set(a,[]).get(a)!).push(e);
 links.forEach(([c,p],i)=>{edge(c,{to:p,f:factor[i],link:i});edge(p,{to:c,f:factor[i],link:i})});
 for(const id of queue)for(const s of m.spouses(id))if(gen.has(s))edge(id,{to:s,f:1,link:-1});
 const best=new Map<string,number>(),down=new Map<string,{to:string;link:number;f:number}>();
 const work=m.homes.filter(h=>gen.has(h));work.forEach(h=>best.set(h,1));
 for(let i=0;i<work.length;i++){const x=work[i],v=best.get(x)!;for(const e of adj.get(x)||[]){const nv=v*e.f;if(nv>(best.get(e.to)??-1)+1e-9){best.set(e.to,nv);down.set(e.to,{to:x,link:e.link,f:e.f});work.push(e.to)}}}
 const hold=new Map<string,Hold>(queue.map(id=>[id,holdOf(best.get(id)??1)]));
 const seconds:[string,string][]=[];for(const id of queue){const r=m.secondWay(id);if(r&&gen.has(r.via))seconds.push([id,r.via])}
 // 3. years: a known birth year, otherwise the average of parents + 28, children − 28 and partners, settled over a few passes
 const years=new Map<string,number>();const estimated=new Set<string>();
 // the engine's guess (tree.first_child_age) places people nobody dated; only those without one are settled here
 const free:string[]=[];
 for(const id of queue){const i=m.info[id];const y=i.birth??i.guess?.exact;if(y)years.set(id,y);if(!i.birth)estimated.add(id);if(!y)free.push(id)}
 for(let pass=0;pass<40;pass++){let changed=false;
  for(const id of free){const c:number[]=[];m.parents(id).slots.forEach(s=>{const y=s&&years.get(s.id);if(y)c.push(y+STEP*(1+(s.gap||0)))});m.parents(id).extra.forEach(s=>{const y=years.get(s.id);if(y!==undefined)c.push(y+STEP)});m.children(id).forEach(k=>{const y=years.get(k);if(y!==undefined)c.push(y-STEP)});m.spouses(id).forEach(s=>{const y=years.get(s);if(y!==undefined)c.push(y)});
   if(!c.length)continue;const v=Math.round(c.reduce((a,b)=>a+b,0)/c.length);if(years.get(id)!==v){years.set(id,v);changed=true}}
  if(!changed)break}
 const home0=years.get(m.homes[0])??1970;
 for(const id of queue)if(!years.has(id))years.set(id,home0-gen.get(id)!*STEP);
 for(const [id,y] of years)years.set(id,Math.min(2030,Math.max(1600,y)));
 // 4. a band for every line: its ancestors, their brothers, sisters and descendants, and whoever married into them.
 // The home person's own brothers and sisters stand between the father's and the mother's line; the couple's children
 // and an ancestor of both on the seam. A crowded line widens its own band and never lies over its neighbour.
 const blood=(id:string)=>{const f=new Set<number>();for(const a of m.ancestorsOf(id).keys()){const b=m.branch.get(a);if(b!==undefined)f.add(b)}return f};
 const homeOfLine=(i:number)=>m.homes.indexOf(m.lines[i].home);
 const lane=new Map<string,string>();
 for(const id of queue){let l:string;const tn=m.tone(id);
  if(two&&side.get(id)===2)l='S';else if(m.homes.includes(id))l='H'+m.homes.indexOf(id);else if(tn)l='L'+tn.line;
  else{const f=blood(id),hs=new Set([...f].map(homeOfLine));l=hs.size>1?'S':f.size>1?'H'+[...hs][0]:lane.get(from.get(id)!)??'S'}
  lane.set(id,l)}
 const order:string[]=[];m.homes.forEach((h,hi)=>{const ls=m.lines.flatMap((l,i)=>l.home===h?['L'+i]:[]);order.push(...(ls.length===2?[ls[0],'H'+hi,ls[1]]:hi===0?[...ls,'H'+hi]:['H'+hi,...ls]));if(hi===0)order.push('S')});
 // inside a band: generation rows, every child under the midpoint of its parents, neighbours pushed apart
 const rowsMap=new Map<number,string[]>();for(const [id,g] of gen)(rowsMap.get(g)||rowsMap.set(g,[]).get(g)!).push(id);
 const keys=[...rowsMap.keys()].sort((a,b)=>b-a);const widest=Math.max(...keys.map(k=>rowsMap.get(k)!.length));
 for(const k of keys)for(const id of rowsMap.get(k)!){const ps=m.parents(id).slots.filter(Boolean).map(s=>s!.id).filter(p=>gen.get(p)===k+1);if(ps.length)at.set(id,ps.reduce((s,p)=>s+at.get(p)!,0)/ps.length)}
 const W0=Math.max(900,widest*SP*1.15);
 const ys=[...years.values()];const y0=Math.floor((Math.min(...ys)-8)/25)*25,y1=Math.ceil((Math.max(...ys)+6)/25)*25;
 const spread=(xs:number[])=>{for(let pass=0;pass<60;pass++){let moved=false;for(let i=1;i<xs.length;i++){const d=xs[i]-xs[i-1];if(d<SP){const push=(SP-d)/2;xs[i-1]-=push;xs[i]+=push;moved=true}}if(!moved)break}return xs};
 const pos=new Map<string,{x:number;y:number}>();const lanes:{key:string;x0:number;x1:number}[]=[];let cursor=0,last='';
 for(const key of order){const ids=queue.filter(id=>lane.get(id)===key);if(!ids.length)continue;
  const dots=new Map<string,{x:number;y:number}>();
  // the band is as wide as its own widest row needs, not as the whole family's: the crown keeps its shape, scaled down
  const ats=ids.map(id=>at.get(id)!),a0=Math.min(...ats),span=Math.max(...ats)-a0;
  const most=Math.max(...keys.map(k=>ids.filter(id=>gen.get(id)===k).length));
  const scale=span>0?Math.min(W0,Math.max(SP*2,most*SP*1.15)/span):W0;
  for(const k of keys){const row=ids.filter(id=>gen.get(id)===k).sort((a,b)=>at.get(a)!-at.get(b)!||a.localeCompare(b));if(!row.length)continue;spread(row.map(id=>(at.get(id)!-a0)*scale)).forEach((x,i)=>dots.set(row[i],{x,y:(years.get(row[i])!-y0)*PPY}))}
  // dots of neighbouring generations can land on the same year: nudge them apart sideways, inside the band
  const all=[...dots.values()];
  for(let pass=0;pass<30;pass++){all.sort((a,b)=>a.x-b.x);let moved=false;
   for(let i=0;i<all.length;i++)for(let j=i+1;j<all.length&&all[j].x-all[i].x<SP*.9;j++){const A=all[i],B=all[j];if(Math.abs(A.y-B.y)<16){const push=(SP*.9-(B.x-A.x))/2+.5;A.x-=push;B.x+=push;moved=true}}
   if(!moved)break}
  const lo=Math.min(...all.map(p=>p.x)),hi=Math.max(...all.map(p=>p.x));
  if(lanes.length)cursor+=key==='S'||last==='S'?GAP*1.4:GAP;
  for(const [id,p] of dots)pos.set(id,{x:p.x-lo+cursor,y:p.y});
  lanes.push({key,x0:cursor,x1:cursor+hi-lo});cursor+=hi-lo;last=key}
 // a wide screen: the bands spread out to the width of the page, the years keep their scale
 const h=(y1-y0)*PPY;const stretch=opt.aspect?Math.min(3,Math.max(1,(opt.aspect*(h+60)-230)/Math.max(cursor,1))):1;
 if(stretch>1){for(const p of pos.values())p.x*=stretch;for(const l of lanes){l.x0*=stretch;l.x1*=stretch}}
 const axis:{y:number;label:string;major:boolean}[]=[];for(let y=y0;y<=y1;y+=25)axis.push({y:(y-y0)*PPY,label:String(y),major:y%50===0});
 return {pos,links,level,hold,down,seconds,lanes,w:cursor*stretch,h,rows:keys.length,axis,years,estimated,y0,y1};
}
const PAD=30,PADL=78,PAPER='#f8f5ec';
/** A hue mixed with the paper: `t` of the hue. */
const pale=(hex:string,t:number)=>{const h=(s:string,i:number)=>parseInt(s.slice(i,i+2),16);const p=[1,3,5].map(i=>h(PAPER,i)),c=[1,3,5].map(i=>h(hex,i));return '#'+c.map((v,i)=>Math.round(v*t+p[i]*(1-t)).toString(16).padStart(2,'0')).join('')};
/** The line of a link by its hold: whole, dashed, dotted. */
export const holdDash=(l:Hold,detail=true,s=1)=>l===1?undefined:l===2?(detail?`${5*s} ${3.5*s}`:'16 11'):(detail?`.1 ${4.4*s}`:'.1 14');
/** A dot by how firmly the person holds to the family: filled, pale inside a rim, an empty ring. */
export function HoldDot({cx,cy,r,color,hold,opacity}:{cx:number;cy:number;r:number;color:string;hold:Hold;opacity?:number}){
 if(hold===1)return <circle cx={cx} cy={cy} r={r} fill={color} opacity={opacity} pointerEvents="none"/>;
 const sw=r*(hold===2?.4:.3);return <circle cx={cx} cy={cy} r={r-sw/2} fill={hold===2?pale(color,.42):PAPER} stroke={color} strokeWidth={sw} opacity={opacity} pointerEvents="none"/>;
}
function Dots({ov,model,visible,center,selected,onPick,onHover,detail,k,names}:{ov:Overview;model:Model;visible:Set<string>;center:string;selected?:string;onPick?:(id:string)=>void;onHover?:(id:string)=>void;detail:boolean;k:number;names:Set<string>}){
 const col=(id:string)=>model.tone(id)?.color||NEUTRAL;
 // a link carries a line's colour when it runs between two people of that line: full for the ancestor backbone, light for kin
 const homes=new Set(model.homes);
 const linkTone=(child:string,parent:string)=>{const p=model.tone(parent);if(!p)return null;if(!p.kin&&(homes.has(child)||model.tone(child)?.kin===false))return {color:p.color,kin:false};const c=model.tone(child);return c&&c.line===p.line?{color:c.color,kin:true}:null};
 const tones=ov.links.map(([a,b])=>linkTone(a,b));
 const dim=(id:string)=>{const tn=model.tone(id);return tn?(tn.kin?.8:.85):.55};
 // a whole large family seen from afar: dots and lines keep a readable size on screen instead of shrinking with it
 const s=detail?Math.max(1,.7/k):1;const r=detail?7*Math.max(1,.45/k):20;const fs=11/Math.max(k,.3);
 const label=(id:string)=>{const i=model.info[id];if(i.knot)return '';if(i.providedName)return i.providedName;const sur=i.short.split(' ').filter(x=>/\p{L}/u.test(x)).slice(-1)[0]||i.short;return k>=3?i.short:k>=1.7?sur.slice(0,10):names.has(id)?i.short:''};
 const grid=detail?ov.axis.filter(a=>a.major||k>=1.8):ov.axis.filter(a=>Number(a.label)%100===0);
 // the part of the tree on screen now: one soft amber frame around it, so size and colour of a dot keep their own meaning
 const seen=[...visible].map(id=>ov.pos.get(id)).filter(Boolean) as {x:number;y:number}[];const fp=detail?15:46;
 const frame=seen.length?{x:Math.min(...seen.map(p=>p.x))-fp,y:Math.min(...seen.map(p=>p.y))-fp,w:Math.max(...seen.map(p=>p.x))-Math.min(...seen.map(p=>p.x))+fp*2,h:Math.max(...seen.map(p=>p.y))-Math.min(...seen.map(p=>p.y))+fp*2}:null;
 // the chosen person's way down to the family, and the link on it that holds least
 const path=new Set<number>();let weakest=-1;
 if(selected){let x=selected,low=1;const guard=new Set<string>();while(ov.down.has(x)&&!guard.has(x)){guard.add(x);const d=ov.down.get(x)!;if(d.link>=0){path.add(d.link);if(d.f<low-1e-9){low=d.f;weakest=d.link}}x=d.to}}
 const line=(i:number,props:Record<string,unknown>)=>{const [a,b]=ov.links[i];const A=ov.pos.get(a)!,B=ov.pos.get(b)!;const l=ov.level[i];return <line key={i} x1={A.x} y1={A.y} x2={B.x} y2={B.y} strokeDasharray={holdDash(l,detail,s)} strokeLinecap={l===3?'round':undefined} {...props}/>};
 return <>
  <g className="ov-grid">{grid.map(a=><line key={'l'+a.label} x1={-PADL+(detail?6:0)} x2={ov.w+PAD} y1={a.y} y2={a.y} stroke={a.major?'#c9cfbf':'#dde1d4'} strokeWidth={detail?1/Math.max(k,.5):4} strokeDasharray={a.major?undefined:'4 6'}/>)}</g>
  {detail?grid.map(a=><text key={'t'+a.label} x={-PADL+8} y={a.y+fs*.35} fontSize={fs*1.15} fill="#8a9488" fontWeight={a.major?700:500}>{a.label}</text>)
   :grid.map(a=><text key={'t'+a.label} x={-PADL+4} y={a.y-10} fontSize={Math.min(90,ov.h/6)} fill="#8a9488" fontWeight={700}>{a.label}</text>)}
  {frame&&<rect x={frame.x} y={frame.y} width={frame.w} height={frame.h} rx={detail?14:44} fill="#f0c36b" fillOpacity={.08} stroke="#e8a63b" strokeOpacity={.7} strokeWidth={detail?1.4:6}/>}
  <g stroke="#9fb39a" strokeWidth={detail?1.4*s:3} opacity={detail?.45:.5}>{ov.links.map((_,i)=>tones[i]?null:line(i,{}))}</g>
  <g>{ov.links.map((_,i)=>{const tn=tones[i];return tn?line(i,{stroke:tn.color,strokeWidth:tn.kin?(detail?1.3*s:3):(detail?1.9*s:5),opacity:tn.kin?(detail?.6:.6):(detail?.75:.75)}):null})}</g>
  <g strokeWidth={detail?1.1*s:2.5} opacity={detail?.5:.4} strokeLinecap="round">{ov.seconds.map(([a,b])=>{const A=ov.pos.get(a),B=ov.pos.get(b);return A&&B?<line key={'2:'+a} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={col(b)} strokeDasharray={holdDash(3,detail,s)}/>:null})}</g>
  {weakest>=0&&line(weakest,{stroke:'#233a31',strokeWidth:detail?11*s:30,opacity:.15,strokeDasharray:undefined,strokeLinecap:'round'})}
  <g stroke="#233a31" strokeWidth={detail?2.2*s:6} opacity=".8">{[...path].map(i=>line(i,{}))}</g>
  {[...ov.pos].map(([id,p])=>{const here=id===center;const sel=id===selected;const rr=here?r*1.7:sel?r*1.35:r;
   return <g key={id}>{here?<circle cx={p.x} cy={p.y} r={rr} fill="#d98a1f" stroke="#fff" strokeWidth={detail?2:3} pointerEvents="none"/>:<HoldDot cx={p.x} cy={p.y} r={rr} color={col(id)} hold={ov.hold.get(id)??1} opacity={sel||visible.has(id)?1:dim(id)}/>}
    {sel&&<circle cx={p.x} cy={p.y} r={rr+(detail?2.6:6)} fill="none" stroke="#233a31" strokeWidth={detail?1.8:4} pointerEvents="none"/>}
    {onPick&&isPerson(model.info[id])&&<title>{model.info[id].name+(model.info[id].life?' · '+model.info[id].life:'')}</title>}</g>})}
  {onPick&&[...ov.pos].filter(([id])=>isPerson(model.info[id])).map(([id,p])=><circle key={'hit'+id} className="ovdot" cx={p.x} cy={p.y} r={Math.max(22/k,r*1.8)} fill="transparent" role="button" tabIndex={0} aria-label={model.info[id].name} onPointerEnter={e=>{if(e.pointerType==='mouse')onHover?.(id)}} onFocus={()=>onHover?.(id)} onClick={()=>onPick(id)} onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();onPick(id)}}}/>)}
  {detail&&[...ov.pos].map(([id,p])=>{const t=label(id);const text=id===selected?[model.info[id].short,model.info[id].life].filter(Boolean).join(' · '):t;return text?<text key={'t'+id} x={p.x} y={p.y+r*2.3+fs*.6} fontSize={fs} textAnchor="middle" fill="#2b4338" fontWeight={id===center||id===selected?700:500} stroke="#f6f3ea" strokeWidth={fs*.35} paintOrder="stroke">{text}</text>:null})}
 </>
}
/** Three samples for the caption: the link and the dot of each hold. */
function HoldLegend({labels}:{labels:Row}){
 return <span className="ov-legend">{([1,2,3] as Hold[]).map(l=><span key={l}><svg width="34" height="14" aria-hidden="true"><line x1="2" y1="7" x2="20" y2="7" stroke="#4a3f94" strokeWidth="1.9" strokeDasharray={holdDash(l)} strokeLinecap={l===3?'round':undefined}/><HoldDot cx={27} cy={7} r={5.5} color="#4a3f94" hold={l}/></svg>{labels.overviewHold?.[l-1]}</span>)}</span>
}
export function MiniMap({ov,model,visible,center,onOpen,label,caption}:{ov:Overview;model:Model;visible:Set<string>;center:string;onOpen:()=>void;label:string;caption?:string}){
 return <button className="minimap" onClick={onOpen} aria-label={label} title={label}><svg viewBox={`${-PADL} ${-PAD} ${ov.w+PADL+PAD} ${ov.h+PAD*2}`} preserveAspectRatio="xMidYMid meet" aria-hidden="true"><Dots ov={ov} model={model} visible={visible} center={center} detail={false} k={1} names={new Set()}/></svg>{caption&&<small>{caption}</small>}</button>
}
export function OverviewDialog({ov,model,visible,center,go,onClose,labels,language,me}:{ov:Overview;model:Model;visible:Set<string>;center:string;go:(id:string)=>void;onClose:()=>void;labels:Row;language:string;me?:string}){
 const box=useRef<HTMLDivElement>(null);const cw=ov.w+PAD+PADL+80,ch=ov.h+PAD*2;const content=useRef({w:cw,h:ch});
 const {t,setT,moving,zoomBy}=useZoomPan(box,{min:.3,max:9,content,margin:120});
 const [selected,setSelected]=useState('');
 const fitK=()=>{const el=box.current;return el?Math.min(el.clientWidth/cw,el.clientHeight/ch):1};
 const fit=useCallback(()=>{const el=box.current;if(!el)return;const k=Math.min(el.clientWidth/cw,el.clientHeight/ch);setT({k,x:(el.clientWidth-cw*k)/2,y:(el.clientHeight-ch*k)/2})},[cw,ch,setT]);
 const focusAt=useCallback((id:string,k:number)=>{const el=box.current,p=ov.pos.get(id);if(!el||!p)return;setT({k,x:el.clientWidth/2-(p.x+PADL)*k,y:el.clientHeight/2-(p.y+PAD)*k})},[ov,setT]);
 // a wide screen always opens on the whole family, a phone on the current person when the whole would be too small
 useLayoutEffect(()=>{if(fitK()<((box.current?.clientWidth||0)>=900?.2:.55))focusAt(center,1.1);else fit()},[]);// eslint-disable-line react-hooks/exhaustive-deps
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose()};addEventListener('keydown',key);return()=>removeEventListener('keydown',key)},[onClose]);
 const heads=new Set<string>([center,...model.lines.map(l=>l.id),...model.homes]);
 const focus=(id:string)=>{setSelected(id);focusAt(id,Math.max(t.k,1.4))};
 const pick=(id:string)=>{go(id);onClose()};
 const sel=selected?model.info[selected]:null;const kin=!selected?[]:me&&model.info[me]?[model.relation(me,selected)].filter(Boolean).map(r=>relationPhrase(r!,labels,language)):model.kinship(selected).map(k=>kinPhrase(k,labels,language));
 const role=(l:{id:string;role:string;home:string})=>lineTitle(l,model,labels);
 const hold=selected&&!model.homes.includes(selected)?ov.hold.get(selected):undefined;
 const when=sel&&!sel.birth&&!sel.death?'≈'+(sel.guess?.year??ov.years.get(selected)):'';
 return <div className="overview" role="dialog" aria-modal="true" aria-label={labels.overviewTitle}>
  <div className="ov-head"><div><h2>{labels.overviewTitle}</h2><p>{labels.overviewHint}</p></div><button className="ov-close" onClick={onClose} aria-label={labels.close}>×</button></div>
  <div className="ov-lines">{model.lines.filter(l=>isPerson(model.info[l.id])).map(l=><button key={l.id} onClick={()=>focus(l.id)}><i style={{background:l.color}}/><span><b>{model.info[l.id].short}</b><small>{role(l)}</small></span></button>)}<HoldLegend labels={labels}/></div>
  <div ref={box} className={'ov-stage'+(moving?' moving':'')} onClick={e=>{if((e.target as Element).tagName==='svg'||(e.target as Element).classList.contains('ov-stage'))setSelected('')}}>
   <svg width={cw} height={ch} className="ov-svg" style={{transform:`translate(${t.x}px,${t.y}px) scale(${t.k})`}}><g transform={`translate(${PADL},${PAD})`}><Dots ov={ov} model={model} visible={visible} center={center} selected={selected} detail onPick={pick} onHover={setSelected} k={t.k} names={heads}/></g></svg>
   <div className="controls"><button aria-label={labels.zoomIn} onClick={()=>zoomBy(1.4)}>+</button><button aria-label={labels.zoomOut} onClick={()=>zoomBy(1/1.4)}>−</button><button aria-label={labels.recenter} title={labels.recenter} onClick={()=>focusAt(center,1.4)}>⌖</button><button aria-label={labels.showWhole} title={labels.showWhole} onClick={fit}>⤢</button></div>
   {sel&&<div className="ov-card"><div><strong>{sel.short}</strong><small>{[lifeLabel(sel,labels,language)||sel.note||when,placeLabel(sel,labels)].filter(Boolean).join(' · ')}</small>{hold&&<small className="ov-hold"><svg width="14" height="14" aria-hidden="true"><HoldDot cx={7} cy={7} r={5.5} color={model.tone(selected)?.color||NEUTRAL} hold={hold}/></svg>{labels.overviewHoldLead}: {labels.overviewHold?.[hold-1]}</small>}{selected&&<SecondWay model={model} id={selected} labels={labels} go={focus}/>}{selected&&me&&model.relation(me,selected)?<KinshipExplanation relation={model.relation(me,selected)!} model={model} labels={labels} language={language}/>:kin.length>0&&<small className="rel">{kin.join(' · ')}</small>}</div></div>}
  </div>
  <p className="ov-foot">{labels.overviewFoot}</p>
 </div>
}
