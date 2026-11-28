'use client';
import {readerStorage,profile,inLanguage} from './reader-profile';
import {useEffect,useRef,useState} from 'react';
import {isPerson,lifeLabel,relationPhrase,type Model,type Relation,type Row} from './tree/model';
import {kinNote} from './kinship-words';
import Feedback from './tree/feedback';
import {plural,type Language} from './i18n';
import LanguagePicker from './language-picker';
import {ChestChip,GameCard,PlayFeed,SpotFrame,type Offer,type Pano} from './play';
/** A historical feed: a chain of short chapters, each with a year, a period picture, a child-first text and optional details,
 *  a person of the tree, a document crop and links to archival films. Editorial content from `family-edition.json` (`feeds`). */
/** `kind` tells the reader how to frame the chapter: `version` — a scene restored without a document (no label is shown: SCENE-2, 3.11.2026); `truth` — what the documents
 *  really say; `visit` — places one can see today (with `places`); `famous` — a hook onto something well known; `fork` — two versions side by side
 *  (`variants`); `surname` — the origin of a family name. A plain chapter has no kind. */
export type ChapterKind='version'|'truth'|'visit'|'famous'|'fork'|'surname';
/** `kind:'ours'` marks a drawing made for the feed ("наша версия": our people, or the paper the text speaks of, drawn after a real one) — never
 *  a document or a portrait. `ours` pairs a real period picture with such a drawing: the page opens on the drawing and the reader switches
 *  «Наша версия» / «Как было». No badge on the picture (the author, 31.10.2026: it distracts from the story); the credit says it under «Подробнее». */
type RestorationRecipe={version:number;model:string;date:string;prompt:string;invented:string[];comparison:Record<string,number>;original_asset:string;crop?:number[];original_sha256:string;sha256:string};
type RestorationVersion={id:string;label?:Row;asset:string;caption:Row;disclosure:Row;recipe:RestorationRecipe};
export type Picture={asset:string;caption?:Row;disclosure?:Row;credit?:string;url?:string;license?:string;kind?:'ours'|'photo-treatment'|'photo-restoration';primary?:string;versions?:RestorationVersion[];ours?:Picture;orig?:string|Picture;spots?:Spot[];pano?:Pano;small?:boolean};
/** A thing on a picture (play layer, 2.11.2026, `scripts/feed-play.py`): a box in percent of the picture from the top left, its name and two lines
 *  on why it is here; `kids` replaces `text` in the children's mode; `find` is the task of the «Найди» game. */
export type Spot={x:number;y:number;w:number;h:number;label:Row;text:Row;kids?:Row;find?:Row};
/** «Сыграй за …»: steps one by one — a choice with its outcome, or a lot (`draw`: a number <= `cut` gives `low`); then the truth and the
 *  document crop of the chapter whose asset is `truth.record`. `kids` texts replace the others in the children's mode where present. */
export type GameStep={q:Row;kids?:Row;choices?:{text:Row;outcome:Row;kids?:Row;icon?:string;gain?:Row}[];draw?:{from:number;to:number;cut:number;low:Row;high:Row;lowKids?:Row;highKids?:Row;button?:Row;stampLow?:Row;stampHigh?:Row}};
export type Route={asset:string;points:{x:number;y:number;label?:Row}[]};
export type Game={title:Row;intro?:Row;kids?:Row;reward?:Row;route?:Route;steps:GameStep[];truth:{text:Row;kids?:Row;record?:string}};
/** `read` is the transcription of the crop in the original language and spelling (never translated); `parts` are further small crops
 *  of the same document, each with its own reading, shown under the first one. `**word**` in a reading is highlighted; `where` says where
 *  to look on the full page. `source` (archive references) is listed under «Подробнее», not under the crop. */
export type Rec={kids?:boolean;asset?:string;kind?:'index'|'home-paper'|'archive-scan';title?:Row;full?:string;source?:string;read?:string;where?:string;parts?:{asset?:string;read?:string}[]};
/** The line of generations drawn above every chapter (`Feed.gens`, oldest first); a chapter marks its generation(s) in `gen.at`
 *  and names who and where it is about (`who`, `where` — proper names, language-neutral). `kids` labels replace `name` in the children's mode.
 *  `ids` are the tree people of the generation: kinship to the chosen reader is counted to the first one the tree can reach. */
export type Gen={name:Row;years:string;kids?:Row;ids?:string[]};
/** A family of today: a couple and their children (`clan`), drawn as cards under the common ancestors. */
export type Clan={parents:string[];families:{head:string;spouse?:string;kids:string[]}[]};
type Activity={kind:'game';key:string;game:Game}|{kind:'spots'|'pano';key:string;picture?:Picture};
type Beat={after:number;figure?:number;record?:number;do?:Activity;placeholder?:{ratio?:[number,number];kind?:string;says?:string}};
/** `flow` places figures, records, activities and draft frames by zero-based paragraph of the full text.
 *  Frames and activities can also stand before the first paragraph.
 *  In the shorter children's text the beats keep their order and use the available paragraph breaks. */
/** `facts` are short documented facts shown as chips inside the story ("кнопки фактов"); `figures` are extra period pictures inside the text;
 *  `records` are document crops shown full-width inside the text with a link to the whole page; `tree` draws a small family diagram
 *  (a couple, their children, and lines of descent from one child down to the family of today). */
export type Chapter={id?:string;part?:Row;year:string|Row;title:Row;text:Row;more?:Row;kind?:ChapterKind;variants?:{title:Row;text:Row;more?:Row}[];places?:{name:Row;note?:Row;url?:string}[];picture?:Picture;figures?:Picture[];facts?:{text:Row;record?:string}[];tree?:{parents:TreeNode[];children:TreeNode[];highlight?:string[];descend?:TreeNode[];descendLabel?:Row;right?:TreeNode[];rightLabel?:Row};person?:string;people?:string[];record?:Rec;records?:Rec[];kids?:{title?:Row;text:Row};kidsRecords?:boolean;kidsSelection?:boolean;flow?:Beat[];extras?:Extra[];gen?:{at:number[];who?:string|Row;where?:string|Row};clan?:Clan;links?:{label:Row;url:string;kind?:'video'|'read'|'map'}[];tone?:string;ask?:Row;game?:Game};
/** A side story attached to a chapter: folded under its own heading, so it does not take a card of its own in the line of the feed.
 *  In the children's mode only extras with a `kids` text are shown. */
