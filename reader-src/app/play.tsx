'use client';
import {readerStorage,profile} from './reader-profile';
/** Play layer of the feeds (2.11.2026, livelier 3.11.2026, author: «можно веселей и завлекательней»; RULES KIDS-7).
 *  - SpotFrame: «Рассмотри» (marks with a card) and «Найди» (tasks one by one, a burst, a word of praise and a chime on every find,
 *    stars of progress, confetti at the end) over a picture; the button «Зайди … · 360°» opens the picture's panorama.
 *  - GameCard: «Сыграй за …» — choices with icons and things for the hero's bundle, a lot drawn from a drum with a slow reveal and a stamp,
 *    and at the end a closed chest: the real document of the chapter comes out of it as a treasure.
 *  - PanoViewer: our own WebGL viewer of an equirectangular 2:1 panorama (no packages): drag, pinch or wheel, keys, optional tilt.
 *    Spots are the same `Spot` boxes, in percent of the whole panorama; the viewer turns them into angles.
 *  - The chest (`localStorage` «reader-chest»): every found thing and every finished game; ChestChip shows «🧰 12 / 40» in the feed.
 *  - Sound: WebAudio, synthesised, no files; «без звука» is remembered («reader-play-mute»). */
import {createContext,useCallback,useContext,useEffect,useLayoutEffect,useRef,useState,type CSSProperties,type ReactNode,type MouseEvent as ReactMouseEvent} from 'react';
import {createPortal} from 'react-dom';
import {plural,type Language} from './i18n';
import type {Row} from './tree/model';
import type {Feed,Game,GameStep,Picture,Spot} from './feed';

const tr=(x:Row|string|undefined,language:string):string=>typeof x==='string'?x:x?.[language]||x?.en||x?.ru||'';
/** A 360° room behind a picture (`play/*.json` → `panos`, see `scripts/feed-play.py`). */
export type Pano={asset:string;title?:Row;enter?:Row;yaw?:number;pitch?:number;spots?:Spot[]};
export type Offer='look'|'find'|'both';
/** The feed a play element belongs to: the chest counts things per feed. */
export const PlayFeed=createContext('');

/* ---------- sound ---------- */
const MUTE_KEY='reader-play-mute';
let audio:AudioContext|null=null;
const isMuted=()=>{try{return readerStorage.getItem(MUTE_KEY)==='1'}catch{return false}};
type Sfx='hit'|'miss'|'tick'|'done'|'treasure'|'shake'|'low'|'high'|'pick';
export function sfx(kind:Sfx){
 if(typeof window==='undefined'||isMuted())return;
 try{
  const AC=window.AudioContext||(window as unknown as {webkitAudioContext?:typeof AudioContext}).webkitAudioContext;if(!AC)return;
  audio??=new AC();const ac=audio;if(ac.state==='suspended')void ac.resume();
  const t=ac.currentTime;
  const note=(f:number,at:number,dur:number,type:OscillatorType='triangle',vol=.16,to?:number)=>{const o=ac.createOscillator(),g=ac.createGain();o.type=type;
   o.frequency.setValueAtTime(f,t+at);if(to)o.frequency.exponentialRampToValueAtTime(to,t+at+dur);
   g.gain.setValueAtTime(0,t+at);g.gain.linearRampToValueAtTime(vol,t+at+.012);g.gain.exponentialRampToValueAtTime(.0001,t+at+dur);
   o.connect(g).connect(ac.destination);o.start(t+at);o.stop(t+at+dur+.05)};
  if(kind==='hit'){note(784,0,.16);note(1175,.08,.3)}
  else if(kind==='miss')note(260,0,.18,'sine',.09,200);
  else if(kind==='tick')note(1500,0,.035,'square',.03);
  else if(kind==='pick')note(660,0,.09,'triangle',.08);
  else if(kind==='shake'){for(let k=0;k<7;k++)note(180+k*13,k*.09,.07,'sawtooth',.025)}
  else if(kind==='done'){[523,659,784,1047].forEach((f,k)=>note(f,k*.11,.35));note(1568,.48,.5,'sine',.07)}
  else if(kind==='treasure'){[659,784,988,1319,1568].forEach((f,k)=>note(f,k*.09,.5,'triangle',.13));[2093,2637,3136].forEach((f,k)=>note(f,.5+k*.07,.4,'sine',.04))}
  else if(kind==='high'){[523,659,784,1047].forEach((f,k)=>note(f,k*.09,.4,'triangle',.15))}
  else if(kind==='low'){note(392,0,.35,'sine',.14);note(311,.25,.6,'sine',.14)}
 }catch{}
}
export function useMute(){
 const [m,setM]=useState(false);
 useEffect(()=>{const f=()=>setM(isMuted());f();addEventListener(MUTE_KEY,f);return()=>removeEventListener(MUTE_KEY,f)},[]);
 const toggle=()=>{const v=!isMuted();try{readerStorage.setItem(MUTE_KEY,v?'1':'0')}catch{}dispatchEvent(new Event(MUTE_KEY));if(!v)sfx('pick')};
 return [m,toggle] as const;
}
function MuteBtn({labels,className='play-mute'}:{labels:Row;className?:string}){
 const [m,toggle]=useMute();
 return <button className={className} onClick={e=>{e.stopPropagation();toggle()}} aria-pressed={m} aria-label={m?labels.playMute:labels.playSound} title={m?labels.playMute:labels.playSound}>{m?'🔇':'🔊'}</button>;
}

