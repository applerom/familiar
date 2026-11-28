'use client';
import {useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {isPerson,type Model,type Row} from './tree/model';

/** Cyrillic letters in a rough Latin sound, so "Ковальский" meets "Kowalski". */
const CYR:Record<string,string>={а:'a',б:'b',в:'v',г:'h',ґ:'g',д:'d',е:'e',ё:'e',є:'e',ж:'z',з:'z',и:'i',і:'i',ї:'i',й:'i',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ў:'u',ф:'f',х:'h',ц:'c',ч:'c',ш:'s',щ:'s',ъ:'',ы:'i',ь:'',э:'e',ю:'iu',я:'ia'};
/** One spelling key for names in any script: no case, accents or Polish digraphs, doubled letters folded. */
export function searchKey(s:string){
 return s.toLocaleLowerCase().replace(/ł/g,'l').normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[а-яёґєіїў]/g,c=>CYR[c]??c)
  .replace(/szcz/g,'s').replace(/sz/g,'s').replace(/cz/g,'c').replace(/rz/g,'z').replace(/ch/g,'h').replace(/w/g,'v').replace(/[jy]/g,'i').replace(/ie/g,'e').replace(/(.)\1+/g,'$1');
}
function strings(x:unknown,out:string[]){if(typeof x==='string')out.push(x);else if(Array.isArray(x))x.forEach(y=>strings(y,out));else if(x&&typeof x==='object')Object.values(x).forEach(y=>strings(y,out));return out}
/** Every word of the query must appear: in the names first, otherwise in dates and places. Names rank higher. */
export function findPeople(people:Row,model:Model,query:string,keep:(id:string)=>boolean=()=>true){
 const words=query.split(/\s+/).map(searchKey).filter(Boolean);if(!words.length)return [];
 const found:{id:string;byName:boolean}[]=[];
 for(const p of Object.values<Row>(people)){if(!isPerson(model.info[p.id])||!keep(p.id))continue;
  const possible=(p.probableIdentities||[]).map((m:Row)=>[m.name,m.card?.names]);
  const names=searchKey(strings([model.info[p.id].short,p.name,p.names,p.namePresentation,p.disambiguator,possible],[]).join(' '));
  if(words.every(w=>names.includes(w))){found.push({id:p.id,byName:true});continue}
  const all=names+' '+searchKey(strings([p.events,(p.facts||[]).map((f:Row)=>[f.label,f.text])],[]).join(' '));
  if(words.every(w=>all.includes(w)))found.push({id:p.id,byName:false})}
 return found;
}
const LIMIT=40;
/** The search sheet: opened from the magnifier in the header, or with "/" and Ctrl+K on a keyboard. */
export function SearchSheet({data,model,group,row,labels,onClose}:{data:Row;model:Model;group:(id:string)=>string;row:(id:string)=>ReactNode;labels:Row;onClose:()=>void}){
 const [query,Q]=useState('');const box=useRef<HTMLInputElement>(null);
 useEffect(()=>{box.current?.focus()},[]);
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.stopImmediatePropagation();onClose()}};addEventListener('keydown',key,true);return()=>removeEventListener('keydown',key,true)},[onClose]);
 const sections=useMemo(()=>{const order=['family','context','archive'];const hits=findPeople(data.people,model,query);
  const born=(id:string)=>model.info[id].birth??9999;
  return order.map(g=>({g,ids:hits.filter(h=>group(h.id)===g).sort((a,b)=>Number(b.byName)-Number(a.byName)||born(a.id)-born(b.id)||model.info[a.id].short.localeCompare(model.info[b.id].short)).map(h=>h.id)})).filter(s=>s.ids.length)},[query,data,model,group]);
 const total=sections.reduce((n,s)=>n+s.ids.length,0);
 const title:Record<string,string>={family:labels.relatives,context:labels.otherFamilies,archive:labels.withdrawn};
 return <section className="search-sheet" role="dialog" aria-label={labels.find}>
  <div className="search-line"><label className="search"><input ref={box} type="text" enterKeyHint="search" autoComplete="off" spellCheck={false} aria-label={labels.find} placeholder={labels.search} value={query} onChange={e=>Q(e.target.value)}/></label>
   <button className="icon-btn" aria-label={labels.close} onClick={onClose}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg></button></div>
  {query.trim()?<div className="results">{total===0&&<p className="note">{labels.searchNone}</p>}
   {sections.map(s=><div key={s.g}><h2>{title[s.g]} · {s.ids.length}</h2><div className="rows">{s.ids.slice(0,LIMIT).map(id=>row(id))}</div>{s.ids.length>LIMIT&&<p className="note">{labels.searchMore}</p>}</div>)}</div>
  :<p className="note">{labels.searchHint}</p>}
 </section>
}
/** The magnifier in the header. */
export const SearchButton=({open,label,onClick}:{open:boolean;label:string;onClick:()=>void})=><button className={'icon-btn search-btn'+(open?' active':'')} aria-label={label} aria-expanded={open} onClick={onClick}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg></button>;