export type Extra={title:Row;text:Row;kids?:Row;more?:Row;picture?:Picture;records?:Rec[]};
/** A node of the chapter's small family diagram: a tree person by id (its name from the tree), or a name with no card; `year` is the
 *  birth year the story goes by («≈1880» for an estimate), shown under the name, so the reader sees at once who the chapter is about. */
export type TreeNode=string|{id?:string;name?:Row;year?:string};
export type Feed={id:string;title:Row;lead:Row;cover:string;period:string|Row;line?:string;people?:string[];gens?:Gen[];chapters:Chapter[];names?:Record<string,Row>};
/** A person's name as the feed writes it in the reader's language (feed.names, RULES LANG-2); else the tree card's short name. */
const feedName=(feed:Feed,pid:string,language:string,short=false):string|undefined=>{const r=feed.names?.[pid] as (Record<string,string>&{short?:Record<string,string>})|undefined;if(!r||typeof r!=='object')return undefined;return (short?r.short?.[language]:undefined)||r[language]||undefined};
const personName=(feed:Feed,model:Model,pid:string,language:string)=>model.info[pid]?.clanSurname?model.info[pid].short:feedName(feed,pid,language)||model.info[pid]?.short||pid;
export const tr=(x:any,language:string):string=>inLanguage(x,language);
const FRAME_LABELS:Record<string,Record<string,string>>={
 'period-picture':{ru:'Здесь будет картинка тех лет',pl:'Tu będzie obraz z tamtych lat',en:'A picture from those days will go here',sv:'Här kommer en bild från den tiden'},
 drawing:{ru:'Здесь будет рисунок',pl:'Tu będzie rysunek',en:'A drawing will go here',sv:'Här kommer en teckning'},
 map:{ru:'Здесь будет карта',pl:'Tu będzie mapa',en:'A map will go here',sv:'Här kommer en karta'},
 'family-photograph':{ru:'Здесь будет семейный снимок',pl:'Tu będzie zdjęcie rodzinne',en:'A family photo will go here',sv:'Här kommer ett familjefoto'}
};

function DraftFrame({frame,language}:{frame:NonNullable<Beat['placeholder']>;language:string}){
 if(!frame.ratio||!frame.says)return null;
 const kind=FRAME_LABELS[frame.kind||''];
 return <figure className="feed-placeholder" style={{aspectRatio:frame.ratio.join(' / ')}}>
  <figcaption>{frame.says}{kind&&<small>{kind[language]||kind.en}</small>}</figcaption>
 </figure>;
}
/** A feed without its own cover opens with its first picture, else its first document: never a dark empty tile. */
const coverOf=(f:Feed)=>f.cover||f.chapters.map(c=>c.picture?.asset||c.figures?.find(x=>x.asset)?.asset||c.record?.asset||c.records?.find(r=>r.asset)?.asset).find(Boolean)||'';
/** Covers of every feed for the Stories page. */
export function FeedCovers({feeds,labels,language,open}:{feeds:Feed[];labels:Row;language:Language;open:(id:string)=>void}){
 if(!feeds.length)return null;
 return <section className="feeds"><h2>{labels.feedsTitle}</h2><p className="lead">{labels.feedsHint}</p>
  <div className="feed-grid">{feeds.map(f=><button key={f.id} className={'feed-cover'+(coverOf(f)?'':' plain')} onClick={()=>open(f.id)} style={coverOf(f)?{backgroundImage:`url(${coverOf(f)})`}:undefined}>
   <span className="feed-cover-text"><small>{[tr(f.period,language),`${f.chapters.length} ${plural(f.chapters.length,labels.feedChaptersForms as any,language)}`].filter(Boolean).join(' · ')}</small><strong>{tr(f.title,language)}</strong><span>{tr(f.lead,language)}</span><em>{labels.feedOpen} →</em></span>
  </button>)}</div>
 </section>
}
const MODE_KEY='reader-feed-mode';
/** Older children's texts can be a single run of sentences. Give those sentences
 *  breathing room without changing the words or touching authored paragraphs. */
function childParagraphs(text:string,language:Language,beats:number){
 const paragraphs=text.split(/\n{2,}/);
 if(paragraphs.length!==1||!beats||!Intl.Segmenter)return paragraphs;
 const sentences=Array.from(new Intl.Segmenter(language,{granularity:'sentence'}).segment(text),s=>s.segment);
 const count=Math.min(4,beats+1,Math.ceil(sentences.length/2));
 return count<2?paragraphs:Array.from({length:count},(_,i)=>
  sentences.slice(Math.round(i*sentences.length/count),Math.round((i+1)*sentences.length/count)).join('').trim());
}
/** "For whom" (21.10.2026): the reader is the person chosen as "me" in the tree (or by a `me=` link). Kinship on the strip of generations is
 *  counted from the reader; a child gets the children's mode. Children hear the long chain of "great-" they like; adults get the tree's words. */
const KIDS_ANCESTOR:Record<string,(n:number,f:boolean)=>string>={
 ru:(n,f)=>n===1?(f?'мама':'папа'):n===2?(f?'бабушка':'дедушка'):'пра-'.repeat(n-3)+(f?'прабабушка':'прадедушка'),
 pl:(n,f)=>n===1?(f?'mama':'tata'):n===2?(f?'babcia':'dziadek'):'pra-'.repeat(n-3)+(f?'prababcia':'pradziadek'),
 en:(n,f)=>n===1?(f?'mum':'dad'):n===2?(f?'grandma':'grandpa'):'great-'.repeat(n-2)+(f?'grandma':'grandpa')};