/* ---------- the chest ---------- */
const CHEST_KEY='reader-chest';
type ChestItem={label:Row|string;feed:string;kind:'find'|'game';at:number};
function chestRead():Record<string,ChestItem>{try{return JSON.parse(readerStorage.getItem(CHEST_KEY)||'{}')||{}}catch{return {}}}
export function chestAdd(key:string,item:Omit<ChestItem,'at'>){
 try{const c=chestRead();if(c[key])return false;c[key]={...item,at:Date.now()};readerStorage.setItem(CHEST_KEY,JSON.stringify(c));dispatchEvent(new Event(CHEST_KEY));return true}catch{return false}
}
export function useChest(){
 const [c,setC]=useState<Record<string,ChestItem>>({});
 useEffect(()=>{const f=()=>setC(chestRead());f();addEventListener(CHEST_KEY,f);addEventListener('storage',f);return()=>{removeEventListener(CHEST_KEY,f);removeEventListener('storage',f)}},[]);
 return c;
}
/** Every thing of a feed that can go into the chest: the «Найди» tasks of its pictures and panoramas, and its games. */
function feedPrizes(feed:Feed){
 const keys=new Set<string>();
 for(const c of feed.chapters){
  const pics=[c.picture,...(c.figures||[]).flatMap(f=>[f,f.ours]),...(c.extras||[]).flatMap(x=>[x.picture,x.picture?.ours])].filter(Boolean) as Picture[];
  for(const p of pics){(p.spots||[]).forEach((s,k)=>s.find&&keys.add(`find:${p.asset}#${k}`));const pn=p.pano;if(pn)(pn.spots||[]).forEach((s,k)=>s.find&&keys.add(`find:${pn.asset}#${k}`))}
  if(c.game)keys.add(`game:${feed.id}/${c.id||c.year}`);
 }
 return keys;
}
/** «🧰 12 / 40» in the head of the feed; a tap shows what is in the chest. Hidden in a feed without play. */
export function ChestChip({feed,labels,language}:{feed:Feed;labels:Row;language:Language}){
 const chest=useChest();const [open,setOpen]=useState(false);
 const all=feedPrizes(feed);if(!all.size)return null;
 const got=[...all].filter(k=>chest[k]);
 const forms=labels.playChestForms as [string,string,string]|undefined;
 return <div className="chest">
  <button className={'chest-chip'+(got.length?' some':'')+(got.length===all.size?' full':'')} onClick={()=>setOpen(v=>!v)} aria-expanded={open} title={labels.playChest}>🧰 {got.length} / {all.size}</button>
  {open&&<div className="chest-pop" role="dialog" aria-label={labels.playChest}>
   <b>🧰 {labels.playChest}: {got.length} {forms?plural(got.length,forms,language):''} {labels.playChestOf} {all.size}</b>
   {got.length?<ul>{got.sort((a,b)=>chest[a].at-chest[b].at).map(k=><li key={k} className={chest[k].kind}>{chest[k].kind==='game'?'📜 ':'✦ '}{tr(chest[k].label,language)}</li>)}</ul>:<p>{labels.playChestEmpty}</p>}
   <div className="chest-dots" aria-hidden="true">{[...all].map(k=><i key={k} className={chest[k]?'on':''}/>)}</div>
   <MuteBtn labels={labels} className="play-mute inline"/>
  </div>}
 </div>;
}

/* ---------- small joys ---------- */
const praise=(labels:Row)=>{const xs=(labels.playPraise as string[]|undefined)||[String(labels.playFound||'!')];return xs[Math.floor(Math.random()*xs.length)]};
function Burst({x,y,word,n}:{x:number|string;y:number|string;word?:string;n:number}){
 return <span key={n} className="play-burst" style={{left:x,top:y}} aria-hidden="true">
  {Array.from({length:10},(_,k)=><i key={k} style={{'--a':`${k*36}deg`,'--d':`${38+(k%3)*14}px`} as CSSProperties}>{k%2?'✦':'★'}</i>)}
  {word&&<b>{word}</b>}
 </span>;
}
function Confetti(){
 return <span className="play-confetti" aria-hidden="true">{Array.from({length:26},(_,k)=><i key={k} style={{'--x':`${(k*37)%100}%`,'--r':`${(k*53)%360}deg`,'--t':`${.9+(k%5)*.18}s`,'--c':['#f1d98a','#8fd39d','#f08a7a','#9ec8f0','#fff'][k%5]} as CSSProperties}/>)}</span>;
}
function Stars({n,m}:{n:number;m:number}){
 return <span className="play-stars" aria-label={`${n} / ${m}`}>{Array.from({length:m},(_,k)=><i key={k} className={k<n?'on':''}>★</i>)}</span>;
}

/* ---------- SpotFrame ---------- */
/** Until the reader taps a small button in the corner, the picture is as before. Boxes are in percent of the drawn image: the layer follows
 *  it even when the frame crops it (object-fit cover). A miss gives a soft hint, the second miss makes the box blink. */
