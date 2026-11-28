'use client';
import {useEffect,useMemo,useRef,useState} from 'react';
import Lightbox from './tree/lightbox';
import Feedback from './tree/feedback';
import {kinNote} from './kinship-words';
import {isPerson,lifeLabel,relationPhrase,translated,type Model,type Row} from './tree/model';
import type {Language} from './i18n';
/** One paper of the family: its picture, its own page with the reading, and whose it is. */
export type Paper={id:string;title:string;year?:number;thumb?:string;full?:string;page?:string;reading?:string;people:string[]};
const PAPER_KINDS=new Set(['archive-record','home-paper','record','document','document-scan']);
const PICTURE=/[.](png|jpe?g|webp|gif)$/i,PAGE=/[.]html?($|[?#])/i,YEAR=/(?<!\d)(1[5-9]\d\d|20[0-2]\d)(?!\d)/;
const picture=(s?:Row):string=>s?.image||(PICTURE.test(s?.asset||'')?s!.asset:'');
/** A fact too weak for the card takes its source off the card and the papers alike. */
export function weakOnlySources(p:Row,from:number){const weak=(f:Row)=>typeof f.weight==='number'&&f.weight<from;
 const kept=new Set<string>([...(p.names||[]),...(p.events||[]),...(p.facts||[]).filter((f:Row)=>!weak(f))].flatMap((r:Row)=>[...(r.sources||[]),...(r.provenance||[])]));
 return new Set<string>((p.facts||[]).filter(weak).flatMap((f:Row)=>f.sources||[]).filter((sid:string)=>!kept.has(sid)))}
/** Everything the delivered graph shows as a paper, once each. Nothing is added to it and nothing withheld is asked for. */
export function collectPapers(data:Row,model:Model,language:Language):Paper[]{
 const out=new Map<string,Paper>(),years=new Map<string,number>(),photos=new Set<string>();
 const get=(id:string)=>out.get(id)||out.set(id,{id,title:'',people:[]}).get(id)!;
 const add=(x:Paper,pid:string)=>{if(!x.people.includes(pid))x.people.push(pid)};
 for(const p of Object.values<Row>(data.people||{}))for(const m of p.media||[])if(m.photo)photos.add(m.sourceSid||m.sid);
 const source=(sid:string,pid?:string)=>{const s=data.sources[sid];if(!s||photos.has(sid))return;const shot=picture(s);
  if(!shot&&!(PAPER_KINDS.has(s.kind)&&s.asset))return;
  const x=get(sid);x.title||=s.title||'';if(shot){x.thumb||=shot;x.full||=shot}if(s.asset&&s.asset!==shot)x.page||=s.asset;if(pid)add(x,pid)};
 const media=(m:Row,pid?:string)=>{if(!m.asset||m.photo||m.kind==='photo-restoration'||m.ours?.kind==='photo-restoration')return;
  const sid=m.sourceSid||m.sid||m.asset,s=data.sources[sid],x=get(sid);
  const raster=PICTURE.test(m.asset)?m.asset:undefined;
  x.title=x.title||m.title||s?.title||'';x.thumb||=picture(s)||raster;x.full||=(PICTURE.test(m.originalAsset||'')?m.originalAsset:raster)||x.thumb;x.reading||=translated(m.description,language)||undefined;
  if(s?.asset&&PAGE.test(s.asset))x.page||=s.asset;if(pid)add(x,pid)};
 for(const [pid,p] of Object.entries<Row>(data.people||{})){const info=model.info[pid];if(!isPerson(info))continue;
  for(const m of p.media||[])media(m,pid);
  for(const match of p.probableIdentities||[]){
   for(const m of match.card?.media||[])media(m);
   for(const sid of match.card?.papers||[])source(sid);
  }
  const dropped=weakOnlySources(p,.3);
  for(const sid of info.growth.documents)if(!dropped.has(sid))source(sid,pid);
  for(const r of [...(p.events||[]),...(p.facts||[])]){const y=Number((YEAR.exec(String(r.date||''))||[])[1]);
   if(y)for(const sid of [...(r.sources||[]),...(r.provenance||[])])years.set(sid,Math.min(years.get(sid)??9999,y))}}
 // A scanned record belongs to everybody it names, whatever cites it.
 for(const [sid,s] of Object.entries<Row>(data.sources||{}))if(picture(s)&&s.kind!=='memory')for(const pid of s.subjects||[])
  if(isPerson(model.info[pid])&&!weakOnlySources(data.people[pid]||{},.3).has(sid))source(sid,pid);
 for(const x of out.values())x.year=Number((YEAR.exec(x.title)||[])[1])||years.get(x.id);
 return [...out.values()].filter(x=>x.title||x.thumb).sort(byYear);
}
const byYear=(a:Paper,b:Paper)=>(a.year??9999)-(b.year??9999)||a.title.localeCompare(b.title);
/** A sheet one can see comes before a line one can only read. */
export const pictured=(list:Paper[])=>[...list.filter(x=>x.thumb),...list.filter(x=>!x.thumb)];
const decade=(y:number,labels:Row)=>String(labels.decade).replace('{n}',String(Math.floor(y/10)*10));
/** A paper lies on the table: whole, never cropped; one that has no picture shows its own title as a written line. */
/** One line cut from a register is a thread in a tile: show its sheet, or the beginning of the line large enough to see. */
const strip=(i:HTMLImageElement,paper:Paper)=>{const ratio=i.naturalWidth/i.naturalHeight;if(ratio<4)return;
 if(ratio>8&&paper.full&&paper.full!==i.getAttribute('src')){i.src=paper.full;return}
 i.classList.add('strip');i.style.height=Math.min(72,1000/ratio)+'px'};
export function PaperTile({paper,open}:{paper:Paper;open:()=>void}){
 return <button className={'paper-tile'+(paper.thumb?'':' written')} onClick={open}>
  {/* eslint-disable-next-line @next/next/no-img-element */}
  <span className="paper-sheet">{paper.thumb?<img src={paper.thumb} alt="" loading="lazy" decoding="async" onLoad={e=>strip(e.currentTarget,paper)}/>:<i aria-hidden="true"/>}</span>
  <span className="paper-title">{paper.title}</span>
 </button>}
/** Who is nearest to the reader comes first. */
export function papersByPerson(papers:Paper[],model:Model,me:string){
 const from=me&&model.info[me]?me:model.homes[0];
 const near=(id:string)=>{if(id===from)return 0;const r=from?model.relation(from,id):null;return r?r.n1+r.n2+(r.spouseOf||r.viaSpouse!==undefined?1.5:0)+(r.kind==='collateral'?.5:0):99};
 const by=new Map<string,Paper[]>();for(const x of pictured(papers))for(const id of x.people)(by.get(id)||by.set(id,[]).get(id)!).push(x);
 return [...by].map(([id,list])=>({id,list,near:near(id)})).sort((a,b)=>a.near-b.near||(model.info[b.id].birth??0)-(model.info[a.id].birth??0)||model.info[a.id].short.localeCompare(model.info[b.id].short));
}
/** "отец · 1895": who this is to the reader, then the years. */
const whoLine=(id:string,model:Model,me:string,labels:Row,language:Language)=>{const i=model.info[id],r=me&&me!==id&&model.info[me]?model.relation(me,id):null;
 return [r?relationPhrase(r,labels,language):'',lifeLabel(i,labels,language)].filter(Boolean).join(' · ')};
const FIRST=12,EACH=4;
export type PaperMode='people'|'time'|'photos';
/** «Show me the papers»: by person, the nearest first; by time; and the photographs beside them. */
export default function Papers({papers,model,me,labels,language,mode,setMode,of='',open,show,go,photos}:{papers:Paper[];model:Model;me:string;labels:Row;language:Language;mode:PaperMode;setMode:(m:PaperMode)=>void;of?:string;open:(id:string,list:string[])=>void;show:(of:string)=>void;go:(id:string,details?:boolean)=>void;photos?:React.ReactNode}){
 const [limit,setLimit]=useState(FIRST);
 const people=useMemo(()=>papersByPerson(papers,model,me),[papers,model,me]);
 const eras=useMemo(()=>{const by=new Map<string,Paper[]>();for(const x of papers){const k=x.year?decade(x.year,labels):labels.papersNoYear;(by.get(k)||by.set(k,[]).get(k)!).push(x)}return [...by]},[papers,labels.languageCode]);
 const who=(id:string)=>whoLine(id,model,me,labels,language);
 const grid=(list:Paper[],all=list)=><div className="paper-grid">{list.map(x=><PaperTile key={x.id} paper={x} open={()=>open(x.id,all.map(y=>y.id))}/>)}</div>;
 const own=of&&model.info[of]?pictured(papers.filter(x=>x.people.includes(of))):[];
 if(own.length)return <section className="page papers"><h1>{model.info[of].short}</h1>{who(of)&&<p className="lead">{who(of)}</p>}{grid(own)}
   <button className="wide-btn" onClick={()=>show('')}>{labels.papersEveryone}</button></section>;
 const modes=[...(papers.length?[['people',labels.papersByPeople],['time',labels.papersByTime]]:[]),...(photos?[['photos',labels.photos]]:[])] as [PaperMode,string][];
 const shown=modes.some(([k])=>k===mode)?mode:modes[0]?.[0];
 return <section className="page papers"><h1>{labels.papers}</h1>
  {modes.length>1&&<div className="paper-modes" role="group" aria-label={labels.papers}>{modes.map(([k,l])=><button key={k} aria-pressed={shown===k} className={shown===k?'on':''} onClick={()=>setMode(k)}>{l}</button>)}</div>}
  {shown==='people'&&<>{people.slice(0,limit).map(({id,list})=><section className="paper-person" key={id}>
    <button className="paper-who" onClick={()=>go(id,true)}><strong>{model.info[id].short}</strong>{who(id)&&<small>{who(id)}</small>}</button>
    {grid(list.slice(0,EACH),list)}
    {list.length>EACH&&<button className="wide-btn" onClick={()=>show(id)}>{labels.papersAll}: {list.length}</button>}
   </section>)}
   {people.length>limit&&<button className="wide-btn" onClick={()=>setLimit(limit+FIRST)}>{labels.papersMore}</button>}</>}
  {shown==='time'&&eras.map(([k,list])=><section className="paper-era" key={k}><h2>{k}</h2>{grid(list,papers)}</section>)}
  {shown==='photos'&&photos}
 </section>
}
/** One paper, large: the picture, whose it is and what it says. Closing it uncovers exactly what was underneath. */
export function PaperView({paper,list,step,onClose,go,model,me,labels,language}:{paper:Paper;list:Paper[];step:(id:string)=>void;onClose:()=>void;go:(id:string,details?:boolean)=>void;model:Model;me:string;labels:Row;language:Language}){
 const [reading,setReading]=useState('');const [zoom,setZoom]=useState<number|null>(null);const body=useRef<HTMLDivElement>(null);
 const at=list.findIndex(x=>x.id===paper.id),prev=at>0?list[at-1]:null,next=at>=0&&at<list.length-1?list[at+1]:null;
 // The paper's own page carries its reading in the reader's language; the same text is shown here.
 useEffect(()=>{setReading('');setZoom(null);body.current?.scrollTo({top:0});if(!paper.page||!PAGE.test(paper.page))return;let live=true;
  fetch(paper.page).then(r=>r.ok?r.text():'').then(text=>{if(!live||!text)return;const node=new DOMParser().parseFromString(text,'text/html').querySelector('.document-reading');
   if(node){node.querySelectorAll('script,style,iframe,object,link').forEach(x=>x.remove());const lines=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);for(let t=lines.nextNode();t;t=lines.nextNode())t.textContent=(t.textContent||'').replace(/\s*\|\s*/g,'\n');setReading(node.innerHTML)}}).catch(()=>{});
  return()=>{live=false}},[paper.id,paper.page]);
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(zoom!==null||e.target instanceof HTMLElement&&e.target.closest('input,textarea,select'))return;
  const take=()=>{e.preventDefault();e.stopImmediatePropagation()};
  if(e.key==='Escape'){take();onClose()}else if(e.key==='ArrowRight'){take();if(next)step(next.id)}else if(e.key==='ArrowLeft'){take();if(prev)step(prev.id)}};
  addEventListener('keydown',key,true);return()=>removeEventListener('keydown',key,true)});
 const pictures=[...(paper.thumb?[{src:paper.thumb,label:''}]:[]),...(paper.full&&paper.full!==paper.thumb?[{src:paper.full,label:labels.fullPage}]:[])];
 const docs=pictures.map((x,k)=>({sid:paper.id+':'+k,title:paper.title,asset:x.src,photo:false}));
 const text=reading||'';
 return <div className="paper-view" role="dialog" aria-modal="true" aria-label={paper.title}>
  <div className="paper-bar"><button className="paper-back" onClick={onClose}>← {labels.back}</button>{list.length>1&&at>=0&&<span>{at+1} / {list.length}</span>}</div>
  <div ref={body} className="paper-body"><div className="paper-column">
   {pictures.map((x,k)=><figure key={x.src} className="paper-large">{x.label&&<figcaption>{x.label}</figcaption>}
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <button onClick={()=>setZoom(k)} aria-label={labels.paperZoom}><img src={x.src} alt={paper.title}/></button></figure>)}
   <h2>{paper.title}</h2>
   {paper.people.length>0&&<div className="paper-whose"><h3>{labels.paperWhose}</h3><div className="chips">{paper.people.map(id=>{const i=model.info[id];if(!i)return null;
     const r=me&&me!==id&&model.info[me]?model.relation(me,id):null,line=[r?relationPhrase(r,labels,language):'',r?kinNote(r,language):''].filter(Boolean).join(': ')||lifeLabel(i,labels,language);
     return <button className="chip" key={id} onClick={()=>go(id,true)}><b>{i.short}</b>{line&&<small>{line}</small>}</button>})}</div></div>}
   {text?<div className="paper-reading"><h3>{labels.paperReading}</h3><div className="document-reading" dangerouslySetInnerHTML={{__html:text}}/></div>
    :paper.reading?<div className="paper-reading"><h3>{labels.paperReading}</h3><div className="document-reading"><p>{paper.reading}</p></div></div>:null}
   {!pictures.length&&paper.page&&!PAGE.test(paper.page)&&<a className="wide-btn" href={paper.page}>{labels.feedOpenDoc}</a>}
   <div className="paper-remark"><Feedback language={language} finding={paper.title}/></div>
   {list.length>1&&at>=0&&<div className="paper-turn"><button disabled={!prev} onClick={()=>prev&&step(prev.id)}>‹ {labels.paperPrev}</button><button disabled={!next} onClick={()=>next&&step(next.id)}>{labels.paperNext} ›</button></div>}
  </div></div>
  {zoom!==null&&<Lightbox docs={docs} index={zoom} setIndex={setZoom} onClose={()=>setZoom(null)} labels={labels}/>}
 </div>
}
