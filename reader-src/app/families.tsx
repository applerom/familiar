'use client';
import {useMemo,useState,type ReactNode} from 'react';
import {lineTitle,placeLabel,type Model,type Row} from './tree/model';
import {plural,type Language} from './i18n';
import {findPeople} from './search';
type Group={key:string;name:string;variants:string[];people:string[];from?:number;to?:number;places:string[];gen:number;version:number};
/** Compare Cyrillic spellings in Polish Latin transliteration. */
const CYR:Record<string,string>={а:'a',б:'b',в:'w',г:'h',д:'d',е:'ie',ё:'io',ж:'z',з:'z',и:'i',й:'j',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'ch',ц:'c',ч:'cz',ш:'sz',щ:'szcz',ъ:'',ы:'y',ь:'',э:'e',ю:'ju',я:'ja',і:'i',ў:'u'};
const translit=(s:string)=>s.replace(/[а-яёіў]/g,(c,i)=>c==='е'&&(i===0||/[аеёиоуыэюяaeiou]/i.test(s[i-1]||''))?'je':CYR[c]??c);
/** Compare surnames without accents, case or script. */
const fold=(s:string)=>translit(s.toLocaleLowerCase()).normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/ł/g,'l').trim();
/** Edit distance folds one-letter spelling variants into one family. */
function dist(a:string,b:string){if(Math.abs(a.length-b.length)>1)return 2;const d=Array.from({length:a.length+1},(_,i)=>[i,...Array(b.length).fill(0)]);for(let j=1;j<=b.length;j++)d[0][j]=j;
 for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return d[a.length][b.length]}