export function SpotFrame({spots,kids,offer,labels,language,className,asset='',pano,children}:{spots?:Spot[];kids:boolean;offer:Offer;labels:Row;language:Language;className:string;asset?:string;pano?:Pano;children:ReactNode}){
 const feed=useContext(PlayFeed);
 const frame=useRef<HTMLDivElement>(null);const layer=useRef<HTMLDivElement>(null);
 const [mode,setMode]=useState<'off'|'look'|'find'>('off');const [sel,setSel]=useState(-1);
 const [box,setBox]=useState<CSSProperties|null>(null);const [room,setRoom]=useState(false);
 const tasks=(spots||[]).map((s,k)=>s.find?k:-1).filter(k=>k>=0);
 const [t,setT]=useState(0);const [hit,setHit]=useState(false);const [miss,setMiss]=useState(0);const [tap,setTap]=useState<{x:number;y:number;n:number}|null>(null);
 const [joy,setJoy]=useState<{x:string;y:string;w:string;n:number}|null>(null);
 const on=mode!=='off';
 useEffect(()=>{if(!on)return;const el=frame.current;const img=el?.querySelector('img');if(!el||!img)return;
  const measure=()=>{const fr=el.getBoundingClientRect(),r=img.getBoundingClientRect();let x=r.left-fr.left,y=r.top-fr.top,w=r.width,h=r.height;
   const nw=img.naturalWidth,nh=img.naturalHeight,fit=getComputedStyle(img).objectFit;
   if(nw&&nh&&(fit==='cover'||fit==='contain')){const sc=(fit==='cover'?Math.max:Math.min)(w/nw,h/nh);x+=(w-nw*sc)/2;y+=(h-nh*sc)/2;w=nw*sc;h=nh*sc}
   setBox({left:x,top:y,width:w,height:h})};
  measure();img.addEventListener('load',measure);const ro=new ResizeObserver(measure);ro.observe(el);
  return()=>{img.removeEventListener('load',measure);ro.disconnect()}},[on]);
 if(!spots?.length&&!pano)return <div className={className}>{children}</div>;
 const sp=spots||[];
 const canFind=tasks.length>0&&offer!=='look',canLook=sp.length>0&&(offer!=='find'||!canFind);
 const txt=(s:Spot)=>tr(kids&&s.kids?s.kids:s.text,language);
 const close=()=>{setMode('off');setSel(-1);setJoy(null)};
 const startFind=()=>{setMode('find');setSel(-1);setT(0);setHit(false);setMiss(0);setTap(null);setJoy(null);sfx('pick')};
 const done=mode==='find'&&t>=tasks.length;const cur=mode==='find'&&!done?sp[tasks[t]]:null;
 const pct=(e:ReactMouseEvent)=>{const r=layer.current!.getBoundingClientRect();return {x:(e.clientX-r.left)/r.width*100,y:(e.clientY-r.top)/r.height*100}};
 const onLayer=(e:ReactMouseEvent)=>{e.stopPropagation();
  if(mode==='look'){setSel(-1);return}
  if(!cur||hit)return;const p=pct(e);const pad=2.5;
  if(p.x>=cur.x-pad&&p.x<=cur.x+cur.w+pad&&p.y>=cur.y-pad&&p.y<=cur.y+cur.h+pad){
   setHit(true);setTap(null);setJoy({x:cur.x+cur.w/2+'%',y:cur.y+cur.h/2+'%',w:praise(labels),n:Date.now()});
   chestAdd(`find:${asset}#${tasks[t]}`,{label:cur.label,feed,kind:'find'});
   if(t+1>=tasks.length)window.setTimeout(()=>sfx('done'),250);else sfx('hit');
  }
  else{setMiss(m=>m+1);setTap(q=>({...p,n:(q?.n||0)+1}));sfx('miss')}};
 const nextTask=()=>{setT(x=>x+1);setHit(false);setMiss(0);setTap(null);setJoy(null);sfx('pick')};
 const found=t+(hit?1:0);
 const s=sel>=0?sp[sel]:null;const low=s?s.y+s.h/2>50:false;
 const rect=(x:Spot,cls:string)=><i className={'spot-box '+cls} style={{left:x.x+'%',top:x.y+'%',width:x.w+'%',height:x.h+'%'}}/>;
 return <>
  {mode==='find'&&<div className={'spot-task'+(hit?' hit':'')+(done?' done':'')} role="status" aria-live="polite">
   <button className="spot-task-x" onClick={close} aria-label={labels.close}>×</button>
   {done?<><Confetti/><b>🎉 {labels.playAll}</b><Stars n={tasks.length} m={tasks.length}/><span className="spot-chest-plus">🧰 +{tasks.length} {labels.playToChest}</span><button className="spot-task-go" onClick={()=>{setMode('look');setSel(-1)}}>🔍 {labels.playLookAll}</button></>
   :hit&&cur?<><b>✨ {tr(cur.label,language)}!</b><p>{txt(cur)}</p><Stars n={found} m={tasks.length}/><button className="spot-task-go" onClick={nextTask}>{t+1>=tasks.length?'🎉':labels.next+' ›'}</button></>
   :cur&&<><b>{tr(cur.find,language)}</b>{miss>0&&<p>{miss>1?labels.playHint:labels.playMiss}</p>}<Stars n={found} m={tasks.length}/></>}
   <MuteBtn labels={labels}/>
  </div>}
  <div ref={frame} className={className+' spot-frame'}>{children}
   {on&&box&&<div ref={layer} className={'spot-layer '+mode} style={box} onClick={onLayer}>
    {mode==='look'&&sp.map((x,k)=><button key={k} className={'spot-mark'+(k===sel?' on':'')} style={{left:x.x+x.w/2+'%',top:x.y+x.h/2+'%'}} aria-label={tr(x.label,language)} aria-expanded={k===sel}
     onClick={e=>{e.stopPropagation();setSel(v=>v===k?-1:k);sfx('pick')}}/>)}
    {s&&rect(s,'sel')}
    {cur&&hit&&rect(cur,'found')}
    {cur&&!hit&&miss>1&&rect(cur,'blink')}
    {tap&&mode==='find'&&!hit&&<i key={tap.n} className="spot-tap" style={{left:tap.x+'%',top:tap.y+'%'}}/>}
    {joy&&<Burst x={joy.x} y={joy.y} word={joy.w} n={joy.n}/>}
   </div>}
   {s&&<div className={'spot-card'+(low?' up':'')} onClick={e=>{e.stopPropagation();setSel(-1)}}><b>{tr(s.label,language)}</b><p>{txt(s)}</p></div>}
   {!on&&<div className="spot-btns">
    {pano&&<button className="spot-btn pano" onClick={e=>{e.stopPropagation();setRoom(true);sfx('pick')}}>🏠 {tr(pano.enter,language)||labels.panoEnter} · 360°</button>}
    {canLook&&<button className="spot-btn" onClick={e=>{e.stopPropagation();setMode('look');sfx('pick')}}>🔍 {labels.playLook}</button>}
    {canFind&&<button className="spot-btn find" onClick={e=>{e.stopPropagation();startFind()}}>◎ {labels.playFind}</button>}
   </div>}
   {mode==='look'&&<div className="spot-btns left"><button className="spot-btn on" onClick={e=>{e.stopPropagation();close()}} aria-label={labels.close}>×</button></div>}
  </div>
  {room&&pano&&<PanoViewer pano={pano} kids={kids} labels={labels} language={language} onClose={()=>setRoom(false)}/>}
 </>;
}