const KIDS_YOUR:Record<string,[string,string]>={ru:['твой','твоя'],pl:['Twój','Twoja'],en:['your','your']};
const KIDS_MAYBE:Record<string,string>={ru:'может быть, ',pl:'może ',en:'maybe '};
const CHILD_AGE=14;
function kinWords(r:Relation,labels:Row,language:string,kids:boolean){
 const word=KIDS_ANCESTOR[language];
 if(kids&&word&&r.kind==='ancestor'&&!r.spouseOf&&r.viaSpouse===undefined&&r.g){const f=r.g==='f';return (r.sure?'':KIDS_MAYBE[language])+KIDS_YOUR[language][f?1:0]+' '+word(r.n1,f)}
 const s=relationPhrase(r,labels,language);
 const TY:Record<string,string>={ваш:'твой',ваша:'твоя',вашего:'твоего',вашей:'твоей'};
 return kids&&language==='ru'?s.split(' ').map(w=>TY[w]||w).join(' '):s;
}
/** Full-screen reader: one chapter at a time, progress on top, explicit controls to turn. A feed with children's texts (`kids`)
 *  has two modes: a short one for children (the default; no details, versions or fact chips) and the full one for parents. */
export function FeedViewer({feed,step,setStep,onClose,go,model,labels,language,changeLanguage,me='',setMe,paper,openPaper}:{paper?:(href:string)=>string|undefined;openPaper?:(id:string,list:string[])=>void;feed:Feed;step:number;setStep:(n:number)=>void;onClose:()=>void;go:(id:string,details?:boolean)=>void;model:Model;labels:Row;language:Language;changeLanguage:(language:Language)=>void;me?:string;setMe?:(id:string)=>void}){
 const n=feed.chapters.length;const i=Math.min(Math.max(step,0),n-1);const c=feed.chapters[i];
 const [open,setOpen]=useState(false);const hasKids=feed.chapters.some(x=>x.kids);
 const [mode,setModeState]=useState<'kids'|'adults'>('kids');
 useEffect(()=>{try{const m=readerStorage.getItem(MODE_KEY);if(m==='kids'||m==='adults')setModeState(m)}catch{}},[]);
 const setMode=(m:'kids'|'adults')=>{setModeState(m);try{readerStorage.setItem(MODE_KEY,m)}catch{}};
 // the reader: a child (younger than CHILD_AGE) gets the children's mode when chosen here or arriving by a `me=` link
 const reader=me&&model.info[me]&&!model.info[me].placeholder?model.info[me]:null;
 const [pick,setPick]=useState(false);const [toc,setToc]=useState(false);const [options,setOptions]=useState(false);const [query,setQuery]=useState('');const [copied,setCopied]=useState(false);
 const modeFor=(pid:string)=>{const b=model.info[pid]?.birth;if(b)setMode(new Date().getFullYear()-b<CHILD_AGE?'kids':'adults')};
 useEffect(()=>{if(me&&/(^|[#&])me=/.test(location.hash))modeFor(me)},[me]);// eslint-disable-line react-hooks/exhaustive-deps
 const chooseReader=(pid:string)=>{setMe?.(pid);modeFor(pid);setPick(false);setQuery('');setCopied(false)};
 const lastIds=feed.gens?.[feed.gens.length-1]?.ids||[];
 const needle=query.trim().toLocaleLowerCase();
 const hits=!pick?[]:needle?Object.values(model.info).filter(x=>isPerson(x)&&(x.name+' '+x.short).toLocaleLowerCase().includes(needle)).sort((a,b)=>(b.birth??0)-(a.birth??0)).slice(0,8)
  // without a query: the youngest descendants of the feed's line, the readers it is most likely shown to
  :Object.values(model.info).filter(x=>isPerson(x)&&(x.birth??0)>=1990&&lastIds.some(a=>model.relation(x.id,a)?.kind==='ancestor')).sort((a,b)=>(b.birth??0)-(a.birth??0)).slice(0,10);
 const share=async()=>{if(!reader)return;const url=location.origin+location.pathname+'#feed='+encodeURIComponent(feed.id)+'&step='+(i+1)+'&me='+encodeURIComponent(reader.id);
  try{if(navigator.share){await navigator.share({title:tr(feed.title,language),url});return}await navigator.clipboard.writeText(url);setCopied(true)}catch{}};
 const kidsMode=hasKids&&mode==='kids';const [credit,setCredit]=useState(false);const [variant,setVariant]=useState(0);const body=useRef<HTMLDivElement>(null);
 const prev=()=>i>0&&setStep(i-1),next=()=>i<n-1&&setStep(i+1);
 useEffect(()=>{setOpen(false);setToc(false);setOptions(false);setCredit(false);setVariant(0);body.current?.scrollTo({top:0})},[i,feed.id]);
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.defaultPrevented||e.target instanceof HTMLElement&&e.target.closest('input,textarea,select,[contenteditable="true"]'))return;if(e.key==='Escape')onClose();else if(e.key==='ArrowRight'){e.preventDefault();next()}else if(e.key==='ArrowLeft'){e.preventDefault();prev()}else if(e.code==='Space'&&!(e.target instanceof HTMLElement&&e.target.closest('button,a,summary'))){e.preventDefault();body.current?.scrollBy({top:(e.shiftKey?-1:1)*(body.current.clientHeight*.85),behavior:'smooth'})}};addEventListener('keydown',key);return()=>removeEventListener('keydown',key)});
 useEffect(()=>{const u=feed.chapters[i+1]?.picture?.asset;if(u){const im=new Image();im.src=u}},[feed,i]);
 const people=[...(c.person?[c.person]:[]),...(c.people||[])].filter(pid=>isPerson(model.info[pid]));
 const paras=(t:string)=>t.split(/\n{2,}/).map((x,k)=>{const ls=x.split('\n');return ls.every(l=>/^[-•] /.test(l))?<ul key={k}>{ls.map((l,j)=><li key={j}>{l.slice(2)}</li>)}</ul>:<p key={k}>{x}</p>});
 const marked=(t:string)=>t.split(/\*\*(.+?)\*\*/).map((x,k)=>k%2?<mark key={k}>{x}</mark>:x);
 /** A scene title opens a paragraph as `**Title.** text` (lab feeds, 11.11.2026): shown bold, not as literal asterisks. */
 const scened=(t:string)=>t.split(/\*\*(.+?)\*\*/).map((x,k)=>k%2?<strong key={k}>{x}</strong>:x);
 const kinds=(labels.feedKind||{}) as Record<string,string>;const kind=c.kind;
 const kt=kidsMode?c.kids:undefined;
 const vars=!kt&&kind==='fork'&&c.variants?.length?c.variants:null;const v=vars?vars[Math.min(variant,vars.length-1)]:null;
 const bodyText=kt?.text||v?.text||c.text;
 const text=tr(bodyText,language),more=kidsMode?'':tr(v?.more||c.more,language);
 const source=profile().family.source_language;
 const fallsBack=(row:Row)=>language!==source&&(typeof row==='string'||!row?.[language])&&!!tr(row,source);
 const originalText=fallsBack(bodyText),originalIntro=!!v&&fallsBack(c.text);
 const allRecs=[...(c.record?[c.record]:[]),...(c.records||[])];
 const paperId=(r:Rec)=>[r.full,r.asset].map(h=>h&&paper?.(h)).find(Boolean) as string|undefined;
 const chapterPapers=allRecs.map(paperId).filter((x):x is string=>!!x);
 const record=(r:Rec,k:number)=><figure key={k} className={'feed-record'+(r.kind==='index'||!r.asset?' feed-index':'')}>{[{asset:r.asset,read:r.read},...(r.parts||[])].map((p,j)=><div key={j} className="feed-snip">{/* eslint-disable-next-line @next/next/no-img-element */}{p.asset&&(paperId(r)?<button className="feed-paper" onClick={()=>openPaper?.(paperId(r)!,chapterPapers)} aria-label={labels.feedOpenDoc}><img src={p.asset} alt={tr(r.title,language)} loading="lazy"/></button>:<img src={p.asset} alt={tr(r.title,language)} loading="lazy"/>)}{p.read&&<q className="feed-read">{marked(p.read)}</q>}</div>)}<figcaption>{r.title&&tr(r.title,language)&&<b>{tr(r.title,language)}</b>}{r.kind==='index'&&<em>{labels.feedIndexOnly}</em>}{r.kind==='home-paper'&&<em>{labels.feedHomePaper}</em>}{r.kind==='archive-scan'&&<em>{labels.feedArchiveScan}</em>}{paperId(r)?<button className="link" onClick={()=>openPaper?.(paperId(r)!,chapterPapers)}>{labels.feedOpenDoc}</button>:(r.full||r.asset)&&<a href={r.full||r.asset} target="_blank" rel="noreferrer">{r.full?labels.feedFullDoc:labels.feedOpenDoc} ↗</a>}</figcaption></figure>;
 // play layer: children get «Найди», adults «Рассмотри»; a feed with one text for all ages offers both (2.11.2026)
 const play={kids:kidsMode,offer:(kidsMode?'find':hasKids?'look':'both') as Offer};
 const fullParagraphs=text.split(/\n{2,}/);
 const flow=(v?[]:c.flow||[]).filter(f=>Number.isInteger(f.after)&&f.after>=-1);
 const visibleFlow=kt?[...flow].sort((a,b)=>a.after-b.after):flow.filter(f=>f.after<fullParagraphs.length);
 const placedF=new Set(visibleFlow.filter(f=>f.after>=0).map(f=>f.figure));
 const placedR=new Set(visibleFlow.filter(f=>f.after>=0).map(f=>f.record));
 const unplaced=allRecs.map((r,k)=>({r,k})).filter(({k})=>!placedR.has(k));
 const markedRecs=unplaced.filter(({r})=>r.kids===true);let remaining=4;
 const unplacedRecords=!kidsMode?unplaced:c.kidsRecords===false?[]:(c.kidsSelection||markedRecs.length)
  ?markedRecs.flatMap(({r,k})=>{if(!remaining)return [];const parts=(r.parts||[]).slice(0,remaining-1);remaining-=1+parts.length;return [{r:{...r,parts},k}]})
  :unplaced.slice(0,1).map(({r,k})=>({r:{...r,parts:(r.parts||[]).slice(0,1)},k}));
 const moved=(kind:Activity['kind'],key?:string)=>visibleFlow.some(f=>f.do?.kind===kind&&f.do.key===key&&
  (f.do.kind==='game'||f.do.picture));
 const staticPicture=(p:Picture):Picture=>({...p,spots:moved('spots',p.asset)?undefined:p.spots,
  pano:moved('pano',p.asset)?undefined:p.pano,ours:p.ours&&staticPicture(p.ours)});
 const cover=c.picture&&staticPicture(c.picture);
 const figure=(f:Picture,k:number)=><FeedFigure key={'f'+k+(f.ours?.asset||'')} f={staticPicture(f)} labels={labels} language={language} {...play}/>;
 const chapterGame=feed.id+'/'+(c.id||tr(c.year,''));
 const game=(g:Game,id:string,key=id)=><GameCard key={key} id={id} game={g} kids={kidsMode} labels={labels} language={language}
  doc={(a:string)=>{const r=allRecs.find(x=>x.asset===a);return r?record(r,-1):null}}/>;
 const activity=(item:Activity,key:number)=>{
  if(item.kind==='game')return game(item.game,item.key,`${chapterGame}/do/${item.key}/${key}`);
  const picture=item.picture;
  const p=picture?.asset===item.key?picture:picture?.ours;
  if(!p||!(item.kind==='spots'?p.spots?.length:p.pano))return null;
  return <figure className="feed-figure" key={'do'+key}>
   <SpotFrame className="feed-figure-frame" asset={p.asset} spots={item.kind==='spots'?p.spots:undefined}
    pano={item.kind==='pano'?p.pano:undefined} labels={labels} language={language} {...play} offer="both">
    <img src={p.asset} alt={tr(p.caption,language)} loading="lazy"/>
   </SpotFrame>
  </figure>;
 };
 // archive references of the documents and authors/licences of the pictures go under «Подробнее», so the story stays light (author, 24.10.2026)
 const srcDocs=kidsMode?[]:[...allRecs,...(c.extras||[]).flatMap(x=>x.records||[])].filter(r=>r.source||r.where).map(r=>({t:tr(r.title,language),s:[r.source,r.where].filter(Boolean).join(' · '),u:r.full}));
 const srcPics=kidsMode?[]:([c.picture,...(c.figures||[]).flatMap(f=>[f,f.ours]),...(c.extras||[]).flatMap(x=>[x.picture,x.picture?.ours])].filter(Boolean) as Picture[]).filter(p=>p.credit||p.url).map(p=>({t:tr(p.caption,language),s:p.credit||p.license||'',u:p.url}));
 const srcList=(title:string,xs:{t:string;s:string;u?:string}[])=>xs.length>0&&<div className="feed-src"><b>{title}</b><ul>{xs.map((d,k)=><li key={k}>{d.t}{d.s&&<>{d.t?': ':''}{d.s}</>}{d.u&&<> · <a href={d.u} target="_blank" rel="noreferrer">↗</a></>}</li>)}</ul></div>;
 const unplacedGame=c.game&&!moved('game',chapterGame)?game(c.game,chapterGame):null;
 const unplacedFigures=(c.figures||[]).flatMap((f,k)=>placedF.has(k)?[]:[figure(f,k)]);
 const beats=visibleFlow.flatMap((beat,j)=>[
   beat.after>=0&&beat.figure!==undefined&&c.figures?.[beat.figure]?figure(c.figures[beat.figure],beat.figure):null,
   beat.after>=0&&beat.record!==undefined&&allRecs[beat.record]?record(allRecs[beat.record],beat.record):null,
   beat.placeholder?.ratio&&<DraftFrame key={'placeholder'+j} frame={beat.placeholder} language={language}/>,
   beat.do&&activity(beat.do,j)
  ].filter(Boolean).map(node=>({after:beat.after,node})));
 const childBeats=kt?[...beats.filter(b=>b.after>=0).map(b=>b.node),...(unplacedGame?[unplacedGame]:[]),...unplacedFigures]:[];
 const storyParagraphs=kt?childParagraphs(text,language,childBeats.length):fullParagraphs;
 const after=(k:number)=>kt&&k>=0
  ?childBeats.filter((_,j)=>Math.min(j,storyParagraphs.length-1)===k)
  :beats.filter(b=>b.after===k).map(b=>b.node);
 const storyBody=()=>[...after(-1),...storyParagraphs.flatMap((x,k)=>[<p key={'p'+k}>{scened(x)}</p>,...after(k)])];
 const showKind=kind&&kinds[kind]&&(!kidsMode||kind==='visit'||kind==='famous');
 const following=feed.chapters[i+1];
 return <div data-feedback-feed={feed.id} data-feedback-feed-label={tr(feed.title,language)} data-feedback-step={String(i+1)} data-feedback-last={following?undefined:'true'} data-feedback-text-mode={kt?'kids':'full'} className={'feed-viewer'+(kind&&!kidsMode?' kind-'+kind:'')+(kidsMode?' feed-kids-mode':'')} role="dialog" aria-modal="true" aria-label={tr(feed.title,language)}>
  <div className="feed-progress" aria-hidden="true">{feed.chapters.map((_,k)=><i key={k} className={k<i?'done':k===i?'now':''}/>)}</div>
  <div className="feed-head"><button className="feed-count" onClick={()=>{setToc(v=>!v);setPick(false);setOptions(false)}} aria-expanded={toc} title={labels.feedContents}><small>{tr(feed.title,language)} · {i+1} / {n} ☰</small></button>
   <button className="feed-options-toggle" onClick={()=>{setOptions(v=>!v);setPick(false);setToc(false)}} aria-expanded={options} aria-controls="feed-options" aria-label={labels.moreMenu} title={labels.moreMenu}>⋯</button>
   <div id="feed-options" className={'feed-options'+(options?' open':'')}>
   {setMe&&<button className={'feed-reader'+(reader?' on':'')} onClick={()=>{setPick(v=>!v);setOptions(false);setToc(false)}} aria-expanded={pick} title={reader?`${labels.feedReader}: ${reader.short}`:labels.feedForWhom}>{reader?`◈ ${reader.short}`:labels.feedForWhom}</button>}
   {hasKids&&<div className="feed-mode" role="tablist" aria-label={labels.feedModeLabel}>{(['kids','adults'] as const).map(m=><button key={m} role="tab" aria-selected={mode===m} className={mode===m?'on':''} onClick={()=>{setMode(m);setOptions(false)}}>{m==='kids'?labels.feedKids:labels.feedAdults}</button>)}</div>}
   <ChestChip feed={feed} labels={labels} language={language}/>
   <LanguagePicker languages={profile().family.languages} language={language} label={labels.language} onChange={lang=>{changeLanguage(lang);setOptions(false)}}/>
   </div>
   <button className="feed-x" onClick={onClose} aria-label={labels.close}>×</button></div>
  {toc&&<nav className="feed-toc" aria-label={labels.feedContents}>{feed.chapters.map((x,k)=><div key={k}>{x.part&&<small>{tr(x.part,language)}</small>}<button className={k===i?'on':''} aria-current={k===i?'step':undefined} onClick={()=>{setStep(k);setToc(false)}}><span>{tr(x.year,language)}</span>{tr((kidsMode&&x.kids?.title)||x.title,language)}</button></div>)}</nav>}
  {pick&&setMe&&<div className="feed-reader-pick">
   <p>{labels.feedReaderHint}</p>
   <input autoFocus aria-label={labels.feedReaderSearch} placeholder={labels.feedReaderSearch} value={query} onChange={e=>setQuery(e.target.value)}/>
   <div className="feed-reader-hits">{hits.map(x=><button key={x.id} className={'chip'+(x.id===me?' on':'')} onClick={()=>chooseReader(x.id)}><b>{x.short}</b>{x.life&&<small>{lifeLabel(x,labels,language)}</small>}</button>)}</div>
   {reader&&<div className="feed-reader-actions"><button onClick={share}>{copied?labels.feedCopied:labels.feedShare}</button><button onClick={()=>{setMe('');setPick(false)}}>{labels.meReset}</button></div>}
  </div>}
  <PlayFeed.Provider value={feed.id}><div ref={body} className="feed-body">
   {cover?.ours||['photo-treatment','photo-restoration'].includes(cover?.kind||'')?<><FeedFigure key={feed.id+'-'+i} f={cover!} labels={labels} language={language} {...play}/><p className="feed-year">{tr(c.year,language)}</p></>:<div className={c.picture?'feed-pic-mat':undefined}><SpotFrame key={feed.id+'-'+i} className={'feed-pic'+(c.picture?'':' empty')} spots={cover?.spots} asset={cover?.asset} pano={cover?.pano} labels={labels} language={language} {...play}>{c.picture?/* eslint-disable-next-line @next/next/no-img-element */<img key={c.picture.asset} src={c.picture.asset} alt={tr(c.picture.caption,language)}/>:null}
    <span className="feed-year" style={c.tone?{background:c.tone}:undefined}>{tr(c.year,language)}</span>
    {c.picture&&<button className="feed-credit-btn" onClick={()=>setCredit(v=>!v)} aria-expanded={credit}>i</button>}
    {credit&&c.picture&&<p className="feed-credit">{[tr(c.picture.caption,language),c.picture.credit].filter(Boolean).join(' · ')}{c.picture.url&&<> · <a href={c.picture.url} target="_blank" rel="noreferrer">{labels.storyPicSource} ↗</a></>}{c.picture.orig&&<> · <a href={typeof c.picture.orig==='string'?c.picture.orig:c.picture.orig.asset} target="_blank" rel="noreferrer">{labels.feedRealTab} ↗</a></>}</p>}
   </SpotFrame></div>}
   {feed.gens&&c.gen&&<GenStrip model={model} gens={feed.gens} gen={c.gen} kids={kidsMode} language={language} labels={labels}
    reader={reader?.short} kin={g=>{if(!reader)return '';for(const id of g.ids||[]){const r=model.info[id]?model.relation(reader.id,id):null;if(r)return kinWords(r,labels,language,kidsMode)+(kinNote(r,language)?' — '+kinNote(r,language):'')}return ''}}/>}
   <div className="feed-text">
    {c.part&&<span className="feed-part">{tr(c.part,language)}</span>}
    {showKind&&<span className={'feed-kind '+kind}>{kinds[kind!]}</span>}
    <h2>{tr(kt?.title||c.title,language)}</h2>
    {(originalText||originalIntro)&&<p><small>{labels.feedOriginalText}</small></p>}
    {v&&<div className="feed-simple" lang={originalIntro?source:undefined}>{paras(tr(c.text,language))}</div>}
    {vars&&<div className="feed-variants" role="tablist">{vars.map((x,k)=><button key={k} role="tab" aria-selected={k===variant} className={k===variant?'on':''} onClick={()=>setVariant(k)}>{tr(x.title,language)}</button>)}</div>}
    {c.clan&&<FeedClan clan={c.clan} model={model} labels={labels} name={pid=>personName(feed,model,pid,language)} open={pid=>{onClose();go(pid,true)}}/>}
    {c.tree&&<FeedTree tree={c.tree} model={model} language={language} labels={labels} name={pid=>feedName(feed,pid,language,true)} open={pid=>{onClose();go(pid,true)}}/>}
    <div className="feed-simple" lang={originalText?source:undefined}>{storyBody()}</div>
    {/* one text for all ages (author, 25.10.2026): a short question or "did you know" for a child reading with an adult */}
    {c.ask&&<aside className="feed-ask"><b>{labels.feedAsk}</b>{paras(tr(c.ask,language))}</aside>}
    {!kt&&unplacedGame}
    {!kidsMode&&c.facts&&c.facts.length>0&&<div className="feed-facts">{c.facts.map((f,k)=><span key={k} className="feed-fact">{f.record?<a href={f.record} target="_blank" rel="noreferrer">◆ {tr(f.text,language)}</a>:<>◆ {tr(f.text,language)}</>}</span>)}</div>}
    {!kt&&unplacedFigures}
    {(more||srcDocs.length>0||srcPics.length>0)&&<details className="story-more" open={open} onToggle={e=>setOpen((e.target as HTMLDetailsElement).open)}><summary>{kind==='truth'?labels.feedMoreTruth:labels.feedMore}</summary>{more&&paras(more)}{srcList(labels.feedSrcDocs,srcDocs)}{srcList(labels.feedSrcPics,srcPics)}</details>}
    {c.places&&c.places.length>0&&<div className="feed-places"><small>{labels.feedPlaces}</small>{c.places.map((p,k)=><div key={k} className="feed-place"><b>{tr(p.name,language)}</b>{p.note&&<span>{tr(p.note,language)}</span>}{p.url&&<a href={p.url} target="_blank" rel="noreferrer">◎ {labels.feedOnMap} ↗</a>}</div>)}</div>}
    {unplacedRecords.map(({r,k})=>record(r,k))}
    {(c.extras||[]).filter(x=>!kidsMode||x.kids).map((x,k)=><details key={i+'-'+k} className="story-more feed-extra"><summary>{labels.feedExtra}: {tr(x.title,language)}</summary>
     {x.picture&&<FeedFigure f={staticPicture(x.picture)} labels={labels} language={language} {...play}/>}
     <div className="feed-simple">{paras(tr(kidsMode?x.kids:x.text,language))}</div>
     {!kidsMode&&x.more&&<div className="feed-extra-more">{paras(tr(x.more,language))}</div>}
     {!kidsMode&&(x.records||[]).map(record)}
    </details>)}
    {(people.length>0||(c.links||[]).length>0)&&<div className="feed-links">
     {people.map(pid=>{const r=reader&&reader.id!==pid?model.relation(reader.id,pid):null,note=r?kinNote(r,language):'';return <button key={pid} className="feed-chip person" onClick={()=>go(pid,true)}><span>{personName(feed,model,pid,language)}{r&&<small>{kinWords(r,labels,language,kidsMode)}{note&&': '+note}</small>}</span></button>})}
     {(c.links||[]).map((l,k)=><a key={k} className={'feed-chip '+(l.kind||'read')} href={l.url} target="_blank" rel="noreferrer">{l.kind==='video'?'▶ ':l.kind==='map'?'◎ ':'↗ '}{tr(l.label,language)}</a>)}
    </div>}
    <div className="paper-remark"><Feedback language={language}/></div>
    {following&&<button className="feed-next" onClick={next}>
     <small>{labels.feedNextChapter} · {tr(following.year,language)} →</small>
     <strong>{tr((kidsMode&&following.kids?.title)||following.title,language)}</strong>
     <span>{tr((kidsMode&&following.kids?.text)||following.text,language).split(/\n/)[0].replace(/\*\*/g,'')}</span>
    </button>}
   </div>
  </div></PlayFeed.Provider>
  <div className="feed-foot"><button onClick={prev} disabled={i===0}>‹ {labels.prev}</button><span>{tr(c.year,language)}</span>{i<n-1?<button onClick={next}>{labels.next} ›</button>:<button onClick={onClose}>{labels.feedEnd}</button>}</div>
 </div>
}

const ROMAN=['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII'];
/** The line of generations, oldest on the left; the chapter's generation is lit, the ones before it are passed. */
/** A picture inside the text. A real picture with a paired drawing shows the drawing, and the real one sits in its corner as a small
 *  «Оригинал» inset: a tap opens it over the feed, so the page never jumps and the scene keeps its rhythm (author, 31.10.2026). */
/** Reader words for a real photograph paired with its restoration or treatment. Only the caption and one quiet line are on the
 *  screen; how it was made (disclosure, invented details, model and date, comparison numbers, recipe) opens under «как сделано». */
const PAIR_WORDS:Record<string,{restored:string;treated:string;how:string;variant:string;invented:string;version:string;recipe:string;original:string;check:(n:Record<string,string>)=>string}>={
 ru:{restored:'Восстановлено по старому снимку',treated:'Обработка настоящего снимка',how:'как сделано',variant:'Вариант',invented:'Додумано',version:'номер',recipe:'Рецепт',original:'оригинал доступен',
  check:n=>`Сверка с оригиналом: попытка ${n.chosen_attempt} из ${n.attempts}; уменьшено до ${n.reduced_width_px} пикс., размытие ${n.blur_radius_px} пикс., средняя разница ${n.mean_absolute_error} из 255`},
 pl:{restored:'Odtworzone ze starego zdjęcia',treated:'Obróbka prawdziwego zdjęcia',how:'jak to zrobiono',variant:'Wariant',invented:'Dopowiedziane',version:'numer',recipe:'Przepis',original:'oryginał dostępny',
  check:n=>`Porównanie z oryginałem: próba ${n.chosen_attempt} z ${n.attempts}; zmniejszone do ${n.reduced_width_px} pks, rozmycie ${n.blur_radius_px} pks, średnia różnica ${n.mean_absolute_error} z 255`},
 en:{restored:'Restored from an old photograph',treated:'Treated real photograph',how:'how it was made',variant:'Variant',invented:'Invented',version:'version',recipe:'Recipe',original:'the original is available',
  check:n=>`Compared with the original: attempt ${n.chosen_attempt} of ${n.attempts}; reduced to ${n.reduced_width_px} px, blur ${n.blur_radius_px} px, mean difference ${n.mean_absolute_error} of 255`}};
/** The variant a reader chose stays chosen while the page is open: in the feed, on the person card and after leaving the chapter. */
const chosenVariant=new Map<string,string>();
/** "Model X; model and revision not recorded" → "Model X": an empty statement is skipped, not printed. */
const recorded=(s:string)=>(s||'').split(/\s*;\s*/).filter(x=>x&&!/(не\s+записан|not\s+recorded|nie\s+zapisan|unrecorded)/i.test(x)).join('; ');
export function FeedFigure({f,labels,language,kids=false,offer='look'}:{f:Picture;labels:Row;language:Language;kids?:boolean;offer?:Offer}){
 const [real,setReal]=useState(false);
 const base=f.ours||f, original=f.ours?f:(typeof f.orig==='object'?f.orig:null);
 const pair=base.kind==='photo-restoration'||base.kind==='photo-treatment'?base.kind:null;
 const key=base.id||base.versions?.[0]?.asset||base.asset;
 const [choice,setChoiceState]=useState(chosenVariant.get(key)||base.primary);
 const setChoice=(v:string)=>{chosenVariant.set(key,v);setChoiceState(v)};
 const version=base.versions?.find(v=>v.id===choice)||base.versions?.find(v=>v.id===base.primary);
 const p=version?{...base,...version}:base;
 const w=PAIR_WORDS[language]||PAIR_WORDS.en;
 const number=(x:number)=>new Intl.NumberFormat(language).format(x);
 const when=(d:string)=>{const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(d||'');return m?new Intl.DateTimeFormat(language,{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(Date.UTC(+m[1],+m[2]-1,+m[3]))):d||''};
 const recipe=version?.recipe;
 const how=pair==='photo-restoration'?w.restored:w.treated;
 const caption=tr(p.caption,language);
 useEffect(()=>{if(!real)return;const key=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.stopImmediatePropagation();setReal(false)}};
  addEventListener('keydown',key,true);return()=>removeEventListener('keydown',key,true)},[real]);
 return <figure className={'feed-figure'+(p.small?' small':'')+(pair?' photo-pair':'')+(pair==='photo-restoration'?' photo-restoration':'')}>
  <SpotFrame className="feed-figure-frame" spots={pair==='photo-restoration'?undefined:p.spots} asset={p.asset} pano={pair==='photo-restoration'?undefined:p.pano} kids={kids} offer={pair==='photo-restoration'?'look':offer} labels={labels} language={language}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={p.asset} alt={pair?[caption,how+(original?', '+w.original:'')].filter(Boolean).join('. '):caption} loading="lazy"/>
   {original&&<button className="feed-figure-orig" onClick={e=>{e.stopPropagation();setReal(true)}} aria-label={labels.feedRealTab}>
    {/* eslint-disable-next-line @next/next/no-img-element */}<img src={original.asset} alt="" loading="lazy"/><span>{labels.feedRealTab}</span></button>}
  </SpotFrame>
  {pair?<>
   {caption&&<figcaption>{caption}</figcaption>}
   {(base.versions?.length||0)>1&&<div className="pair-variants" role="group" aria-label={w.variant}>{base.versions!.map((v,n)=><button key={v.id} aria-pressed={v.id===version?.id} onClick={()=>{setChoice(v.id);setReal(false)}}>{tr(v.label,language)||`${w.variant} ${n+1}`}</button>)}</div>}
   <details className="pair-how"><summary><span>{how}</span> · <u>{w.how}</u></summary>
    {tr(p.disclosure,language)&&<p>{tr(p.disclosure,language)}</p>}
    {recipe&&<>
     {recipe.invented?.length>0&&<p>{w.invented}: {recipe.invented.map(x=>tr(x,language)).filter(Boolean).join(', ')}</p>}
     <p>{[recorded(recipe.model),when(recipe.date),recipe.version?`${w.version} ${recipe.version}`:''].filter(Boolean).join(' · ')}</p>
     {recipe.comparison&&<p>{w.check(Object.fromEntries(Object.entries(recipe.comparison).map(([k,v])=>[k,number(v)])))}</p>}
     <details className="pair-recipe"><summary>{w.recipe}</summary><pre>{JSON.stringify(recipe,null,2)}</pre></details>
    </>}
   </details>
  </>:<figcaption>{[tr(p.caption,language),tr(p.disclosure,language)].filter(Boolean).join(' · ')}</figcaption>}
  {real&&original&&<div className="feed-figure-over" role="dialog" aria-label={labels.feedRealTab} onClick={e=>{e.stopPropagation();setReal(false)}}>
   {/* eslint-disable-next-line @next/next/no-img-element */}<img src={original.asset} alt={tr(original.caption,language)}/>
   <p>{tr(original.caption,language)}</p></div>}
 </figure>;
}

