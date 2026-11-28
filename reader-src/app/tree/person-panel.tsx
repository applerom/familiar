'use client';
import {feedbackEnabled,inLanguage} from '../reader-profile';
import {SecondWay} from './second-way';
import {useEffect,useMemo,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {isPerson,genitive,humanText,kinPhrase,relationPhrase,lifeLabel,guessBasis,placeLabel,lifeFactText,translated,DOCUMENT_NAME_TYPES,type Model,type Row,type Slot} from './model';
import {kinshipTerm} from './kinship';
import {KinshipExplanation} from '../kinship-words';
import {PaperTile,pictured,weakOnlySources,type Paper} from '../papers';
import Feedback from './feedback';
import ConfirmationMark,{confirmationText} from './confirmation';
import Lightbox,{type Doc} from './lightbox';
import {Face,region} from './portrait';
import {storyParts,storyText} from '../stories';
import {FeedFigure,tr,type Feed} from '../feed';
import {plural,type Language} from '../i18n';
const LIFE=/^(Рождение|Смерть|Брак|Погреб|Крещени|Иммигр|Проживан|Образован)/i;
/** The card tells the leading version. A version weaker than this stays in the investigation. */
const SHOWN_FROM=.3;
const PLACEHOLDER=/Źródło/;// the projection replaces internal source titles with a trilingual placeholder; such sources stay uncounted and unlinked
function Fact({f,data,labels,subject,language,own,open:openPaper}:{f:Row;data:Row;labels:Row;subject:string;language:Language;own:Paper[];open:(id:string)=>void}){
 const [open,setOpen]=useState(false);const long=(f.text||'').length>150;
 const tone=f.scope==='search'?'search':f.status;
 const pics=own.filter(x=>x.thumb&&(f.sources||[]).includes(x.id));
 const label=(f.label||'').replace(/\s*из (дерева|экспорта)$/i,'').replace(/^Память семьи$/i,'');const linked=(f.sources||[]).some((sid:string)=>{const s=data.sources[sid];return s&&!PLACEHOLDER.test(s.title||'')&&(s.asset||s.url)});
 return <article className={'fact '+tone}>
  {label&&<h4><i className={'tone '+tone} aria-hidden="true"/>{label}</h4>}
  <p className={open||!long?'':'clamp'}>{humanText(f.text,language)}</p>
  {open&&f.basis&&<p className="note">{translated(f.basis,language)}</p>}
  {pics.length>0&&<div className="fact-pics">{pics.slice(0,4).map(x=><button key={x.id} onClick={()=>openPaper(x.id)} aria-label={x.title}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={x.thumb} alt="" loading="lazy"/></button>)}</div>}
  {(long||f.basis||linked)&&<button className="more" onClick={()=>setOpen(!open)}>{open?labels.less:labels.more}</button>}
  {open&&<div className="source-links">{(f.sources||[]).map((sid:string)=>{const s=data.sources[sid];return s&&!PLACEHOLDER.test(s.title||'')?own.some(x=>x.id===sid)?<button className="link" key={sid} onClick={()=>openPaper(sid)}>{s.title||labels.source}</button>:<a key={sid} href={s.asset||s.url||undefined}>{s.title||labels.source}</a>:null})}</div>}
  {open&&feedbackEnabled()&&<details><summary>{labels.correctEvent}</summary><Feedback subject={subject+':fact:'+f.eventKey} language={language}/></details>}
 </article>
}
const COV_WORD:Record<string,string>={found:'covOutFound',read:'covRead','zero-controlled':'covOutZero','zero-uncontrolled':'covOutUnchecked',gap:'covOutGap',unrecorded:'covOutUnrecorded'};
/** "Where we looked": the host's private line on a card, told in plain words; the ledger itself stays in the investigation. */
function Coverage({c,labels,language}:{c:Row;labels:Row;language:Language}){
 const line=[`${labels.covLooked} ${c.searched} ${plural(c.searched,labels.covSources,language)}`,c.found>0?`${labels.covFound} ${c.found}`:''].filter(Boolean).join(' · ');
 return <details className="evidence coverage"><summary>{labels.covTitle}</summary><p>{line}</p>
  {c.sources?.length>0&&<ul className="cov-list">{c.sources.map((s:Row)=><li key={s.id}><b>{s.title}</b><small>{labels[COV_WORD[s.outcome]||'covOutUnrecorded']}</small></li>)}</ul>}
  {c.never?.length>0&&<p>{labels.covNever}: {c.never.map((n:Row)=>n.title).join(' · ')}</p>}
 </details>
}
/**
 * The card of one person. Order follows what a family reader wants first: who this is to me, the story with its
 * documents and documentary findings, then family memory, life dates and relatives. Historical grounds and
 * retired claims stay in the folded details.
 */
export default function PersonPanel({data,model,id,go,showFamily,labels,language,expanded,setExpanded,me,setMe,openFeed,papers,openPaper,papersOf}:{papers:Paper[];openPaper:(id:string,list:string[])=>void;papersOf:(id:string)=>void;data:Row;model:Model;id:string;go:(id:string)=>void;showFamily?:()=>void;labels:Row;language:Language;expanded:boolean;setExpanded:(v:boolean)=>void;me:string;setMe:(id:string)=>void;openFeed?:(id:string,step?:number)=>void}){
 const p=data.people[id];const info=model.info[id];const growth=info.growth;const [all,setAll]=useState(false);const [lb,setLb]=useState<number|null>(null);const [pick,setPick]=useState(false);const [meQuery,setMeQuery]=useState('');
 const root=useRef<HTMLElement>(null);
 // a new person starts at the top of the card, on the desktop column and in the phone sheet alike
 useEffect(()=>{setAll(false);setLb(null);setPick(false);setMeQuery('')},[id]);
 // the phone sheet keeps its scroll offset while folded, so the reset runs again when it opens
 useEffect(()=>{const el=root.current;if(el){el.scrollTop=0;const body=el.querySelector<HTMLElement>('.body');if(body)body.scrollTop=0}},[id,expanded]);
 // who is looking: relations are counted from that person; without a choice they are counted from the two home people
 const rel=me&&model.info[me]?model.relation(me,id):null;
 const kinWord=rel&&rel.kind!=='self'?kinshipTerm(rel,language)?.word:'';
 const askKin=kinWord&&(language==='ru'||language==='pl'?genitive(kinWord,language):kinWord);
 const reportedKin=(p.reportedKinship||[]).filter((k:Row)=>k.viewer===me).map((k:Row)=>translated(k.text,language));
 const meNeedle=meQuery.trim().toLocaleLowerCase();
 const meHits=meNeedle?Object.values(model.info).filter(i=>isPerson(i)&&(i.name+' '+i.short).toLocaleLowerCase().includes(meNeedle)).sort((a,b)=>(b.birth??0)-(a.birth??0)).slice(0,8):[];
 const documentary=(f:Row)=>(f.sources||[]).some((sid:string)=>['archive-record','home-paper','record','document','image'].includes(data.sources[sid]?.kind)||data.sources[sid]?.record&&data.sources[sid]?.kind!=='memory'&&data.sources[sid]?.kind!=='gedcom'&&data.sources[sid]?.kind!=='import');
 const weak=(f:Row)=>typeof f.weight==='number'&&f.weight<SHOWN_FROM;
 const facts:Row[]=useMemo(()=>(p.facts||[]).filter((f:Row,i:number,a:Row[])=>!weak(f)&&f.text!==info.fullName&&f.text!==p.name&&f.text!==p.namePresentation?.full&&a.findIndex(g=>g.text===f.text)===i).sort((a:Row,b:Row)=>Number(documentary(b))-Number(documentary(a))||Number(a.scope==='search')-Number(b.scope==='search')),[p,data]);
 const ORDER=['Рожд','Крещ','Образ','Брак','Иммигр','Прожив','Смерт','Погреб'];const rankLife=(f:Row)=>{const i=ORDER.findIndex(k=>(f.label||'').startsWith(k));return i<0?ORDER.length:i};
 const lifeFacts=facts.filter(f=>!f.detailOnly&&(f.eventType||LIFE.test(f.label||''))&&f.scope!=='search').sort((a,b)=>Number(documentary(b))-Number(documentary(a))||rankLife(a)-rankLife(b));const other=facts.filter(f=>!f.detailOnly&&!lifeFacts.includes(f));
 const found=other.filter(f=>documentary(f)||f.status==='verified');const memories=other.filter(f=>!found.includes(f));const details=facts.filter(f=>f.detailOnly);
 const dropped=useMemo(()=>weakOnlySources(p,SHOWN_FROM),[p]);
 // the person's own papers first; a paper that names somebody else and only mentions this person follows
 const own=useMemo(()=>{
  const stem=(pid:string)=>{const n=(model.info[pid]?.givenName||model.info[pid]?.short.split(' ')[0]||'').toLocaleLowerCase();return n.length>4?n.slice(0,-1):n};
  const names=(x:Paper,pid:string)=>{const k=stem(pid);return k.length>2&&x.title.toLocaleLowerCase().includes(k)};
  const rank=(x:Paper)=>names(x,id)?0:x.people.some(o=>o!==id&&names(x,o))?2:1;
  const mine=papers.filter(x=>x.people.includes(id));
  return pictured([0,1,2].flatMap(r=>mine.filter(x=>rank(x)===r)))},[papers,id,model]);const openOwn=(sid:string)=>openPaper(sid,own.map(x=>x.id));
 const photos:Doc[]=useMemo(()=>(p.media||[]).filter((m:Row)=>m.asset&&m.photo&&m.kind!=='photo-restoration'&&m.ours?.kind!=='photo-restoration')
  .sort((a:Row,b:Row)=>Number(a.type==='grave')-Number(b.type==='grave')).map((m:Row):Doc=>({sid:m.sid,title:m.title||'',reading:translated(m.description,language),asset:m.asset,photo:true,crop:region(m.crop)})),[p,language]);
 // A story may have a simple part first and details after a line of dashes; illustrations are period pictures, not family documents.
 const paired=(s:Row)=>s.kind==='photo-restoration'||s.ours?.kind==='photo-restoration';
 const restored=[...(p.illustrations||[]),...(p.media||[])].filter(paired);
 const pics:Doc[]=useMemo(()=>(p.illustrations||[]).filter((s:Row)=>s.asset&&!paired(s)).map((s:Row,i:number)=>({sid:'ill:'+i,title:[inLanguage(s.caption,language),s.credit].filter(Boolean).join(' · '),asset:s.asset,photo:true,href:s.url,hrefLabel:labels.storyPicSource})),[p,language,labels]);
 // the face that leads the card opens its photograph whole; a restored portrait opens with its original one tap away
 const portrait=info.portrait;
 const lead:Doc[]=portrait&&!photos.some(d=>d.sid===portrait.sid)?[{sid:portrait.sid,title:portrait.title,asset:portrait.asset,originalAsset:portrait.original,photo:true,crop:portrait.crop}]:[];
 const viewer=[...lead,...photos,...pics];
 const openFace=()=>setLb(Math.max(0,viewer.findIndex(d=>d.sid===portrait?.sid)));
 const face=(cls:string)=>portrait?<button className={'card-face '+cls} onClick={openFace} aria-label={labels.photos+': '+portrait.title}><Face key={portrait.asset} portrait={portrait} alt={info.short}/></button>:null;
 const known=[...found,...memories];const shown=all?known:known.slice(0,4);
 const {slots,extra}=model.parents(id);const parents=slots.filter(s=>s&&!s.gap&&!s.weak) as Slot[];const leads=slots.filter(s=>s&&(s.gap||s.weak)) as Slot[];const downs=model.descendantsBelow(id);
 // a possible ancestor across generations nobody has found yet: the recorded number or range of the missing ones
 const gapText=(s:Slot)=>{const lo=Number(s.link?.missing)||s.gap||0,hi=Number(s.link?.missing_max)||lo;return String(labels.lineGap||'{n}').replace('{n}',hi>lo?`${lo}–${hi}`:String(lo))};
 const linked=slots.filter(s=>s?.link&&translated(s.link.basis||s.link.text,language)) as Slot[];
 const identities:Row[]=p.probableIdentities||[];
 const possible=identities.filter(x=>data.presentationAliases?.[x.alias]===id);
 const sameAs=identities.filter(x=>x.basis);
 const spouses=model.spouses(id),kids=model.children(id),sibs=model.siblings(id),spouseLink=(s:string)=>model.spouseConnection(id,s),others=data.associations?.filter((a:Row)=>(a.from===id||a.to===id)&&a.type!=='sibling'&&a.type!=='spouse').map((a:Row)=>({id:a.from===id?a.to:a.from,label:a.label,status:a.status}))||[];
 const married=(p.names||[]).filter((n:Row)=>n.married_name).map((n:Row)=>n.married_name);
 const kin=model.kinship(id).map(k=>kinPhrase(k,labels,language));const {simple,more}=storyParts(storyText(p.story,language));
 const chip=(pid:string,hyp=false,hint='')=>{const i=model.info[pid];return isPerson(i)?<button key={pid} className={'chip'+(hyp?' hyp':'')} onClick={()=>go(pid)}><b className={i.unnamed?'unnamed':undefined}>{i.short}{i.maidenShown&&<small className="maiden" title={labels.maidenLabel+': '+i.maidenShown}> ({i.maidenShown})</small>}{i.story&&<i className="st-dot" title={labels.hasStory} aria-label={labels.hasStory}/>}</b>{(i.life||hint)&&<small>{[lifeLabel(i,labels,language),hint].filter(Boolean).join(' · ')}</small>}</button>:null};
 const group=(title:string,items:React.ReactNode[])=>items.some(Boolean)?<section className="group"><h3>{title}</h3><div className="chips">{items}</div></section>:null;
 // chapters of the historical feeds where this person appears: the first chapter of each feed that names them
 const feedHits=((data.feeds||[]) as Feed[]).map(f=>({feed:f,step:f.chapters.findIndex(c=>c.person===id||(c.people||[]).includes(id))})).filter(h=>h.step>=0);
 const tone=model.tone(id);const birthText=info.guess&&possible.some(m=>m.card?.birth)?'':info.birthText;
 const line=[lifeLabel({...info,birthText},labels,language),placeLabel(info,labels)].filter(Boolean).join(' · ');
 const paras=(t:string)=>t.split(/\n{2,}/).map((x,i)=><p key={i}>{x}</p>);
 // how we know: the confirmation, the combined sources behind a probable link, the card notes and the basis of the dates
 const evidenceSids=model.relationshipEvidence(id).filter(sid=>data.sources[sid]&&!PLACEHOLDER.test(data.sources[sid].title||''));
 const confirmation=info.confirmation&&info.confirmation.level!=='mention'?confirmationText(info.confirmation,language):'';
 const connection=translated(info.connectionNote,language),dateBasis=translated(info.dateBasis,language),birthGuess=guessBasis(info,model,language);
 // how a document spelled the name (the old orthography, the case of the act, Latin): with its document, in "More"
 const writtenNames=[...new Map((p.names||[]).filter((n:Row)=>DOCUMENT_NAME_TYPES.includes(n.type)&&typeof n.display==='string'&&n.display.trim()&&n.display.trim()!==info.fullName&&n.display.trim()!==info.short)
  .map((n:Row)=>[n.display.trim(),(n.provenance||[]).map((sid:string)=>data.sources[sid]?.title).filter((t:string)=>t&&!PLACEHOLDER.test(t))] as [string,string[]])).entries()];
 // what was told or read stays on record beside the reading the card tells; what the family declined is not told again
 const amended:Row[]=(p.amendments||[]).filter((a:Row)=>a.state!=='declined');
 const hasEvidence=!!(amended.length||confirmation||evidenceSids.length||connection||dateBasis||birthGuess||linked.length||sameAs.length||writtenNames.length);
 const incompleteName=!(p.names||[]).some((n:Row)=>n.given&&n.surname);
 return <aside ref={root} data-feedback-person={id} data-feedback-person-label={info.short} data-ask-kin={askKin||undefined} className={'panel'+(expanded?' open':'')} aria-live="polite">
  <div className={'panel-peek'+(portrait?' with-face':'')}>{face('peek-face')}<button className="peek" onClick={()=>setExpanded(!expanded)} aria-expanded={expanded}>
   <span className="grab" aria-hidden="true"/>
   {!portrait&&<span className={'av'+(tone?.kin?' line-kin':'')} style={tone?{background:tone.color}:undefined}>{info.short.slice(0,1)}</span>}
   <span className="who"><strong className={info.unnamed?'unnamed':undefined}>{info.short}<ConfirmationMark value={info.confirmation} language={language}/></strong>{p.disambiguator?.[language]&&<small className="disambiguator">{p.disambiguator[language]}</small>}{(line||info.note)&&<small>{line||info.note}</small>}</span>
   {(simple||own.length>0)&&<span className="peek-docs" aria-label={[simple?labels.story:'',own.length?labels.docs+' '+own.length:''].filter(Boolean).join(', ')}>{simple&&<i className="st-dot"/>}{own.length>0&&<>▣ {own.length}</>}</span>}
   <span className="chev" aria-hidden="true">{expanded?'▾':'▴'}</span>
  </button>{showFamily&&<button className="show-person-family" onClick={showFamily}>{labels.treeShowFamily}</button>}</div>
  <div className="body">
   {incompleteName&&feedbackEnabled()&&<section className="group ask"><Feedback subject={id} language={language} kind="name_person"/></section>}
   <header className={portrait?'with-face':undefined}>{face('header-face')}<h2 className={info.unnamed?'unnamed':undefined}>{info.short}<ConfirmationMark value={info.confirmation} language={language}/></h2>{p.disambiguator?.[language]&&<p className="note">{p.disambiguator[language]}</p>}{info.showMaiden&&info.maidenShown&&<p className="note maiden">{labels.maidenLabel+': '+info.maidenShown}</p>}{info.fullName!==info.short&&<p className="note">{labels.fullName}: {info.fullName}</p>}{info.alt&&<p className="note">{labels.variants}: {info.alt}</p>}{info.note&&line&&<p className="note">{info.note}</p>}{line&&<p className="life">{line}</p>}{married.filter((m:string)=>!info.short.includes(m)).map((m:string,i:number)=><p className="note" key={i}>{labels.married}: {m}</p>)}</header>
   {!simple&&typeof p.summary==='string'&&p.summary&&<p className="card-summary">{p.summary}</p>}
   {info.connector&&translated(info.connectorBasis,language)&&<p className="note connector-explanation">{translated(info.connectorBasis,language)}</p>}
   {showFamily&&<button className="show-person-family panel-family-action" onClick={showFamily}>{labels.treeShowFamily}</button>}
   {p.surnameDisplay?.written?.length>0&&<p className="note surname-written">{labels.writtenSurname}: {p.surnameDisplay.written.join(' · ')}</p>}
   {p.surnameDisplay?.origin==='derived-from-children'&&<p className="note surname-derived">{labels.surnameFromChildren} {(p.surnameDisplay.children||[]).map((pid:string)=>model.info[pid]?.short).filter(Boolean).join(', ')}.</p>}
   <div className="kin">{me&&model.info[me]?<>{reportedKin.length?<span>{reportedKin.join(' · ')}</span>:rel?<KinshipExplanation relation={rel} model={model} labels={labels} language={language}/>:null}</>
    :<>{kin.map((k,i)=><span key={i}>{k}</span>)}</>}
   </div>
   {restored.map((f:Row,i:number)=><FeedFigure key={'restored:'+id+':'+i} f={f as any} labels={labels} language={language}/>)}
   {simple&&<section className={'story'+(more?' layered':'')}>
    <h3 className="eyebrow"><i className="st-dot" aria-hidden="true"/>{labels.story}</h3>
    <div className="story-simple">{paras(simple)}</div>
    {pics.length>0&&<div className="story-pics">{pics.map((d,i)=><button key={d.sid} onClick={()=>setLb(lead.length+photos.length+i)}><figure>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={d.asset} alt={d.title} loading="lazy"/><figcaption>{d.title.split(' · ')[0]}</figcaption></figure></button>)}</div>}
    {more&&<details className="story-more"><summary>{labels.storyMore}</summary>{paras(more)}</details>}
    {feedHits.length>0&&<div className="feed-hits">{feedHits.map(h=><button key={h.feed.id+h.step} onClick={()=>openFeed?.(h.feed.id,h.step)}><small>{labels.feedIn}</small><b>{tr(h.feed.title,language)}</b><span>{tr(h.feed.chapters[h.step].year,language)} · {tr(h.feed.chapters[h.step].title,language)}</span></button>)}</div>}
   </section>}
   {connection&&info.connectionShort&&Object.keys(info.connectionShort).length>0&&<p className="connection-lead"><b>{labels.connection}</b><br/>{connection}</p>}
   {photos.length>0&&<section className="group card-photos"><h3>{labels.photos}</h3><div className="strip">{photos.map((d,i)=><button key={d.sid} className="thumb" onClick={()=>setLb(lead.length+i)}>{d.crop?<Face portrait={{sid:d.sid,asset:d.asset,title:d.title,crop:d.crop,subjects:1}} face={false} alt={d.title}/>:/* eslint-disable-next-line @next/next/no-img-element */<img src={d.asset} alt={d.title} loading="lazy"/>}<span>{d.title}</span></button>)}</div></section>}
   {own.length>0&&<section className="group card-papers"><h3>{labels.docs}</h3><div className="paper-grid">{own.slice(0,4).map(x=><PaperTile key={x.id} paper={x} open={()=>openOwn(x.id)}/>)}</div>{own.length>4&&<button className="wide-btn" onClick={()=>papersOf(id)}>{labels.papersAll}: {own.length}</button>}</section>}
   {(p.events||[]).filter((e:Row)=>(e.tag==='DEAT'||e.type==='death')&&e.cause&&!lifeFacts.some(f=>(f.eventType==='death'||f.label===labels.deathEvent)&&f.text?.includes(e.cause))).map((e:Row,k:number)=><section className="group" key={'cause'+k}><h3>{labels.deathEvent}</h3><p>{String(labels.deathCause).replace('{cause}',e.cause)}</p></section>)}
   {shown.length>0&&<section className="group"><h3>{labels.known}</h3>{shown.map((f:Row,i:number)=><Fact key={`${f.eventKey||'fact'}:${i}`} f={f} data={data} labels={labels} subject={id} language={language} own={own} open={openOwn}/>)}{known.length>4&&<button className="more wide" onClick={()=>setAll(!all)}>{all?labels.less:labels.showAll}</button>}</section>}
   {lifeFacts.length>0&&<section className="group"><h3>{labels.life}</h3><ul className="life-list">{lifeFacts.map((f,i)=><li key={i}><b>{f.label.replace(/\s*из дерева$/i,'')}</b><span>{lifeFactText(f.text,language)}{f.basis&&<details><summary>{labels.more}</summary><p className="note">{translated(f.basis,language)}</p></details>}{(f.sources||[]).filter((sid:string)=>own.some(x=>x.id===sid)).map((sid:string)=><button key={sid} className="link" onClick={()=>openOwn(sid)}>{labels.feedOpenDoc}</button>)}</span></li>)}</ul></section>}
   {possible.map(x=>{
    const card=x.card||{}, ids=new Set([...(card.papers||[]),...(card.media||[]).map((m:Row)=>m.sourceSid||m.sid||m.asset)]);
    const names=[...new Set([translated(x.name,language),...(card.names||[])].filter(Boolean))];
    const summary=translated(card.summary,language);
    const related=pictured(papers.filter(paper=>ids.has(paper.id))), openRelated=(sid:string)=>openPaper(sid,related.map(paper=>paper.id));
    const born=card.birth&&humanText(/^\d{4}$/.test(card.birth)?'ABT '+card.birth:card.birth,language);
    const dates=[born&&`${labels.born} ${born}`,card.death&&`${labels.deathEvent.toLowerCase()} ${humanText(card.death,language)}`].filter(Boolean).join(' · ');
    const milestones=(card.events||[]).map((e:Row)=>{
     const kind=e.type||({BAPTISM:'baptism',MARR:'marriage'} as Row)[e.tag];
     return [labels.placeRoles?.[kind],humanText(e.date,language),translated(e.place,language)].filter(Boolean).join(' ');
    }).filter(Boolean);
    return <section className="group possible-identity" key={x.alias}><h3>{labels.sameAs}</h3>
     {names.length>0&&<p>{names.join(' · ')}</p>}
     {summary&&<div>{paras(summary)}</div>}
     {dates&&<p>{dates}</p>}
     {milestones.map((text:string,i:number)=><p key={i}>{text}</p>)}
     {related.length>0&&<div className="paper-grid">{related.map(paper=><PaperTile key={paper.id} paper={paper} open={()=>openRelated(paper.id)}/>)}</div>}
     {card.facts?.length>0&&<details><summary>{labels.more}</summary>{card.facts.map((f:Row,i:number)=><Fact key={i} f={f} data={data} labels={labels} subject={x.alias} language={language} own={related} open={openRelated}/>)}</details>}
    </section>;
   })}
   {group(labels.parents,parents.map(s=>chip(s.id,model.connectionLevel(s)===3)))}
   {group(labels.lineLeadsTo,leads.filter(s=>!s.weak).map(s=>chip(s.id,model.connectionLevel(s)===3,gapText(s))))}
   <SecondWay model={model} id={id} labels={labels} go={go}/>
   {group(labels.lineMaybe,leads.filter(s=>s.weak).map(s=>chip(s.id,true,s.gap?gapText(s):'')))}
   {group(labels.lineDown,downs.map(d=>chip(d.id,model.connectionLevel(d.slot)>1,d.slot.gap?gapText(d.slot):'')))}
   {group(labels.spouses,spouses.map(s=>chip(s,model.connectionLevel(spouseLink(s))===3)))}
   {group(labels.children,kids.map(k=>chip(k)))}
   {group(labels.siblings,sibs.map(s=>chip(s)))}
   {group(labels.otherVersions,extra.map(s=>chip(s.id,model.connectionLevel(s)===3)))}
   {group(labels.otherLinks,others.map((o:Row)=>chip(o.id,o.status==='hypothesis',o.label)))}
   {(hasEvidence||p.coverage?.searched>0||details.length>0||p.retiredFacts?.length>0)&&<details className="evidence card-more"><summary>{labels.more}</summary>
    {hasEvidence&&<section><h4>{labels.evidence}</h4>
    {confirmation&&<p>{confirmation}</p>}
    {writtenNames.length>0&&<p className="written-names"><b>{labels.writtenName}</b>{writtenNames.map(([name,titles])=><span key={name}><br/>{name}{titles.length>0&&<small> · {titles.join(' · ')}</small>}</span>)}</p>}
    {evidenceSids.length>0&&<p>{labels.evidenceBy} · {evidenceSids.length} {plural(evidenceSids.length,labels.sourcesCount,language)}:{' '}{evidenceSids.map((sid,i)=>{const source=data.sources[sid];return <span key={sid}>{i>0?' · ':''}{source.asset||source.url?<a href={source.asset||source.url} target="_blank" rel="noreferrer">{source.title}</a>:source.title}</span>})}</p>}
    {connection&&<p><b>{labels.connection}</b><br/>{connection}</p>}
    {linked.map(s=><p key={'link:'+s.id}><b>{s.main&&s.gap?labels.mainLine:s.main?labels.mainLine+' · '+labels.assumption:s.weak?labels.lineMaybe:s.gap?labels.lineLeadsTo:labels.assumption}: {model.info[s.id]?.short}</b><br/>{translated(s.link!.basis||s.link!.text,language)}</p>)}
    {amended.map((a:Row)=><p className="amendment" key={'amend:'+a.id}><b>{a.origin==='record'?labels.amendRead:labels.amendTold}</b><br/>{translated(a.original,language)}<br/><b>{a.state==='confirmed'?labels.amendYes:labels.amendThink}</b><br/>{[['birth','death'].includes(a.field)?lifeFactText(translated(a.value,language),language):translated(a.value,language),translated(a.basis,language)].filter(Boolean).map(x=>String(x).replace(/[.]$/,'')).join('. ')}</p>)}
    {sameAs.map((x:Row)=><p key={'same:'+x.alias}><b>{labels.sameAs}: {translated(x.name,language)}</b><br/>{translated(x.basis,language)}</p>)}
    {dateBasis&&<p><b>{labels.dateBasis}</b><br/>{dateBasis}</p>}
    {birthGuess&&<p className="birth-guess"><b>{labels.birthGuess}</b><br/>{birthGuess}</p>}
    </section>}
    {details.map((f:Row,i:number)=><Fact key={'detail'+i} f={f} data={data} labels={labels} subject={id} language={language} own={own} open={openOwn}/>)}{(p.retiredFacts||[]).map((f:Row,i:number)=><article className="fact" key={'retired'+i}><p><s>{humanText(f.text,language)}</s></p>{f.retiredBecause&&<p className="note">{translated(f.retiredBecause,language)}</p>}</article>)}
    {p.coverage?.searched>0&&<Coverage c={p.coverage} labels={labels} language={language}/>}
   </details>}
   <div className="kin kin-viewer"><small>{me&&model.info[me]&&<>{labels.meFrom}: {model.info[me].short} · </>}<button className="link" onClick={()=>setPick(!pick)}>{labels.whoLooks}</button>{me&&model.info[me]&&<> · <button className="link" onClick={()=>setMe('')}>{labels.meReset}</button></>}</small>
    {pick&&<div className="me-pick"><p>{labels.meHint}</p><input autoFocus aria-label={labels.meSearch} placeholder={labels.meSearch} value={meQuery} onChange={e=>setMeQuery(e.target.value)}/>{meHits.map(i=><button key={i.id} className="chip" onClick={()=>{setMe(i.id);setPick(false);setMeQuery('')}}><b className={i.unnamed?'unnamed':undefined}>{i.short}</b>{(data.people[i.id]?.disambiguator?.[language]||i.life)&&<small>{[data.people[i.id]?.disambiguator?.[language],lifeLabel(i,labels,language)].filter(Boolean).join(' · ')}</small>}</button>)}</div>}
   </div>
   {feedbackEnabled()&&<section className="group ask"><p>{labels.know}</p><Feedback subject={id} language={language}/></section>}
  </div>
  {/* the viewer lives on the body: inside the phone sheet it would be clipped and sit under the tab bar */}
  {lb!==null&&typeof document!=='undefined'&&createPortal(<Lightbox docs={viewer} index={lb} setIndex={setLb} onClose={()=>setLb(null)} labels={labels}/>,document.body)}
 </aside>
}