/* ---------- GameCard ---------- */
/** «Сыграй за …»: steps one by one. A choice shows its outcome (and may put a thing into the hero's bundle); a lot is drawn from a drum:
 *  it shakes, the number slows down digit by digit, then a stamp. At the end a closed chest: the chapter's real document is the treasure. */
export function GameCard({game,kids,labels,language,doc,id}:{game:Game;kids:boolean;labels:Row;language:Language;doc:(asset:string)=>ReactNode;id:string}){
 const feed=useContext(PlayFeed);
 const [stage,setStage]=useState(-1);const [pick,setPick]=useState<number|null>(null);const [roll,setRoll]=useState<number|null>(null);
 const [phase,setPhase]=useState<'idle'|'shake'|'spin'|'land'>('idle');const [bag,setBag]=useState<{icon?:string;gain:Row|string}[]>([]);const [opened,setOpened]=useState(false);
 const timers=useRef<number[]>([]);const card=useRef<HTMLElement>(null);
 useEffect(()=>()=>{timers.current.forEach(x=>clearTimeout(x))},[]);
 const later=(f:()=>void,ms:number)=>{timers.current.push(window.setTimeout(f,ms))};
 const k=(a?:Row|string,b?:Row|string)=>tr(kids&&b?b:a,language);
 const n=game.steps.length;const st=stage>=0&&stage<n?game.steps[stage]:null;
 const go=()=>{setStage(x=>x+1);setPick(null);setRoll(null);setPhase('idle');sfx('pick');later(()=>card.current?.scrollIntoView({block:'nearest',behavior:'smooth'}),50)};
 const choose=(j:number)=>{if(pick!==null||!st?.choices)return;setPick(j);const c=st.choices[j];if(c.gain)setBag(b=>[...b,{icon:c.icon,gain:c.gain!}]);sfx(c.gain?'hit':'pick')};
 const draw=(d:NonNullable<GameStep['draw']>)=>{
  const r=()=>d.from+Math.floor(Math.random()*(d.to-d.from+1));const final=r();
  setPhase('shake');sfx('shake');
  // the number slows down: 14 flips, each a little longer, the last ones with a heartbeat of ticks
  let at=900;for(let j=0;j<14;j++){const last=j===13;at+=55+j*j*1.9;later(()=>{setPhase('spin');setRoll(last?final:r());sfx('tick')},at)}
  later(()=>{setPhase('land');sfx(final<=d.cut?'low':'high')},at+380)};
 const answered=st&&(st.draw?phase==='land':pick!==null);
 const isLow=st?.draw&&roll!==null?roll<=st.draw.cut:false;
 const open=()=>{setOpened(true);sfx('treasure');chestAdd(`game:${id}`,{label:game.reward||game.title,feed,kind:'game'})};
 const restart=()=>{setStage(-1);setPick(null);setRoll(null);setPhase('idle');setBag([]);setOpened(false)};
 return <section ref={card} className={'feed-game'+(stage<0?' fresh':'')}>
  <h3>🎲 {tr(game.title,language)}</h3>
  {stage<0&&<>{(game.intro||game.kids)&&<p>{k(game.intro,game.kids)}</p>}<button className="game-go big" onClick={go}>▶ {labels.playStart}</button></>}
  {stage>=0&&bag.length>0&&<div className="game-bag"><small>🎒 {labels.playBag}:</small>{bag.map((b,j)=><span key={j} className="game-bag-item">{tr(b.gain,language)}</span>)}</div>}
  {st&&<div className="game-step" key={stage}>
   <div className="game-dots" aria-hidden="true">{game.steps.map((_,j)=><i key={j} className={j<stage?'done':j===stage?'now':''}/>)}</div>
   <p className="game-q">{k(st.q,st.kids)}</p>
   {st.choices&&<div className="game-choices">{st.choices.map((c,j)=><button key={j} className={pick===j?'on':''} disabled={pick!==null&&pick!==j} aria-pressed={pick===j} onClick={()=>choose(j)}>{c.icon&&<span className="game-ico">{c.icon}</span>}<span>{tr(c.text,language)}</span></button>)}</div>}
   {st.choices&&pick!==null&&<p className="game-out">{k(st.choices[pick].outcome,st.choices[pick].kids)}{st.choices[pick].gain&&<span className="game-gain">🎒 + {tr(st.choices[pick].gain,language)}</span>}</p>}
   {st.draw&&<div className={'game-draw '+phase}>
    {phase==='idle'?<button className="game-go big" onClick={()=>draw(st.draw!)}>{st.draw.button?tr(st.draw.button,language):'🎩 '+labels.playDraw}</button>
    :<div className="game-drum-wrap">
     <div className="game-drum" aria-hidden="true">{Array.from({length:9},(_,j)=><i key={j} style={{'--j':j,left:8+(j*37)%52+'px',top:10+(j*23)%54+'px'} as CSSProperties}/>)}</div>
     {phase==='shake'?<span className="game-drum-hint">{labels.playDrumHint}</span>
     :<span className={'game-lot'+(phase==='spin'?' rolling':' landed '+(isLow?'low':'high'))}>№ {roll}{phase==='land'&&<em className={'game-stamp '+(isLow?'low':'high')}>{isLow?tr(st.draw.stampLow,language)||labels.playStampLow:tr(st.draw.stampHigh,language)||labels.playStampHigh}</em>}</span>}
    </div>}
    {answered&&<p className="game-out">{isLow?k(st.draw.low,st.draw.lowKids):k(st.draw.high,st.draw.highKids)}</p>}
   </div>}
   {answered&&<button className="game-go" onClick={go}>{stage+1>=n?'🧰 ':''}{labels.next} ›</button>}
  </div>}
  {stage>=n&&<div className="game-truth">
   {!opened?<button className="game-chest" onClick={open}><span className="game-chest-box">🧰</span><b>{labels.playTreasureOpen}</b></button>
   :<><Confetti/><h4>✨ {labels.playTreasure} {labels.playTruth}</h4>{k(game.truth.text,game.truth.kids).split(/\n{2,}/).map((x,j)=><p key={j}>{x}</p>)}
    {game.truth.record&&<div className="game-treasure">{doc(game.truth.record)}</div>}
    <span className="spot-chest-plus">🧰 + {tr(game.reward||game.title,language)}</span>
    <button className="game-go again" onClick={restart}>↻ {labels.playAgain}</button></>}
  </div>}
 </section>;
}

