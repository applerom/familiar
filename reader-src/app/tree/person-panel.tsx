'use client';
import {feedbackEnabled} from '../reader-profile';
import {useEffect,useMemo,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {humanText,kinPhrase,relationPhrase,lifeLabel,guessBasis,placeLabel,lifeFactText,translated,type Model,type Row,type Slot} from './model';
import {KinshipExplanation} from '../kinship-words';
import Feedback from './feedback';
import ConfirmationMark,{confirmationText} from './confirmation';
import Lightbox,{type Doc} from './lightbox';
import {storyParts,storyText} from '../stories';
import {FeedFigure,tr,type Feed} from '../feed';
import {plural,type Language} from '../i18n';
const LIFE=/^(Рождение|Смерть|Брак|Погреб|Крещени|Иммигр|Проживан|Образован)/i;
/** The card tells the leading version. A version weaker than this stays in the investigation. */
const SHOWN_FROM=.3;
const PLACEHOLDER=/Źródło/;// the projection replaces internal source titles with a trilingual placeholder; such sources stay uncounted and unlinked
function Fact({f,data,labels,subject,language,docs,open:openDoc}:{f:Row;data:Row;labels:Row;subject:string;language:Language;docs:Doc[];open:(i:number)=>void}){
 const [open,setOpen]=useState(false);const long=(f.text||'').length>150;
 const tone=f.scope==='search'?'search':f.status;
 const pics=(f.sources||[]).map((sid:string)=>docs.findIndex(d=>(d.sourceSid||d.sid)===sid)).filter((i:number)=>i>=0);
 const label=(f.label||'').replace(/\s*из (дерева|экспорта)$/i,'');const badge=f.testimony&&label.toLocaleLowerCase()!==labels.familyFirm?.toLocaleLowerCase()?labels.familyFirm:'';
 return <article className={'fact '+tone}>
  <h4><i className={'tone '+tone} aria-hidden="true"/>{label}{badge&&<small>{badge}</small>}</h4>
  <p className={open||!long?'':'clamp'}>{humanText(f.text,language)}</p>
  {open&&f.basis&&<p className="note">{translated(f.basis,language)}</p>}
  {pics.length>0&&<div className="fact-pics">{pics.slice(0,4).map((i:number)=>{const d=docs[i];return <button key={d.sid} onClick={()=>openDoc(i)} title={d.title}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={d.asset} alt={d.title} loading="lazy"/></button>})}</div>}
  {(long||f.basis||f.sources?.length>0)&&<button className="more" onClick={()=>setOpen(!open)}>{open?labels.less:labels.more}</button>}
  {open&&<div className="source-links">{(f.sources||[]).map((sid:string)=>{const s=data.sources[sid];return s&&!PLACEHOLDER.test(s.title||'')?<a key={sid} href={s.asset||s.url||undefined} target="_blank" rel="noreferrer">{s.title||labels.source}{!s.asset&&!s.url?' · '+labels.localArchive:''}</a>:null})}</div>}
  {open&&feedbackEnabled()&&<details><summary>{labels.correctEvent}</summary><Feedback subject={subject+':fact:'+f.eventKey} language={language}/></details>}
 </article>
}
const COV_MARK:Record<string,[string,string]>={found:['R','covOutFound'],read:['D','covRead'],'zero-controlled':['○','covOutZero'],'zero-uncontrolled':['?','covOutUnchecked'],gap:['⊘','covOutGap'],unrecorded:['…','covOutUnrecorded']};
/** "Where we looked": host-private display of the search coverage matrix; the public graph never carries it. */
function Coverage({c,labels,language}:{c:Row;labels:Row;language:Language}){
 const line=c.searched>0?[`${labels.covLooked} ${c.searched} ${plural(c.searched,labels.covSources,language)}`,c.found>0?`${labels.covFound} ${c.found}`:'',c.identified>0?`${labels.covIdentified}: ${c.identified}`:'',c.recheck>0?`${labels.covRecheck}: ${c.recheck}`:''].filter(Boolean).join(' · '):labels.covNone;
 const never:Row[]=c.never||[];
 return <details className="evidence coverage"><summary>{labels.covTitle}<span className="cov-line">{line}</span></summary>
  {c.sources?.length>0&&<ul className="cov-list">{c.sources.map((s:Row)=>{const [mark,word]=COV_MARK[s.outcome]||COV_MARK.gap;
   return <li key={s.id} className={'cov-'+s.outcome}>
    <span className="cov-mark" title={labels[word]} aria-label={labels[word]}>{mark}{s.identified&&<small title={labels.covIdentified}>✓</small>}</span>
    <span className="cov-what"><b>{s.title}</b>{s.surnameSearch&&<small>{labels.covSurname}</small>}{s.placeSearch&&<small>{labels.covPlace}</small>}{s.recordRead&&<small>{labels.covRead}</small>}{s.forms?.length>0&&<small>{s.forms.join(' · ')}</small>}{s.missingForms?.length>0?<small>{labels.covMissing}: {s.missingForms.join(' · ')}{s.missingMore>0&&` · ${labels.covMore} ${s.missingMore}`}</small>:!s.planComplete&&<small>{labels.covIncomplete}</small>}</span>
    <span className="cov-when">{s.last&&<small>{s.last}</small>}<i className="cov-dots" title={s.strength>0?`${labels.covStrength}: ${s.strength}/4`:labels.covStrengthUnknown}>{[1,2,3,4].map(n=><u key={n} className={n<=s.strength?'on':''}/>)}</i></span>
   </li>})}</ul>}
  {never.length>0&&<p className="cov-never"><b>{labels.covNever}:</b> {never.map(n=>n.title).join(' · ')}{c.neverMore>0&&` · ${labels.covMore} ${c.neverMore}`}</p>}
 </details>
}
/**
 * The card of one person. Order follows what a family reader wants first: who this is to me, the story with its
 * documents and documentary findings, then family memory, life dates and relatives. Historical grounds and
 * retired claims stay in the folded details.
 */
export default function PersonPanel({data,model,id,go,showFamily,labels,language,expanded,setExpanded,me,setMe,openFeed}:{data:Row;model:Model;id:string;go:(id:string)=>void;showFamily?:()=>void;labels:Row;language:Language;expanded:boolean;setExpanded:(v:boolean)=>void;me:string;setMe:(id:string)=>void;openFeed?:(id:string,step?:number)=>void}){
 const p=data.people[id];const info=model.info[id];const growth=info.growth;const [all,setAll]=useState(false);const [lb,setLb]=useState<number|null>(null);const [pick,setPick]=useState(false);const [meQuery,setMeQuery]=useState('');
 const root=useRef<HTMLElement>(null);
 // a new person starts at the top of the card, on the desktop column and in the phone sheet alike
 useEffect(()=>{setAll(false);setLb(null);setPick(false);setMeQuery('')},[id]);
 // the phone sheet keeps its scroll offset while folded, so the reset runs again when it opens
 useEffect(()=>{const el=root.current;if(el){el.scrollTop=0;const body=el.querySelector<HTMLElement>('.body');if(body)body.scrollTop=0}},[id,expanded]);
 // who is looking: relations are counted from that person; without a choice they are counted from the two home people
 const rel=me&&model.info[me]?model.relation(me,id):null;
 const reportedKin=(p.reportedKinship||[]).filter((k:Row)=>k.viewer===me).map((k:Row)=>translated(k.text,language));
 const meNeedle=meQuery.trim().toLocaleLowerCase();
 const meHits=meNeedle?Object.values(model.info).filter(i=>!i.placeholder&&(i.name+' '+i.short).toLocaleLowerCase().includes(meNeedle)).sort((a,b)=>(b.birth??0)-(a.birth??0)).slice(0,8):[];
 const documentary=(f:Row)=>(f.sources||[]).some((sid:string)=>['archive-record','home-paper','record','document','image'].includes(data.sources[sid]?.kind)||data.sources[sid]?.record&&data.sources[sid]?.kind!=='memory'&&data.sources[sid]?.kind!=='gedcom'&&data.sources[sid]?.kind!=='import');
 const weak=(f:Row)=>typeof f.weight==='number'&&f.weight<SHOWN_FROM;
 const facts:Row[]=useMemo(()=>(p.facts||[]).filter((f:Row,i:number,a:Row[])=>!weak(f)&&f.text!==info.fullName&&a.findIndex(g=>g.text===f.text)===i).sort((a:Row,b:Row)=>Number(documentary(b))-Number(documentary(a))||Number(a.scope==='search')-Number(b.scope==='search')),[p,data]);
 const ORDER=['Рожд','Крещ','Образ','Брак','Иммигр','Прожив','Смерт','Погреб'];const rankLife=(f:Row)=>{const i=ORDER.findIndex(k=>(f.label||'').startsWith(k));return i<0?ORDER.length:i};
 const lifeFacts=facts.filter(f=>!f.detailOnly&&(f.eventType||LIFE.test(f.label||''))&&f.scope!=='search').sort((a,b)=>Number(documentary(b))-Number(documentary(a))||rankLife(a)-rankLife(b));const other=facts.filter(f=>!f.detailOnly&&!lifeFacts.includes(f));
 const found=other.filter(f=>documentary(f)||f.status==='verified');const memories=other.filter(f=>!found.includes(f));const details=facts.filter(f=>f.detailOnly);
 // Explicitly selected direct mentions only. A research citation is not a gallery item.
 // Order: portraits, then the person's own register entries by year (the record itself first, the whole page beside it),
 // then documents that merely name the person, then gravestones.
 const dropped=useMemo(()=>{const kept=new Set<string>([...(p.names||[]),...(p.events||[]),...(p.facts||[]).filter((f:Row)=>!weak(f))].flatMap((r:Row)=>[...(r.sources||[]),...(r.provenance||[])]));return new Set<string>((p.facts||[]).filter(weak).flatMap((f:Row)=>f.sources||[]).filter((sid:string)=>!kept.has(sid)))},[p]);
 const docs:Doc[]=useMemo(()=>{const lifeSids=new Set(lifeFacts.flatMap(f=>f.sources||[]));const year=(t:string)=>Number((/\b(1[5-9]\d\d|20\d\d)\b/.exec(t)||[])[1])||9999;
  const rank=(s:Row)=>s.photo?(s.type==='grave'||/памятник|могил|надгроб|grave|nagrob/i.test(s.title||'')?3:0):(s.mentionRole&&!['child','groom','bride','deceased','self'].includes(s.mentionRole))||(!s.mentionRole&&!lifeSids.has(s.sid))?2:1;
  const own=[...(p.media||[])].filter((s:Row)=>s.asset&&s.kind!=='photo-restoration'&&s.ours?.kind!=='photo-restoration').sort((a:Row,b:Row)=>rank(a)-rank(b)||year(a.title||'')-year(b.title||'')).flatMap((s:Row):Doc[]=>{
   const base={sid:s.sid,sourceSid:s.sourceSid||s.sid,title:[s.title,data.sources[s.sourceSid||s.sid]?.title].filter((x,i,a)=>x&&a.indexOf(x)===i).join(' · '),reading:translated(s.description,language),asset:s.asset,originalAsset:s.originalAsset,photo:s.photo===true,kind:rank(s)};
   if(!base.photo&&s.originalAsset&&s.originalAsset!==s.asset)return [
    {...base,sid:s.sid+':detail',view:'detail',title:base.title+' · '+labels.detail},
    {...base,sid:s.sid+':full',asset:s.originalAsset,view:'fullPage',title:base.title+' · '+labels.fullPage}
   ];
   return [base];
  });
  const covered=new Set(own.map(d=>d.sourceSid));const shot=(s:Row)=>s?.image||(/\.(png|jpe?g|webp|gif)$/i.test(s?.asset||'')?s.asset:'');
  return [...own,...growth.documents.filter(sid=>shot(data.sources[sid])&&!covered.has(sid)&&!dropped.has(sid)).map((sid):Doc=>{const s=data.sources[sid];return {sid,sourceSid:sid,title:s.title||labels.source,asset:shot(s),photo:false,kind:1,...(s.asset&&s.asset!==shot(s)?{href:s.asset,hrefLabel:labels.feedOpenDoc}:{})}})]},[p,labels,lifeFacts]);
 // A story may have a simple part first and details after a line of dashes; illustrations are period pictures, not family documents.
 const paired=(s:Row)=>s.kind==='photo-restoration'||s.ours?.kind==='photo-restoration';
 const restored=[...(p.illustrations||[]),...(p.media||[])].filter(paired);
 const pics:Doc[]=useMemo(()=>(p.illustrations||[]).filter((s:Row)=>s.asset&&!paired(s)).map((s:Row,i:number)=>({sid:'ill:'+i,title:[s.caption?.[language]||s.caption?.en||s.caption?.ru||s.caption,s.credit].filter(Boolean).join(' · '),asset:s.asset,photo:true,href:s.url,hrefLabel:labels.storyPicSource})),[p,language,labels]);
 const viewer=[...docs,...pics];
 const known=[...found,...memories];const shown=all?known:known.slice(0,4);
 const {slots,extra}=model.parents(id);const parents=slots.filter(Boolean) as Slot[];
 const spouses=model.spouses(id),kids=model.children(id),sibs=model.siblings(id),spouseLink=(s:string)=>model.spouseConnection(id,s),others=data.associations?.filter((a:Row)=>(a.from===id||a.to===id)&&a.type!=='sibling'&&a.type!=='spouse').map((a:Row)=>({id:a.from===id?a.to:a.from,label:a.label,status:a.status}))||[];
 const married=(p.names||[]).filter((n:Row)=>n.married_name).map((n:Row)=>n.married_name);
 const kin=model.kinship(id).map(k=>kinPhrase(k,labels,language));const {simple,more}=storyParts(storyText(p.story,language));
 const chip=(pid:string,hyp=false,hint='')=>{const i=model.info[pid];return i&&!i.placeholder?<button key={pid} className={'chip'+(hyp?' hyp':'')} onClick={()=>go(pid)}><b className={i.unnamed?'unnamed':undefined}>{i.short}{i.maidenShown&&<small className="maiden" title={labels.maidenLabel+': '+i.maidenShown}> ({i.maidenShown})</small>}{i.story&&<i className="st-dot" title={labels.hasStory} aria-label={labels.hasStory}/>}</b>{(i.life||hint)&&<small>{[lifeLabel(i,labels,language),hint].filter(Boolean).join(' · ')}</small>}</button>:null};
 const group=(title:string,items:React.ReactNode[])=>items.some(Boolean)?<section className="group"><h3>{title}</h3><div className="chips">{items}</div></section>:null;
 // chapters of the historical feeds where this person appears: the first chapter of each feed that names them
 const feedHits=((data.feeds||[]) as Feed[]).map(f=>({feed:f,step:f.chapters.findIndex(c=>c.person===id||(c.people||[]).includes(id))})).filter(h=>h.step>=0);
 const tone=model.tone(id);const line=[lifeLabel(info,labels,language),placeLabel(info,labels)].filter(Boolean).join(' · ');
 const paras=(t:string)=>t.split(/\n{2,}/).map((x,i)=><p key={i}>{x}</p>);
 // how we know: the confirmation, the combined sources behind a probable link, the card notes and the basis of the dates
 const evidenceSids=model.relationshipEvidence(id).filter(sid=>data.sources[sid]&&!PLACEHOLDER.test(data.sources[sid].title||''));
 const confirmation=info.confirmation&&info.confirmation.level!=='mention'?confirmationText(info.confirmation,language):'';
 const connection=translated(info.connectionNote,language),dateBasis=translated(info.dateBasis,language),birthGuess=guessBasis(info,model,language);
 const hasEvidence=!!(confirmation||evidenceSids.length||connection||dateBasis||birthGuess);
 const incompleteName=!(p.names||[]).some((n:Row)=>n.given&&n.surname);
 return <aside ref={root} data-feedback-person={id} data-feedback-person-label={info.short} className={'panel'+(expanded?' open':'')} aria-live="polite">
  <div className="panel-peek"><button className="peek" onClick={()=>setExpanded(!expanded)} aria-expanded={expanded}>
   <span className="grab" aria-hidden="true"/>
   <span className={'av'+(tone?.kin?' line-kin':'')} style={tone?{background:tone.color}:undefined}>{info.short.slice(0,1)}</span>
   <span className="who"><strong className={info.unnamed?'unnamed':undefined}>{info.short}<ConfirmationMark value={info.confirmation} language={language}/></strong>{p.disambiguator?.[language]&&<small className="disambiguator">{p.disambiguator[language]}</small>}{(line||info.note)&&<small>{line||info.note}</small>}</span>
   {(simple||docs.length>0)&&<span className="peek-docs" aria-label={[simple?labels.story:'',docs.length?labels.docs+' '+docs.length:''].filter(Boolean).join(', ')}>{simple&&<i className="st-dot"/>}{docs.length>0&&<>▣ {docs.length}</>}</span>}
   <span className="chev" aria-hidden="true">{expanded?'▾':'▴'}</span>
  </button>{showFamily&&<button className="show-person-family" onClick={showFamily}>{labels.treeShowFamily}</button>}</div>
  <div className="body">
   {incompleteName&&feedbackEnabled()&&<section className="group ask"><Feedback subject={id} language={language} kind="name_person"/></section>}
   <header><h2 className={info.unnamed?'unnamed':undefined}>{info.short}<ConfirmationMark value={info.confirmation} language={language}/></h2>{p.disambiguator?.[language]&&<p className="note">{p.disambiguator[language]}</p>}{info.showMaiden&&(info.maidenShown||!info.maidenSurname)&&<p className="note maiden">{info.maidenShown?labels.maidenLabel+': '+info.maidenShown:labels.maidenUnknownLong}</p>}{info.fullName!==info.short&&<p className="note">{labels.fullName}: {info.fullName}</p>}{info.alt&&<p className="note">{labels.variants}: {info.alt}</p>}{info.note&&line&&<p className="note">{info.note}</p>}{line&&<p className="life">{line}</p>}{married.filter((m:string)=>!info.short.includes(m)).map((m:string,i:number)=><p className="note" key={i}>{labels.married}: {m}</p>)}</header>
   {!simple&&typeof p.summary==='string'&&p.summary&&<p className="card-summary">{p.summary}</p>}
   {info.connector&&translated(info.connectorBasis,language)&&<p className="note connector-explanation">{translated(info.connectorBasis,language)}</p>}
   {showFamily&&<button className="show-person-family panel-family-action" onClick={showFamily}>{labels.treeShowFamily}</button>}
   {p.surnameDisplay?.written?.length>0&&<p className="note surname-written">{labels.writtenSurname}: {p.surnameDisplay.written.join(' · ')}</p>}
   {p.surnameDisplay?.origin==='derived-from-children'&&<p className="note surname-derived">{labels.surnameFromChildren} {(p.surnameDisplay.children||[]).map((pid:string)=>model.info[pid]?.short).filter(Boolean).join(', ')}.</p>}
   <div className="kin">{me&&model.info[me]?<>{reportedKin.length?<span>{reportedKin.join(' · ')}</span>:rel?<KinshipExplanation relation={rel} model={model} labels={labels} language={language}/>:<span>{labels.meNone}</span>}{reportedKin.length>0&&rel&&<><small>{labels.graphKinship}:</small><KinshipExplanation relation={rel} model={model} labels={labels} language={language}/></>}</>
    :<>{kin.map((k,i)=><span key={i}>{k}</span>)}</>}
   </div>
   {restored.map((f:Row,i:number)=><FeedFigure key={'restored:'+id+':'+i} f={f as any} labels={labels} language={language}/>)}
   {simple&&<section className={'story'+(more?' layered':'')}>
    <h3 className="eyebrow"><i className="st-dot" aria-hidden="true"/>{labels.story}</h3>
    <div className="story-simple">{paras(simple)}</div>
    {pics.length>0&&<div className="story-pics">{pics.map((d,i)=><button key={d.sid} onClick={()=>setLb(docs.length+i)}><figure>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={d.asset} alt={d.title} loading="lazy"/><figcaption>{d.title.split(' · ')[0]}</figcaption></figure></button>)}</div>}
    {more&&<details className="story-more"><summary>{labels.storyMore}</summary>{paras(more)}</details>}
    {feedHits.length>0&&<div className="feed-hits">{feedHits.map(h=><button key={h.feed.id+h.step} onClick={()=>openFeed?.(h.feed.id,h.step)}><small>{labels.feedIn}</small><b>{tr(h.feed.title,language)}</b><span>{h.feed.chapters[h.step].year} · {tr(h.feed.chapters[h.step].title,language)}</span></button>)}</div>}
   </section>}
   {connection&&info.connectionShort&&Object.keys(info.connectionShort).length>0&&<p className="connection-lead"><b>{labels.connection}</b><br/>{connection}</p>}
   {(docs.length>0||growth.documents.some(sid=>!dropped.has(sid)))&&<section className="group"><h3>{labels.docs}</h3><div className="strip">{docs.map((d,i)=><button key={d.sid} className={'thumb'+(d.view==='detail'?' record':'')} onClick={()=>setLb(i)}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={d.asset} alt={d.title} loading="lazy"/><i>{d.view?labels[d.view]:d.kind===3?labels.docGrave:d.kind===2?labels.docMention:d.photo?labels.docPhoto:labels.original}</i><span>{d.title}</span></button>)}</div>{growth.documents.filter(sid=>!dropped.has(sid)&&!docs.some(d=>d.sourceSid===sid||d.asset===data.sources[sid]?.asset)).map(sid=>{const s=data.sources[sid];return <p className="note" key={sid}>{s.asset?<a href={s.asset} target="_blank" rel="noreferrer">{s.title||labels.source} ↗</a>:s.title||labels.source}</p>})}</section>}
   {(p.events||[]).filter((e:Row)=>(e.tag==='DEAT'||e.type==='death')&&e.cause&&!lifeFacts.some(f=>(f.eventType==='death'||f.label===labels.deathEvent)&&f.text?.includes(e.cause))).map((e:Row,k:number)=><section className="group" key={'cause'+k}><h3>{labels.deathEvent}</h3><p>{String(labels.deathCause).replace('{cause}',e.cause)}</p></section>)}
   {shown.length>0&&<section className="group"><h3>{labels.known}</h3>{shown.map((f:Row,i:number)=><Fact key={`${f.eventKey||'fact'}:${i}`} f={f} data={data} labels={labels} subject={id} language={language} docs={docs} open={setLb}/>)}{known.length>4&&<button className="more wide" onClick={()=>setAll(!all)}>{all?labels.less:labels.showAll}</button>}</section>}
   {lifeFacts.length>0&&<section className="group"><h3>{labels.life}</h3><ul className="life-list">{lifeFacts.map((f,i)=><li key={i}><b>{f.label.replace(/\s*из дерева$/i,'')}</b><span>{lifeFactText(f.text,language)}{f.testimony&&<small className="note"> · {labels.familyFirm}</small>}{f.basis&&<details><summary>{labels.more}</summary><p className="note">{translated(f.basis,language)}</p></details>}{(f.sources||[]).map((sid:string)=>{const s=data.sources[sid];return s?.asset?<a key={sid} className="source-links" href={s.asset} target="_blank" rel="noreferrer">{labels.feedFullDoc} ↗</a>:null})}{feedbackEnabled()&&<details><summary>{labels.correctEvent}</summary><Feedback subject={id+':fact:'+f.eventKey} language={language}/></details>}</span></li>)}</ul></section>}
   {group(labels.parents,parents.map(s=>chip(s.id,model.connectionLevel(s)===3)))}
   {group(labels.spouses,spouses.map(s=>chip(s,model.connectionLevel(spouseLink(s))===3)))}
   {group(labels.children,kids.map(k=>chip(k)))}
   {group(labels.siblings,sibs.map(s=>chip(s)))}
   {group(labels.otherVersions,extra.map(s=>chip(s.id,model.connectionLevel(s)===3)))}
   {group(labels.otherLinks,others.map((o:Row)=>chip(o.id,o.status==='hypothesis',o.label)))}
   {(hasEvidence||p.coverage||details.length>0||p.retiredFacts?.length>0)&&<details className="evidence card-more"><summary>{labels.more}</summary>
    {hasEvidence&&<section><h4>{labels.evidence}</h4>
    {confirmation&&<p>{confirmation}</p>}
    {evidenceSids.length>0&&<p>{labels.evidenceBy} · {evidenceSids.length} {plural(evidenceSids.length,labels.sourcesCount,language)}:{' '}{evidenceSids.map((sid,i)=>{const source=data.sources[sid];return <span key={sid}>{i>0?' · ':''}{source.asset||source.url?<a href={source.asset||source.url} target="_blank" rel="noreferrer">{source.title}</a>:source.title}</span>})}</p>}
    {connection&&<p><b>{labels.connection}</b><br/>{connection}</p>}
    {dateBasis&&<p><b>{labels.dateBasis}</b><br/>{dateBasis}</p>}
    {birthGuess&&<p className="birth-guess"><b>{labels.birthGuess}</b><br/>{birthGuess}</p>}
    </section>}
    {details.map((f:Row,i:number)=><Fact key={'detail'+i} f={f} data={data} labels={labels} subject={id} language={language} docs={docs} open={setLb}/>)}{(p.retiredFacts||[]).map((f:Row,i:number)=><article className="fact" key={'retired'+i}><p><s>{humanText(f.text,language)}</s></p>{f.retiredBecause&&<p className="note">{translated(f.retiredBecause,language)}</p>}</article>)}
    {p.coverage&&<Coverage c={p.coverage} labels={labels} language={language}/>}
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