function GenStrip({model,gens,gen,kids,language,labels,reader,kin}:{model:Model;gens:Gen[];gen:NonNullable<Chapter['gen']>;kids:boolean;language:Language;labels:Row;reader?:string;kin:(g:Gen)=>string}){
 const generationName=(g:Gen)=>g.ids?.some(id=>model.info[id]?.clanSurname)?g.ids.map(id=>model.info[id]?.short).filter(Boolean).join(' · '):tr(kids&&g.kids?g.kids:g.name,language);
 const at=new Set(gen.at);const first=Math.min(...gen.at);const txt=(x:string|Row)=>typeof x==='string'?x:tr(x,language);
 // Kinship of the selected generations to the reader, in child and adult forms.
 const lit=reader?[...gen.at].sort((a,b)=>a-b).map(k=>gens[k]).filter(Boolean).map(g=>[generationName(g),kin(g)]).filter(([,w])=>w):[];
 return <div className="feed-gens" aria-label={labels.feedGensLabel}>
  <ol>{gens.map((g,k)=><li key={k} className={at.has(k)?'on':k<first?'past':''}><i/><b>{generationName(g)}</b><small>{g.years}</small></li>)}</ol>
  <p><span>{labels.feedGen} {gen.at.length>1?ROMAN[first]+'–'+ROMAN[Math.max(...gen.at)]:ROMAN[first]}</span>{gen.who&&<> · {txt(gen.who)}</>}{gen.where&&<em> · ◎ {txt(gen.where)}</em>}</p>
  {lit.length>0&&<p className="feed-kin">{!kids&&<span>{labels.feedReader} {reader}: </span>}{lit.map(([name,w])=>`${name} — ${w}`).join('; ')}</p>}
 </div>
}
/** The family of today: common ancestors on top, then one card per child with spouse and children. */
function FeedClan({clan,model,labels,name,open}:{clan:Clan;model:Model;labels:Row;name:(id:string)=>string;open:(id:string)=>void}){
 const Node=({id,cls=''}:{id:string;cls?:string})=><button className={'ft-node '+cls} onClick={()=>open(id)} disabled={!model.info[id]}>{name(id)}</button>;
 return <div className="feed-tree feed-clan" aria-label={labels.feedTreeLabel}>
  <div className="ft-row ft-parents">{clan.parents.map(id=><Node key={id} id={id}/>)}</div>
  <div className="ft-link"/>
  <div className="fc-grid">{clan.families.map(f=><div key={f.head} className="fc-family">
   <div className="fc-couple"><Node id={f.head} cls="hl"/>{f.spouse&&<Node id={f.spouse}/>}</div>
   {f.kids.length>0&&<div className="fc-kids">{f.kids.map(id=><Node key={id} id={id}/>)}</div>}
  </div>)}</div>
 </div>
}