/* ---------- PanoViewer ---------- */
const VS='attribute vec2 p;varying vec2 v;void main(){v=p;gl_Position=vec4(p,0.,1.);}';
const FS='precision highp float;varying vec2 v;uniform sampler2D t;uniform vec3 F,R,U;uniform vec2 T;'+
 'void main(){vec3 d=normalize(F+R*v.x*T.x+U*v.y*T.y);float lon=atan(d.x,d.z);float lat=asin(clamp(d.y,-1.,1.));'+
 'gl_FragColor=texture2D(t,vec2(fract(lon/6.2831853+.5),.5-lat/3.1415927));}';
const D2R=Math.PI/180,PITCH=55;const NO_SPOTS:Spot[]=[];
type View={yaw:number;pitch:number;vfov:number};
function basis(v:View){const y=v.yaw*D2R,p=v.pitch*D2R;
 return {F:[Math.sin(y)*Math.cos(p),Math.sin(p),Math.cos(y)*Math.cos(p)],R:[Math.cos(y),0,-Math.sin(y)],U:[-Math.sin(p)*Math.sin(y),Math.cos(p),-Math.sin(p)*Math.cos(y)]}}
const dot=(a:number[],b:number[])=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
/** Percent of the panorama (u right, v down) ⇄ a direction. */
const dirOf=(u:number,v:number)=>{const lon=(u/100-.5)*2*Math.PI,lat=(.5-v/100)*Math.PI;return [Math.cos(lat)*Math.sin(lon),Math.sin(lat),Math.cos(lat)*Math.cos(lon)]};
const uvOf=(d:number[])=>{const l=Math.hypot(d[0],d[1],d[2]);return {u:(Math.atan2(d[0],d[2])/(2*Math.PI)+.5)*100,v:(.5-Math.asin(d[1]/l)/Math.PI)*100}};
const inBox=(u:number,v:number,s:Spot,pad=1.5)=>{const du=((u-(s.x+s.w/2))%100+150)%100-50;return Math.abs(du)<=s.w/2+pad&&v>=s.y-pad*2&&v<=s.y+s.h+pad*2};

