'use client';
import {readerStorage,profile,siteURL,inLanguage} from './reader-profile';
import {localizeGraph} from './localize';
import {useEffect,useLayoutEffect,useMemo,useRef,useState} from 'react';
import KinshipWords,{kinNote} from './kinship-words';
import {kinshipLexicon} from './tree/kinship';
import TreeStage from './tree/tree-stage';
import PersonPanel from './tree/person-panel';
import Families from './families';
import Stories from './stories';
import WorldMap,{worldText} from './world-map';
import {FeedViewer,type Feed} from './feed';
import LanguagePicker from './language-picker';
import PageTop,{familyHeading} from './page-top';
import Papers,{PaperView,collectPapers,type Paper,type PaperMode} from './papers';
import {SearchSheet,SearchButton} from './search';
import {MiniMap,OverviewDialog,buildOverview} from './tree/overview';
import {buildModel,isPerson,kinPhrase,lifeLabel,placeLabel,relationPhrase} from './tree/model';

import {plural,translations,type Language} from './i18n';
type Row=Record<string,any>;
const ICONS:Record<string,React.ReactNode>={tree:<><circle cx="12" cy="5" r="2.5"/><circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="M12 7.5V12M12 12 6.8 16.6M12 12l5.2 4.6"/></>,stories:<><path d="M3 5.5A2.5 2.5 0 0 1 5.5 3H11v16H5.5A2.5 2.5 0 0 0 3 21z"/><path d="M21 5.5A2.5 2.5 0 0 0 18.5 3H13v16h5.5A2.5 2.5 0 0 1 21 21z"/></>,papers:<><path d="M6 3h8l5 5v13H6z"/><path d="M14 3v5h5M9 13h7M9 17h5"/></>};
const Icon=({name}:{name:string})=><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>;
const GRAVE=/памятник|могил|надгроб|grave|nagrob|· документ$/i;
/** A step through the reader is an entry of the browser's history: Back returns to the page and to the place on it. */
let entry=Date.now();
const push=(hash:string)=>history.pushState({n:++entry},'',hash);
const baseHash=()=>{const q=new URLSearchParams(location.hash.slice(1));q.delete('paper');return q.toString()};
export default function Family({initialData,signedInViewer}:{initialData:Row;signedInViewer:string}){
 const [viewer,setViewer]=useState(()=>{try{return readerStorage.getItem('family-me')??(signedInViewer||null)}catch{return signedInViewer||null}});
 const [id,select]=useState(()=>typeof location==='undefined'?'':new URLSearchParams(location.hash.slice(1)).get('person')||'');const [picked,setPicked]=useState('');const [view,V]=useState('tree');const [language,L]=useState<Language>(profile().family.source_language);const data=useMemo(()=>localizeGraph(initialData,language),[initialData,language]);const [expanded,Expand]=useState(false);const [map,Map_]=useState(false);const [visible,setVisible]=useState<Set<string>>(new Set());const [feed,setFeed]=useState<{id:string;step:number}|null>(null);const [finding,Find]=useState(false);const [paperId,setPaper]=useState('');const [paperList,setPaperList]=useState<string[]>([]);const [paperMode,setPaperMode]=useState<PaperMode>('people');const [of,setOf]=useState('');const base=translations[language];const title=profile().family.title;const t={...base,...(language===profile().family.source_language?data.readerLabels:{}),title:typeof title==='string'?title:title[language]||title[profile().family.source_language]||base.title,homeGenitive:profile().reader_names?.[language]||{}};
 // "me" is who is looking at the tree: from a personal link (#person=…&me=…) or chosen in the panel, remembered in this browser
 const rememberViewer=(pid:string)=>{setViewer(pid);try{readerStorage.setItem('family-me',pid)}catch{}};
 const setMe=(pid:string)=>{
  rememberViewer(pid);
  if(view==='tree'&&(pid||home))go(pid||home);
  else select(pid);
 };
 const [undo,setUndo]=useState<{name:string}|null>(null);
 useEffect(()=>{if(!undo)return;const timer=setTimeout(()=>setUndo(null),6000);return()=>clearTimeout(timer)},[undo]);
 const at=useRef<string|null>(null),places=useRef(new Map<number,number>());
 useEffect(()=>{try{const saved=readerStorage.getItem('family-language');if(saved&&profile().family.languages.includes(saved as Language))L(saved as Language)}catch{}const change=()=>{const q=new URLSearchParams(location.hash.slice(1));setPaper(q.get('paper')||'');const now=baseHash();if(at.current===now)return;at.current=now;setOf(q.get('of')||'');const p=q.get('person');const m=q.get('me');const v=q.get('view');const f=q.get('feed');if(m)rememberViewer(m);if(f){V('stories');setFeed({id:f,step:Math.max(0,(parseInt(q.get('step')||'1',10)||1)-1)});return}setFeed(null);if(p){select(p);setPicked('');V('tree');Map_(false);Expand(q.get('details')==='1')}else if(v&&['tree','stories','world','families','papers','kinship'].includes(v)){V(v);Map_(false);Find(false)}else{select('');setPicked('');V('tree');Expand(false)}};change();addEventListener('hashchange',change);return()=>removeEventListener('hashchange',change)},[]);// eslint-disable-line react-hooks/exhaustive-deps
 // the place on a page belongs to its history entry: a new step starts at the top, Back returns to where the reader was
 const where=view+'|'+of;
 useEffect(()=>{const keep=()=>{const n=history.state?.n;if(typeof n==='number')places.current.set(n,scrollY)};addEventListener('scroll',keep,{passive:true});return()=>removeEventListener('scroll',keep)},[]);
 useLayoutEffect(()=>{const n=history.state?.n;if(typeof n==='number'){const y=places.current.get(n)??0;requestAnimationFrame(()=>scrollTo(0,y))}else{history.replaceState({...(history.state||{}),n:++entry},'');if(!/(^|[#&])(word)=/.test(location.hash))scrollTo(0,0)}},[where]);
 useEffect(()=>{const key=(e:KeyboardEvent)=>{const el=e.target as HTMLElement;if(/INPUT|TEXTAREA|SELECT/.test(el.tagName))return;if(e.key==='/'||((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k')){e.preventDefault();Find(true)}};addEventListener('keydown',key);return()=>removeEventListener('keydown',key)},[]);
 useEffect(()=>{if(view!=='kinship')return;const word=new URLSearchParams(location.hash.slice(1)).get('word');if(word)requestAnimationFrame(()=>document.getElementById('word-'+word)?.scrollIntoView())},[view,language]);
 useEffect(()=>{document.documentElement.lang=language;document.title=view==='world'?worldText[language].title+' · '+t.title:t.title},[language,t.title,view]);
 const model=useMemo(()=>data?buildModel(data,t):null,[data,language]);
 // the open picture takes the shape of the screen: a wide one spreads the lines out, a phone keeps the natural width
 const overview=useMemo(()=>model&&map?buildOverview(model,{aspect:innerWidth/Math.max(320,innerHeight-200)}):null,[model,map]);
 // the corner picture is wide and low: its lines spread out to fill it
 const mini=useMemo(()=>model&&view==='tree'?buildOverview(model,{aspect:3.4}):null,[model,view]);
 function changeLanguage(value:Language){L(value);try{readerStorage.setItem('family-language',value)}catch{}}
 // open a person in the tree; `details` opens the card itself (the story) on a phone, where the card starts folded
 function go(pid:string,details=false){if(!isPerson(model?.info[pid]))return;Find(false);V('tree');select(pid);setPicked('');location.hash='person='+encodeURIComponent(pid)+(details?'&details=1':'');Expand(details)}
 function show(v:string){Find(false);if(v===view&&!of&&!feed){scrollTo({top:0,behavior:'smooth'});return}V(v);setOf('');setFeed(null);Map_(false);push('#view='+v);at.current=baseHash()}
 // a historical feed opens over the Stories page; the chapter lives in the hash so a link can point at it
 function openFeed(fid:string,step=0){setFeed({id:fid,step});V('stories');push('#feed='+encodeURIComponent(fid)+'&step='+(step+1));at.current=baseHash()}
 // a paper lies over whatever was open: closing it, or Back, uncovers the same place
 function openPaper(id:string,list:string[]=[]){if(!paperId)push((location.hash||'#view='+view)+'&paper='+encodeURIComponent(id));else history.replaceState(history.state,'',location.hash.replace(/([#&])paper=[^&]*/,'$1paper='+encodeURIComponent(id)));setPaperList(list);setPaper(id)}
 function closePaper(){if(paperList.length)history.back();else{history.replaceState(history.state,'','#'+(baseHash()||'view='+view));setPaper('')}}
 function papersOf(pid:string){setOf(pid);V('papers');push('#view=papers'+(pid?'&of='+encodeURIComponent(pid):''));at.current=baseHash()}
 function closeFeed(){setFeed(null);history.replaceState(history.state,'','#view=stories');at.current=baseHash()}
 const papers=useMemo(()=>model?collectPapers(data,model,language):[],[data,model,language]);
 const paperBy=useMemo(()=>{const m=new Map<string,Paper>();for(const x of papers){m.set(x.id,x);for(const k of [x.page,x.full,x.thumb])if(k&&!m.has(k))m.set(k,x)}for(const [sid,s] of Object.entries<Row>(initialData.sources||{})){const x=m.get(sid);if(x)for(const k of [s.asset,...Object.values<string>(s.assetIn||{})])if(k&&!m.has(k))m.set(k,x)}return m},[papers,initialData]);
 if(!data||!model)return <main className="loading">{t.opening}</main>;
 const labels:Row={...t,status:{verified:t.document,export:t.family,hypothesis:t.familyUncertain,conflict:t.conflict}};
 const connected=model.familyPeople;
 const people=data.people;const canonicalId=data.identityAliases?.[id]||id;const resolvedId=data.presentationAliases?.[canonicalId]||canonicalId;const home=model.homes[0];const resolveViewer=(pid:string)=>data.identityAliases?.[pid]||pid;
 const start=resolveViewer(viewer||'');
 const me=viewer===null?resolveViewer(initialData.defaultViewer||initialData.narrator||''):isPerson(model.info[start])?start:'';
 const personId=isPerson(model.info[resolvedId])?resolvedId:isPerson(model.info[start])?start:home;
 const panelId=picked||personId;
 const openFamily=(pid:string)=>{if(pid!==personId)setUndo({name:model.info[personId].short});go(pid)};
 const group=(pid:string)=>connected.has(pid)?'family':['refuted_relationship','withdrawn_relationship','split_identity'].includes(data.cardStatuses[pid]?.review?.kind)?'archive':'context';
 const row=(pid:string,kin?:string)=>{const i=model.info[pid];if(!isPerson(i))return null;const tone=model.tone(pid);const line=[kin,data.people[pid]?.disambiguator?.[language],lifeLabel(i,t,language)||i.note,placeLabel(i,t)].filter(Boolean).join(' · ');return <button key={pid} className="person-row" onClick={()=>go(pid)}><span className={'av'+(tone?.kin?' line-kin':'')} style={tone?{background:tone.color}:undefined}>{i.name.slice(0,1)}</span><span><strong>{i.short}{i.maidenShown&&<small className="maiden" title={t.maidenLabel+': '+i.maidenShown}> ({i.maidenShown})</small>}{i.story&&<i className="st-dot" title={t.hasStory} aria-label={t.hasStory}/>}</strong>{line&&<small>{line}</small>}</span></button>};
 // who this person is: from the viewer when chosen, otherwise from the two home people
 const kinOf=(pid:string)=>{const from=me&&model.info[me]?me:'';const r=from&&from!==pid?model.relation(from,pid):null;if(r){const note=kinNote(r,language);return relationPhrase(r,labels,language)+(note?': '+note:'')}const k=model.kinship(pid)[0];return k?kinPhrase(k,labels,language):''};
 // pictures attached to people: family photographs, gravestones and the editorial period pictures from the stories
 const album=(()=>{const byPic=new Map<string,{asset:string;title:string;people:string[];grave:boolean}>();for(const p of Object.values<Row>(people)){for(const m of p.media||[]){if(!m.photo||!m.asset||m.cardOnly)continue;const e=byPic.get(m.asset)||byPic.set(m.asset,{asset:m.asset,title:m.title||'',people:[],grave:m.type==='grave'||GRAVE.test(m.title||'')}).get(m.asset)!;if(!e.people.includes(p.id))e.people.push(p.id)}}return [...byPic.values()]})();
 const period=(()=>{const seen=new Set<string>();const out:{asset:string;caption:string;person:string}[]=[];for(const p of Object.values<Row>(people))for(const s of p.illustrations||[]){if(!s.asset||seen.has(s.asset))continue;seen.add(s.asset);out.push({asset:s.asset,caption:inLanguage(s.caption,language),person:p.id})}return out})();
 const albumGrid=(items:typeof album)=><div className="album">{items.map(a=><button key={a.asset} onClick={()=>a.people[0]&&go(a.people[0])}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={a.asset} alt={a.people.map(p=>model.info[p].short).join(', ')} loading="lazy"/><p>{a.people.map(p=>model.info[p].short).join(', ')||a.title}</p></button>)}</div>;
 const hasStories=(data.feeds||[]).some((f:Feed)=>f.chapters?.length)||Object.values(model.info).some(p=>p.story&&!p.placeholder);
 const hasPhotos=album.length>0||period.length>0;
 const hasPapers=papers.length>0||hasPhotos;
 const currentView=(view==='stories'&&!hasStories||view==='papers'&&!hasPapers||view==='world'&&!data.worldMap||view==='kinship'&&!kinshipLexicon(language))?'tree':view;
 // the lower row holds the places a reader comes for; whatever is empty in this family is not there
 const tabs:[string,string][]=[['tree',t.tree],...(hasStories?[['stories',t.stories] as [string,string]]:[]),...(hasPapers?[['papers',t.papers] as [string,string]]:[])];
 // a desk lists the quieter places itself, together with its own pages
 const quiet:[string,string][]=document.getElementById('desk-more')?[]:[['families',t.families],...(data.worldMap?[['world',worldText[language].nav] as [string,string]]:[])];
 const familyTitle=familyHeading(t.title,model.homes.map(h=>model.info[h]?.surnameKey));
 return <div className={'shell v-'+currentView} data-feedback-screen={finding?'search':currentView}>
  <PageTop title={familyTitle} home={siteURL('#view=tree')} onHome={()=>go(home)} notice={profile().family.fictional?t.fictionalDemo:undefined} navigation={<nav className="tabs-top" aria-label={t.title}>{tabs.map(([k,l])=><button className={currentView===k?'active':''} key={k} onClick={()=>show(k)}>{l}</button>)}</nav>} search={<SearchButton open={finding} label={t.find} onClick={()=>Find(!finding)}/>} language={profile().family.languages.length>1?<LanguagePicker languages={profile().family.languages} language={language} label={t.language} onChange={changeLanguage}/>:undefined}
   more={t.moreMenu} moreItems={<>{quiet.map(([k,l])=><a key={k} href={'#view='+k} onClick={e=>{e.preventDefault();show(k)}}>{l}</a>)}{profile().family.languages.length>1&&<label className="page-more-language">{t.languageWord}<LanguagePicker names languages={profile().family.languages} language={language} label={t.language} onChange={changeLanguage}/></label>}</>}/>
  {finding&&<SearchSheet data={data} model={model} group={group} row={id=>row(id,kinOf(id))} labels={labels} onClose={()=>Find(false)}/>}
  {currentView==='tree'&&personId&&<div className="tree-body">
   <TreeStage model={model} id={personId} go={go} labels={labels} onVisible={setVisible}>
    {mini&&<MiniMap ov={mini} model={model} visible={visible} center={personId} onOpen={()=>Map_(true)} label={t.map} caption={`${model.familyPeople.size} ${plural(model.familyPeople.size,labels.personsForms,language)}`}/>}
   </TreeStage>
   {panelId&&<PersonPanel data={data} model={model} id={panelId} go={go} showFamily={panelId!==personId?()=>openFamily(panelId):undefined} labels={labels} language={language} expanded={expanded} setExpanded={Expand} me={me} setMe={setMe} openFeed={openFeed} papers={papers} openPaper={openPaper} papersOf={papersOf}/>}
  </div>}
  {map&&overview&&<OverviewDialog ov={overview} model={model} visible={visible} center={personId} go={pid=>{if(pid!==personId)setUndo({name:model.info[personId].short});go(pid,true)}} onClose={()=>Map_(false)} labels={labels} language={language} me={me}/>}
  {undo&&<button className="person-undo" onClick={()=>{history.back();setUndo(null)}}>← {t.backToPerson.replace('{name}',undo.name)}</button>}
  {currentView==='stories'&&<Stories data={data} model={model} go={go} labels={labels} language={language} openFeed={openFeed}/>}
  {currentView==='world'&&<WorldMap atlas={data.worldMap} language={language} go={go} openFeed={openFeed} feeds={data.feeds||[]}/>}
  {feed&&(()=>{const f=(data.feeds||[]).find((x:Feed)=>x.id===feed.id);return f?<FeedViewer feed={f} step={feed.step} setStep={n=>openFeed(f.id,n)} onClose={closeFeed} go={go} model={model} labels={labels} language={language} changeLanguage={changeLanguage} me={me} setMe={setMe} paper={href=>paperBy.get(href)?.id} openPaper={openPaper}/>:null})()}
  {currentView==='kinship'&&<KinshipWords model={model} me={me} language={language} go={go}/>}
  {view==='families'&&<Families data={data} model={model} connected={connected} group={group} go={go} labels={labels} language={language} row={row}/>}
  {currentView==='papers'&&<Papers papers={papers} model={model} me={me} labels={labels} language={language} mode={paperMode} setMode={m=>{setPaperMode(m);scrollTo({top:0})}} of={of} open={openPaper} show={papersOf} go={go} photos={hasPhotos?<div className="photos">
   {album.some(a=>!a.grave)&&<><h2 className="album-head">{t.photosReal}</h2>{albumGrid(album.filter(a=>!a.grave))}</>}
   {period.length>0&&<><h2 className="album-head">{t.photosPeriod}</h2><p className="lead">{t.photosPeriodHint}</p><div className="album period">{period.map(a=><button key={a.asset} onClick={()=>go(a.person,true)}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={a.asset} alt={a.caption} loading="lazy"/><p>{a.caption}<small>{model.info[a.person]?.short}</small></p></button>)}</div></>}
   {album.some(a=>a.grave)&&<><h2 className="album-head">{t.photosGraves}</h2>{albumGrid(album.filter(a=>a.grave))}</>}
  </div>:undefined}/>}
  {paperId&&paperBy.get(paperId)&&<PaperView paper={paperBy.get(paperId)!} list={paperList.map(id=>paperBy.get(id)).filter((x):x is Paper=>!!x)} step={id=>openPaper(id,paperList)} onClose={closePaper} go={go} model={model} me={me} labels={labels} language={language}/>}
  <nav className="tabs-bottom" aria-label={t.title}>{tabs.map(([k,l])=><button className={currentView===k?'active':''} key={k} onClick={()=>show(k)}><Icon name={k}/>{l}</button>)}</nav>
 </div>
}