function groupBySurname(m:Model,ids:Iterable<string>,gen:(id:string)=>number,version:(id:string)=>boolean):Group[]{
 const groups=new Map<string,Group>();const forms=new Map<string,Map<string,number>>();
 const add=(g:Group,id:string,sur:string)=>{const i=m.info[id];g.people.push(id);g.gen=Math.min(g.gen,gen(id));if(version(id))g.version++;
  if(i.birth){g.from=g.from===undefined?i.birth:Math.min(g.from,i.birth);g.to=g.to===undefined?i.birth:Math.max(g.to,i.birth)}
  if(i.place&&i.placeRole==='birth'&&!g.places.includes(i.place))g.places.push(i.place);
  const f=forms.get(g.key)||forms.set(g.key,new Map()).get(g.key)!;f.set(sur,(f.get(sur)||0)+1)};
 for(const id of ids){const i=m.info[id];if(!i||i.placeholder)continue;const sur=i.surnameKey;if(!sur)continue;const key=fold(sur);
  let g=groups.get(key);
  if(!g&&key.length>=7)for(const o of groups.values())if(dist(o.key,key)<=1){g=o;break}
  if(!g){g={key,name:sur,variants:[],people:[],places:[],gen:gen(id),version:0};groups.set(key,g)}
  add(g,id,sur)}
 for(const g of groups.values()){const ranked=[...forms.get(g.key)!.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).map(([s])=>s);g.name=ranked[0];g.variants=ranked.slice(1);g.people.sort((a,b)=>(m.info[a].birth??9999)-(m.info[b].birth??9999)||m.info[a].short.localeCompare(m.info[b].short))}
 return [...groups.values()].sort((a,b)=>a.gen-b.gen||b.people.length-a.people.length||a.name.localeCompare(b.name));
}
const cap=(s:string)=>s.charAt(0).toLocaleUpperCase()+s.slice(1);
export default function Families({data,model,connected,group,go,labels,language,row}:{data:Row;model:Model;connected:Set<string>;group:(id:string)=>string;go:(id:string)=>void;labels:Row;language:Language;row:(id:string)=>ReactNode}){
 const [open,setOpen]=useState('');const [query,Q]=useState('');const [scope,Scope]=useState('all');const [list,setList]=useState(false);
 // the four ancestor lines: everyone above the line's first person, with the generation and whether a dotted link lies on the way
 const lines=useMemo(()=>model.lines.map((l,idx)=>{const gen=new Map<string,number>(),via=new Map<string,boolean>();const todo:[string,number,boolean][]=[[l.id,1,l.status==='hypothesis']];
  while(todo.length){const [x,g,v]=todo.pop()!;if(gen.has(x))continue;gen.set(x,g);via.set(x,v);model.parents(x).slots.forEach(s=>s&&todo.push([s.id,g+1,v||model.connectionLevel(s)===3]))}
  return {...l,idx,members:gen,groups:groupBySurname(model,gen.keys(),id=>gen.get(id)!,id=>via.get(id)!)}}),[model]);
 // surnames that came in by marriage: everyone connected who is not on an ancestor line, minus the line surnames in any spelling
 const inLaws=useMemo(()=>{const taken=lines.flatMap(l=>l.groups.flatMap(g=>[g.name,...g.variants].map(fold)));const inside=new Set(lines.flatMap(l=>[...l.members.keys()]));
  const isLine=(g:Group)=>[g.name,...g.variants].map(fold).some(k=>taken.some(t=>t===k||(k.length>=7&&dist(t,k)<=1)));
  return groupBySurname(model,[...connected].filter(id=>!inside.has(id)&&(!lines.length||!model.homes.includes(id))),()=>0,()=>false).filter(g=>!isLine(g)).sort((a,b)=>b.people.length-a.people.length||a.name.localeCompare(b.name))},[lines,connected,model]);
 const needle=query.trim().toLocaleLowerCase();
 const results=useMemo(()=>{const keep=(id:string)=>scope==='all'||group(id)===scope;const ids=needle?findPeople(data.people,model,needle,keep).map(h=>h.id):list?Object.keys(data.people).filter(id=>model.info[id]&&!model.info[id].placeholder&&keep(id)):[];return ids.map(id=>data.people[id] as Row).sort((a,b)=>model.info[a.id].short.localeCompare(model.info[b.id].short,language))},[needle,list,scope,data,model,group,language]);
 const n=(k:number)=>`${k} ${plural(k,labels.personsForms,language)}`;
 const span=(g:Group)=>g.from===undefined?'':g.from===g.to?String(g.from):`${g.from}–${g.to}`;
 const chips=(gs:Group[],prefix:string)=><div className="surnames">{gs.map(g=>{const k=prefix+g.key;return <button key={k} className={'sur'+(open===k?' on':'')+(g.version===g.people.length&&g.version?' ver':'')} aria-expanded={open===k} onClick={()=>setOpen(open===k?'':k)}><b>{g.name}{g.variants.length>0&&<small className="var"> · {labels.alsoSpelled} {g.variants.join(', ')}</small>}</b><small>{[n(g.people.length),span(g),g.places.slice(0,2).join(', ')].filter(Boolean).join(' · ')}</small></button>})}</div>;
 const opened=(gs:Group[],prefix:string)=>{const g=gs.find(x=>prefix+x.key===open);return g?<div className="rows opened">{g.version>0&&g.version<g.people.length&&<p className="note">{labels.viaVersion}</p>}{g.people.map(id=>row(id))}</div>:null};
 return <section className="page families">
  <h1>{labels.familiesTitle}</h1><p className="lead">{labels.familiesIntro}</p>
  {lines.map(l=>{const i=model.info[l.id];const home=model.info[l.home].short.split(' ')[0];const place=placeLabel(i,labels);
   return <section key={l.id} className="line" style={{'--b':l.color} as React.CSSProperties}>
    <h2><i aria-hidden="true"/>{lineTitle(l,model,labels)}</h2>
    <p className="line-head"><button className="link" onClick={()=>go(l.id)}>{i.short}</button>{place&&<span> · {place}</span>}<span> · {n(l.members.size)}</span></p>
    {chips(l.groups,l.idx+':')}{opened(l.groups,l.idx+':')}
   </section>})}
  {inLaws.length>0&&<section className="line inlaws"><h2><i aria-hidden="true"/>{lines.length?labels.inLaws:labels.familiesTitle}</h2>{lines.length>0&&<p className="line-head">{labels.inLawsHint}</p>}{chips(inLaws,'in:')}{opened(inLaws,'in:')}</section>}
  <section className="line all"><h2><i aria-hidden="true"/>{labels.peopleTitle}</h2><p className="line-head">{labels.peopleHint}</p>
   <div className="people-tools"><label className="search"><input aria-label={labels.find} placeholder={labels.search} value={query} onChange={e=>Q(e.target.value)}/></label>
    <select aria-label={labels.people} value={scope} onChange={e=>Scope(e.target.value)}><option value="family">{labels.relatives}</option><option value="context">{labels.otherFamilies}</option><option value="all">{labels.everyone}</option></select>
    {!needle&&<button className="more wide" onClick={()=>setList(!list)}>{list?labels.hideList:labels.showList}</button>}</div>
   {(needle||list)&&<><p className="note">{labels.found}: {results.length}</p><div className="rows">{results.map(p=>row(p.id))}</div></>}
  </section>
 </section>
}