export function PanoViewer({pano,kids,labels,language,onClose}:{pano:Pano;kids:boolean;labels:Row;language:Language;onClose:()=>void}){
 const feed=useContext(PlayFeed);
 const root=useRef<HTMLDivElement>(null);const canvas=useRef<HTMLCanvasElement>(null);const marks=useRef<(HTMLElement|null)[]>([]);
 const view=useRef<View>({yaw:pano.yaw||0,pitch:pano.pitch||0,vfov:typeof window!=='undefined'&&innerWidth<innerHeight?90:70});const gl=useRef<{draw:()=>void}|null>(null);
 const [ready,setReady]=useState(false);const [err,setErr]=useState(false);const [moved,setMoved]=useState(false);
 const spots=pano.spots||NO_SPOTS;const tasks=spots.map((s,k)=>s.find?k:-1).filter(k=>k>=0);
 const [mode,setMode]=useState<'look'|'find'>(kids&&tasks.length?'find':'look');const [sel,setSel]=useState(-1);
 const [t,setT]=useState(0);const [hit,setHit]=useState(false);const [miss,setMiss]=useState(0);const [tilt,setTilt]=useState(false);
 const [joy,setJoy]=useState<{x:number;y:number;w:string;n:number}|null>(null);const [arrow,setArrow]=useState<0|-1|1>(0);
 const done=mode==='find'&&t>=tasks.length;const cur=mode==='find'&&!done?spots[tasks[t]]:null;
 const state=useRef({mode,cur,hit,miss,sel});useLayoutEffect(()=>{state.current={mode,cur,hit,miss,sel}});

 // marks follow the view: every frame the centre of each spot is projected onto the screen
 const place=useCallback(()=>{const c=canvas.current;if(!c)return;const W=c.clientWidth,H=c.clientHeight;const v=view.current;const b=basis(v);
  const ty=Math.tan(v.vfov*D2R/2),tx=ty*W/H;const st=state.current;
  spots.forEach((s,k)=>{const el=marks.current[k];if(!el)return;const d=dirOf(s.x+s.w/2,s.y+s.h/2);const z=dot(d,b.F);
   const show=st.mode==='look'||k===st.sel||(st.cur===s&&(st.hit||st.miss>1));
   if(z<.08||!show){el.style.display='none';return}
   const px=(dot(d,b.R)/z/tx+1)/2*W,py=(1-dot(d,b.U)/z/ty)/2*H;el.style.display='';el.style.transform=`translate(${px}px,${py}px)`});
  if(st.cur&&!st.hit&&st.miss>1){const d=dirOf(st.cur.x+st.cur.w/2,st.cur.y+st.cur.h/2);const z=dot(d,b.F),x=dot(d,b.R)/Math.max(z,.01)/tx;
   setArrow(z<.08||Math.abs(x)>1?(dot(d,b.R)>0?1:-1):0)}else setArrow(0);
 },[spots]);

 useEffect(()=>{const c=canvas.current!;const g=c.getContext('webgl',{antialias:false})as WebGLRenderingContext|null;if(!g){setErr(true);return}
  const sh=(type:number,src:string)=>{const s=g.createShader(type)!;g.shaderSource(s,src);g.compileShader(s);return s};
  const pr=g.createProgram()!;g.attachShader(pr,sh(g.VERTEX_SHADER,VS));g.attachShader(pr,sh(g.FRAGMENT_SHADER,FS));g.linkProgram(pr);
  if(!g.getProgramParameter(pr,g.LINK_STATUS)){setErr(true);return}
  g.useProgram(pr);const buf=g.createBuffer();g.bindBuffer(g.ARRAY_BUFFER,buf);g.bufferData(g.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),g.STATIC_DRAW);
  const loc=g.getAttribLocation(pr,'p');g.enableVertexAttribArray(loc);g.vertexAttribPointer(loc,2,g.FLOAT,false,0,0);
  const uF=g.getUniformLocation(pr,'F'),uR=g.getUniformLocation(pr,'R'),uU=g.getUniformLocation(pr,'U'),uT=g.getUniformLocation(pr,'T');
  let tex:WebGLTexture|null=null;let raf=0;let alive=true;
  const draw=()=>{if(!alive||!tex)return;const dpr=Math.min(devicePixelRatio||1,2);const W=Math.round(c.clientWidth*dpr),H=Math.round(c.clientHeight*dpr);
   if(c.width!==W||c.height!==H){c.width=W;c.height=H}g.viewport(0,0,W,H);const v=view.current;const b=basis(v);const ty=Math.tan(v.vfov*D2R/2);
   g.uniform3fv(uF,b.F);g.uniform3fv(uR,b.R);g.uniform3fv(uU,b.U);g.uniform2f(uT,ty*W/H,ty);g.drawArrays(g.TRIANGLE_STRIP,0,4);place()};
  gl.current={draw:()=>{cancelAnimationFrame(raf);raf=requestAnimationFrame(draw)}};
  const img=new Image();img.crossOrigin='anonymous';
  img.onload=()=>{if(!alive)return;const max=g.getParameter(g.MAX_TEXTURE_SIZE) as number;let src:TexImageSource=img;
   if(img.width>max){const cv=document.createElement('canvas');cv.width=max;cv.height=max/2;cv.getContext('2d')!.drawImage(img,0,0,max,max/2);src=cv}
   tex=g.createTexture();g.bindTexture(g.TEXTURE_2D,tex);g.texImage2D(g.TEXTURE_2D,0,g.RGB,g.RGB,g.UNSIGNED_BYTE,src);
   g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MIN_FILTER,g.LINEAR);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_MAG_FILTER,g.LINEAR);
   g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_S,g.CLAMP_TO_EDGE);g.texParameteri(g.TEXTURE_2D,g.TEXTURE_WRAP_T,g.CLAMP_TO_EDGE);
   setReady(true);draw()};
  img.onerror=()=>setErr(true);img.src=pano.asset;
  const ro=new ResizeObserver(()=>{const a=c.clientWidth/Math.max(c.clientHeight,1);view.current.vfov=Math.min(view.current.vfov,a<1?90:75);gl.current?.draw()});ro.observe(c);
  return()=>{alive=false;cancelAnimationFrame(raf);ro.disconnect();if(tex)g.deleteTexture(tex)}},[pano.asset,place]);
 useEffect(()=>{gl.current?.draw()},[mode,sel,hit,miss,t]);

 const turn=(dyaw:number,dpitch:number,dfov=0)=>{const v=view.current;v.yaw=((v.yaw+dyaw)%360+540)%360-180;v.pitch=Math.max(-PITCH,Math.min(PITCH,v.pitch+dpitch));v.vfov=Math.max(35,Math.min(90,v.vfov+dfov));gl.current?.draw()};
 const tapRef=useRef<(x:number,y:number)=>void>(()=>{});
 // pointers: one finger turns (with a little inertia), two pinch; a short tap without moving is a tap on the room
 useEffect(()=>{const c=canvas.current!;const pts=new Map<number,{x:number;y:number}>();let start:{x:number;y:number;t:number}|null=null;let vel={x:0,y:0};let last=0;let inert=0;let pinch=0;
  const perPx=()=>view.current.vfov/c.clientHeight;
  const down=(e:PointerEvent)=>{try{c.setPointerCapture(e.pointerId)}catch{}pts.set(e.pointerId,{x:e.clientX,y:e.clientY});cancelAnimationFrame(inert);
   if(pts.size===1){start={x:e.clientX,y:e.clientY,t:performance.now()};vel={x:0,y:0};last=performance.now()}else{start=null;const [a,b]=[...pts.values()];pinch=Math.hypot(a.x-b.x,a.y-b.y)}};
  const move=(e:PointerEvent)=>{const p=pts.get(e.pointerId);if(!p)return;
   if(pts.size===2){p.x=e.clientX;p.y=e.clientY;const [a,b]=[...pts.values()];const d=Math.hypot(a.x-b.x,a.y-b.y);if(pinch)turn(0,0,(pinch-d)*.12);pinch=d;return}
   const dx=e.clientX-p.x,dy=e.clientY-p.y;p.x=e.clientX;p.y=e.clientY;const k=perPx();turn(-dx*k,dy*k);
   const now=performance.now();const dt=Math.max(now-last,8);const cl=(x:number)=>Math.max(-4,Math.min(4,x));vel={x:cl(-dx*k/dt*16),y:cl(dy*k/dt*16)};last=now;
   if(start&&Math.hypot(e.clientX-start.x,e.clientY-start.y)>6){start=null;setMoved(true)}};
  const up=(e:PointerEvent)=>{pts.delete(e.pointerId);if(pts.size)return;
   if(start&&performance.now()-start.t<450){tapRef.current(e.clientX,e.clientY)}
   else if(performance.now()-last<80&&Math.hypot(vel.x,vel.y)>.15){const spin=()=>{vel={x:vel.x*.93,y:vel.y*.93};turn(vel.x,vel.y);if(Math.hypot(vel.x,vel.y)>.03)inert=requestAnimationFrame(spin)};inert=requestAnimationFrame(spin)}
   start=null};
  const wheel=(e:WheelEvent)=>{e.preventDefault();turn(0,0,e.deltaY*.04)};
  c.addEventListener('pointerdown',down);c.addEventListener('pointermove',move);c.addEventListener('pointerup',up);c.addEventListener('pointercancel',up);c.addEventListener('wheel',wheel,{passive:false});
  return()=>{cancelAnimationFrame(inert);c.removeEventListener('pointerdown',down);c.removeEventListener('pointermove',move);c.removeEventListener('pointerup',up);c.removeEventListener('pointercancel',up);c.removeEventListener('wheel',wheel)}
 },[]);
 // keys: arrows turn, Escape leaves; the feed underneath does not hear them
 useEffect(()=>{const key=(e:KeyboardEvent)=>{const m:Record<string,[number,number]>={ArrowLeft:[-12,0],ArrowRight:[12,0],ArrowUp:[0,8],ArrowDown:[0,-8]};
   if(e.key==='Escape'){e.stopImmediatePropagation();onClose()}else if(m[e.key]){e.stopImmediatePropagation();e.preventDefault();turn(...m[e.key])}else if(e.key===' ')e.stopImmediatePropagation()};
  addEventListener('keydown',key,true);return()=>removeEventListener('keydown',key,true)});
 // tilt of the phone: the view follows the turn and tilt from the moment it was switched on
 useEffect(()=>{if(!tilt)return;let base:{a:number;b:number;yaw:number;pitch:number}|null=null;
  const f=(e:DeviceOrientationEvent)=>{if(e.alpha==null||e.beta==null)return;if(!base){base={a:e.alpha,b:e.beta,yaw:view.current.yaw,pitch:view.current.pitch};return}
   const da=((e.alpha-base.a+540)%360)-180;view.current.yaw=((base.yaw-da)%360+540)%360-180;view.current.pitch=Math.max(-PITCH,Math.min(PITCH,base.pitch+(e.beta-base.b)));gl.current?.draw()};
  addEventListener('deviceorientation',f);return()=>removeEventListener('deviceorientation',f)},[tilt]);
 const toggleTilt=async()=>{if(tilt){setTilt(false);return}const D=(window as unknown as {DeviceOrientationEvent?:{requestPermission?:()=>Promise<string>}}).DeviceOrientationEvent;
  try{if(D?.requestPermission&&await D.requestPermission()!=='granted')return}catch{return}setTilt(true)};
 const full=()=>{const el=root.current;if(!el)return;if(document.fullscreenElement)void document.exitFullscreen();else el.requestFullscreen?.().catch(()=>{})};
 useEffect(()=>()=>{if(document.fullscreenElement)void document.exitFullscreen().catch(()=>{})},[]);

 function tapAt(x:number,y:number){const c=canvas.current!;const r=c.getBoundingClientRect();const v=view.current;const b=basis(v);
  const ty=Math.tan(v.vfov*D2R/2),tx=ty*r.width/r.height;const nx=((x-r.left)/r.width)*2-1,ny=1-((y-r.top)/r.height)*2;
  const d=[0,1,2].map(i=>b.F[i]+b.R[i]*nx*tx+b.U[i]*ny*ty);const {u,v:vv}=uvOf(d);const st=state.current;
  if(st.mode==='look'){const k=spots.findIndex(s=>inBox(u,vv,s,0));setSel(k);if(k>=0)sfx('pick');return}
  if(!st.cur||st.hit)return;
  if(inBox(u,vv,st.cur)){setHit(true);setJoy({x:x-r.left,y:y-r.top,w:praise(labels),n:Date.now()});const idx=spots.indexOf(st.cur);
   chestAdd(`find:${pano.asset}#${idx}`,{label:st.cur.label,feed,kind:'find'});
   if(tasks.indexOf(idx)+1>=tasks.length)window.setTimeout(()=>sfx('done'),250);else sfx('hit')}
  else{setMiss(m=>m+1);sfx('miss')}}
 useEffect(()=>{tapRef.current=tapAt});
 const nextTask=()=>{setT(x=>x+1);setHit(false);setMiss(0);setJoy(null);sfx('pick')};
 const startFind=()=>{setMode('find');setSel(-1);setT(0);setHit(false);setMiss(0);setJoy(null);sfx('pick')};
 const txt=(s:Spot)=>tr(kids&&s.kids?s.kids:s.text,language);
 const s=sel>=0?spots[sel]:null;const found=t+(hit?1:0);
 const stop=(e:{stopPropagation:()=>void})=>e.stopPropagation();
 return createPortal(<div ref={root} className="pano" role="dialog" aria-modal="true" aria-label={tr(pano.title,language)} onTouchStart={stop} onTouchEnd={stop} onClick={stop}>
  <canvas ref={canvas} className="pano-canvas"/>
  <div className="pano-marks">{spots.map((x,k)=><button key={k} ref={el=>{marks.current[k]=el}} className={'pano-mark'+(k===sel?' on':'')+(mode==='find'?(cur===x&&hit?' found':' blink'):'')} style={{display:'none'}}
   aria-label={tr(x.label,language)} onClick={e=>{e.stopPropagation();if(mode==='look'){setSel(v=>v===k?-1:k);sfx('pick')}}}><span>{mode==='look'?tr(x.label,language):''}</span></button>)}</div>
  {joy&&<Burst x={joy.x} y={joy.y} word={joy.w} n={joy.n}/>}
  {arrow!==0&&<div className={'pano-arrow '+(arrow<0?'l':'r')} aria-hidden="true">{arrow<0?'‹‹':'››'}</div>}
  <div className="pano-top">
   <b>🏠 {tr(pano.title,language)}</b>
   <div className="pano-tools">
    {spots.length>0&&<button className={mode==='look'?'on':''} onClick={()=>{setMode('look');setSel(-1)}}>🔍 {labels.playLook}</button>}
    {tasks.length>0&&<button className={mode==='find'?'on':''} onClick={startFind}>◎ {labels.playFind}</button>}
    {typeof window!=='undefined'&&'DeviceOrientationEvent' in window&&matchMedia('(pointer:coarse)').matches&&<button className={tilt?'on':''} onClick={toggleTilt} aria-pressed={tilt}>📱 {labels.panoTilt}</button>}
    <MuteBtn labels={labels} className="pano-ico"/>
    <button className="pano-ico" onClick={full} aria-label="⛶">⛶</button>
    <button className="pano-x" onClick={onClose} aria-label={labels.panoExit}>× <span>{labels.panoExit}</span></button>
   </div>
  </div>
  {mode==='find'&&<div className={'spot-task pano-task'+(hit?' hit':'')+(done?' done':'')} role="status" aria-live="polite">
   {done?<><Confetti/><b>🎉 {labels.playAll}</b><Stars n={tasks.length} m={tasks.length}/><span className="spot-chest-plus">🧰 +{tasks.length} {labels.playToChest}</span><button className="spot-task-go" onClick={()=>setMode('look')}>🔍 {labels.playLookAll}</button></>
   :hit&&cur?<><b>✨ {tr(cur.label,language)}!</b><p>{txt(cur)}</p><Stars n={found} m={tasks.length}/><button className="spot-task-go" onClick={nextTask}>{t+1>=tasks.length?'🎉':labels.next+' ›'}</button></>
   :cur&&<><b>{tr(cur.find,language)}</b>{miss>0&&<p>{miss>1?labels.playHint:labels.playMiss}</p>}<Stars n={found} m={tasks.length}/></>}
  </div>}
  {s&&mode==='look'&&<div className="spot-card pano-card" onClick={()=>setSel(-1)}><b>{tr(s.label,language)}</b><p>{txt(s)}</p></div>}
  {!moved&&ready&&!s&&<div className="pano-hint" aria-hidden="true"><span>👆</span>{labels.panoHint}</div>}
  {!ready&&!err&&<div className="pano-wait">…</div>}
  {err&&<div className="pano-wait">WebGL ✕ — <a href={pano.asset} target="_blank" rel="noreferrer">360° ↗</a></div>}
 </div>,document.body);
}