/** A small family diagram: a couple, their children in a row, and lines of descent from one child down to the family of today. */
function FeedTree({tree,model,language,labels,name:pname,open}:{tree:NonNullable<Chapter['tree']>;model:Model;language:Language;labels:Row;name:(id:string)=>string|undefined;open:(id:string)=>void}){
 const hl=new Set(tree.highlight||[]);
 const Node=({node}:{node:TreeNode})=>{const x=typeof node==='string'?{id:node}:node;const id=x.id||'';const known=!!(id&&model.info[id]);
  // the feed's own reader-language short name first, then the node's label (string or per language), then the tree card
  const name=(id&&pname(id))||(x.name?tr(x.name,language):'')||(known?model.info[id].short:id);
  return <button className={'ft-node'+(hl.has(id)?' hl':'')+(x.year?' ft-dated':'')} onClick={()=>open(id)} disabled={!known}>{name}{x.year&&<small>{x.year}</small>}</button>};
 const key=(n:TreeNode,k:number)=>typeof n==='string'?n:(n.id||tr(n.name,'pl')||'')+k;
 return <div className="feed-tree" aria-label={labels.feedTreeLabel}>
  <div className="ft-row ft-parents">{tree.parents.map((n,k)=><Node key={key(n,k)} node={n}/>)}</div>
  <div className="ft-link"/>
  <div className="ft-row ft-children">{tree.children.map((n,k)=><Node key={key(n,k)} node={n}/>)}</div>
  {(tree.descend?.length||tree.right?.length)?<div className="ft-cols">
   {tree.descend&&tree.descend.length>0&&<div className="ft-col"><small>{tr(tree.descendLabel,language)}</small>{tree.descend.map((n,k)=><div key={key(n,k)} className="ft-step"><i/><Node node={n}/></div>)}</div>}
   {tree.right&&tree.right.length>0&&<div className="ft-col"><small>{tr(tree.rightLabel,language)}</small>{tree.right.map((n,k)=><div key={key(n,k)} className="ft-step"><i/><Node node={n}/></div>)}</div>}
  </div>:null}
 </div>
}
