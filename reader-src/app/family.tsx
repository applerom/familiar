'use client';
import {readerStorage,profile,siteURL} from './reader-profile';
import {useEffect,useMemo,useState} from 'react';
import KinshipWords from './kinship-words';
import {kinshipLexicon} from './tree/kinship';
import TreeStage from './tree/tree-stage';
import PersonPanel from './tree/person-panel';
import Families from './families';
import Stories from './stories';
import WorldMap,{worldText} from './world-map';
import {FeedViewer,type Feed} from './feed';
import LanguagePicker from './language-picker';
import PageTop,{familyHeading} from './page-top';
import {SearchSheet,SearchButton} from './search';
import {MiniMap,OverviewDialog,buildOverview} from './tree/overview';
import {growthWords} from './tree/growth';
import {buildModel,kinPhrase,lifeLabel,placeLabel,relationPhrase} from './tree/model';

import {translations,type Language} from './i18n';
type Row=Record<string,any>;
const ICONS:Record<string,React.ReactNode>={tree:<><circle cx="12" cy="5" r="2.5"/><circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="M12 7.5V12M12 12 6.8 16.6M12 12l5.2 4.6"/></>,stories:<><path d="M3 5.5A2.5 2.5 0 0 1 5.5 3H11v16H5.5A2.5 2.5 0 0 0 3 21z"/><path d="M21 5.5A2.5 2.5 0 0 0 18.5 3H13v16h5.5A2.5 2.5 0 0 1 21 21z"/></>,families:<><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-4 3.4-6 6.5-6s5.9 2 6.5 6"/><circle cx="17.5" cy="9" r="2.5"/><path d="M17 14c2.5.2 4 2 4.5 5"/></>,photos:<><rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="9" cy="10.5" r="1.8"/><path d="m4 17 5-4.5 4 3.5 3-2.5 4 3.5"/></>};
ICONS.kinship=<><path d="M4 4h7v16H4zM13 4h7v16h-7zM7 8h1M7 12h1M16 8h1M16 12h1"/></>;
ICONS.world=<><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6h14M5 18h14"/></>;
const Icon=({name}:{name:string})=><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[name]}</svg>;
const GRAVE=/памятник|могил|надгроб|grave|nagrob|· документ$/i;
export default function Family({initialData}:{initialData:Row}){
 const data=initialData;const [id,select]=useState('');const [view,V]=useState('tree');const [language,L]=useState<Language>(profile().family.source_language);const [expanded,Expand]=useState(false);const [map,Map_]=useState(false);const [visible,setVisible]=useState<Set<string>>(new Set());const [hint,setHint]=useState(false);const [fine,setFine]=useState(false);const [me,setMeState]=useState(initialData.defaultViewer||initialData.narrator||'');const [feed,setFeed]=useState<{id:string;step:number}|null>(null);const [finding,Find]=useState(false);const base=translations[language];const title=profile().family.title;const t={...base,...(language===profile().family.source_language?data.readerLabels:{}),title:typeof title==='string'?title:title[language]||base.title,homeGenitive:profile().reader_names?.[language]||{}};
 // "me" is who is looking at the tree: from a personal link (#person=…&me=…) or chosen in the panel, remembered in this browser
 const setMe=(pid:string)=>{setMeState(pid);try{readerStorage.setItem('family-me',pid)}catch{}};
 const [undo,setUndo]=useState<{name:string}|null>(null);
 useEffect(()=>{if(!undo)return;const timer=setTimeout(()=>setUndo(null),6000);return()=>clearTimeout(timer)},[undo]);
 useEffect(()=>{try{const saved=readerStorage.getItem('family-language');if(saved&&profile().family.languages.includes(saved as Language))L(saved as Language);if(!readerStorage.getItem('tree-hint-seen'))setHint(true);setFine(matchMedia('(pointer: fine)').matches);const m=readerStorage.getItem('family-me');if(m!==null)setMeState(m)}catch{}const change=()=>{const q=new URLSearchParams(location.hash.slice(1));const p=q.get('person');const m=q.get('me');const v=q.get('view');const f=q.get('feed');if(m)setMe(m);if(f){V('stories');setFeed({id:f,step:Math.max(0,(parseInt(q.get('step')||'1',10)||1)-1)});return}setFeed(null);if(p){select(p);V('tree');Map_(false);Expand(q.get('details')==='1')}else if(v&&['tree','stories','world','families','photos','kinship'].includes(v))V(v);else{select('');V('tree');Expand(false)}};change();addEventListener('hashchange',change);return()=>removeEventListener('hashchange',change)},[]);// eslint-disable-line react-hooks/exhaustive-deps
 useEffect(()=>{const key=(e:KeyboardEvent)=>{const el=e.target as HTMLElement;if(/INPUT|TEXTAREA|SELECT/.test(el.tagName))return;if(e.key==='/'||((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k')){e.preventDefault();Find(true)}};addEventListener('keydown',key);return()=>removeEventListener('keydown',key)},[]);
 useEffect(()=>{if(view!=='kinship')return;const q=new URLSearchParams(location.hash.slice(1));const word=q.get('word'),group=q.get('group');if(word||group)requestAnimationFrame(()=>document.getElementById(word?'word-'+word:'kin-group-'+group)?.scrollIntoView())},[view,language]);
 useEffect(()=>{document.documentElement.lang=language;document.title=view==='world'?worldText[language].title+' · '+t.title:t.title},[language,t.title,view]);
 const model=useMemo(()=>data?buildModel(data,t):null,[data,language]);
 const overview=useMemo(()=>model&&map?buildOverview(model):null,[model,map]);
 const mini=useMemo(()=>model&&view==='tree'?buildOverview(model):null,[model,view]);
 // everyone reachable from the two home people through parents, children, partners and sibling links
 const connected=useMemo(()=>{const set=new Set<string>();if(!data||!model)return set;const adjacent:Record<string,string[]>={};function join(a:string,b:string){if(!a||!b)return;(adjacent[a]??=[]).push(b);(adjacent[b]??=[]).push(a)}
  data.edges.filter((e:Row)=>!['rejected','disproved'].includes(e.status)).forEach((e:Row)=>join(e.child,e.parent));(data.families||[]).forEach((f:Row)=>join(f.husband,f.wife));(data.associations||[]).filter((a:Row)=>a.type==='sibling'||a.type==='possible_parent'||a.type==='spouse').forEach((a:Row)=>join(a.from,a.to));
  const todo=[...model.homes];while(todo.length){const x=todo.pop()!;if(set.has(x)||!model.info[x]||model.info[x].placeholder)continue;set.add(x);todo.push(...(adjacent[x]||[]).filter((y:string)=>!set.has(y)))}return set},[data,model]);
 function changeLanguage(value:Language){L(value);try{readerStorage.setItem('family-language',value)}catch{}}
 // open a person in the tree; `details` opens the card itself (the story) on a phone, where the card starts folded
 function go(pid:string,details=false){Find(false);V('tree');select(pid);location.hash='person='+encodeURIComponent(pid)+(details?'&details=1':'');Expand(details);seenHint()}
 function seenHint(){if(hint){setHint(false);try{readerStorage.setItem('tree-hint-seen','1')}catch{}}}
 function show(v:string){Find(false);V(v);Map_(false);if(location.hash&&!location.hash.includes('person='))history.replaceState(null,'','#view='+v);else if(v!=='tree')history.pushState(null,'','#view='+v)}
 // a historical feed opens over the Stories page; the chapter lives in the hash so a link can point at it
 function openFeed(fid:string,step=0){setFeed({id:fid,step});V('stories');history.pushState(null,'','#feed='+encodeURIComponent(fid)+'&step='+(step+1))}
 function closeFeed(){setFeed(null);history.replaceState(null,'','#view=stories')}
 if(!data||!model)return <main className="loading">{t.opening}</main>;
 const labels:Row={...t,status:{verified:t.document,export:t.family,hypothesis:t.familyUncertain,conflict:t.conflict}};
 const people=data.people;const resolvedId=data.identityAliases?.[id]||data.presentationAliases?.[id]||id;const home=data.root||model.homes[0];const personId=people[resolvedId]?resolvedId:home;
 const group=(pid:string)=>connected.has(pid)?'family':['refuted_relationship','withdrawn_relationship','split_identity'].includes(data.cardStatuses[pid]?.review?.kind)?'archive':'context';
 const row=(pid:string,kin?:string)=>{const i=model.info[pid];if(!i||i.placeholder)return null;const tone=model.tone(pid);const line=[kin,data.people[pid]?.disambiguator?.[language],lifeLabel(i,t,language)||i.note,placeLabel(i,t)].filter(Boolean).join(' · ');return <button key={pid} className="person-row" onClick={()=>go(pid)}><span className={'av'+(tone?.kin?' line-kin':'')} style={tone?{background:tone.color}:undefined}>{i.name.slice(0,1)}</span><span><strong>{i.short}{i.maidenShown&&<small className="maiden" title={t.maidenLabel+': '+i.maidenShown}> ({i.maidenShown})</small>}{i.story&&<i className="st-dot" title={t.hasStory} aria-label={t.hasStory}/>}</strong>{line&&<small>{line}</small>}</span></button>};
 // who this person is: from the viewer when chosen, otherwise from the two home people
 const kinOf=(pid:string)=>{const from=me&&model.info[me]?me:'';const r=from&&from!==pid?model.relation(from,pid):null;if(r)return relationPhrase(r,labels,language);const k=model.kinship(pid)[0];return k?kinPhrase(k,labels,language):''};
 // pictures attached to people: family photographs, gravestones and the editorial period pictures from the stories
 const album=(()=>{const byPic=new Map<string,{asset:string;title:string;people:string[];grave:boolean}>();for(const p of Object.values<Row>(people)){for(const m of p.media||[]){if(!m.photo||!m.asset)continue;const e=byPic.get(m.asset)||byPic.set(m.asset,{asset:m.asset,title:m.title||'',people:[],grave:m.type==='grave'||GRAVE.test(m.title||'')}).get(m.asset)!;if(!e.people.includes(p.id))e.people.push(p.id)}}return [...byPic.values()]})();
 const period=(()=>{const seen=new Set<string>();const out:{asset:string;caption:string;person:string}[]=[];for(const p of Object.values<Row>(people))for(const s of p.illustrations||[]){if(!s.asset||seen.has(s.asset))continue;seen.add(s.asset);out.push({asset:s.asset,caption:s.caption?.[language]||s.caption?.en||s.caption?.ru||s.caption||'',person:p.id})}return out})();
 const albumGrid=(items:typeof album)=><div className="album">{items.map(a=><button key={a.asset} onClick={()=>a.people[0]&&go(a.people[0])}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={a.asset} alt={a.people.map(p=>model.info[p].short).join(', ')} loading="lazy"/><p>{a.people.map(p=>model.info[p].short).join(', ')||a.title}</p></button>)}</div>;
 const hasStories=(data.feeds||[]).some((f:Feed)=>f.chapters?.length)||Object.values(model.info).some(p=>p.story&&!p.placeholder);
 const hasPhotos=album.length>0||period.length>0;
 const currentView=(view==='stories'&&!hasStories||view==='photos'&&!hasPhotos||view==='kinship'&&!kinshipLexicon(language))?'tree':view;
 const tabs:[string,string][]=[['tree',t.tree],...(hasStories?[['stories',t.stories] as [string,string]]:[]),...(data.worldMap?[['world',worldText[language].nav] as [string,string]]:[]),['families',t.families],...(kinshipLexicon(language)?[['kinship',kinshipLexicon(language)!.title] as [string,string]]:[]),...(hasPhotos?[['photos',t.photos] as [string,string]]:[])];
 const gw=growthWords[language]||growthWords.en;const growthRows=Object.values(model.info).map(i=>i.growth);
 const growthSummary=growthRows.length?`${gw.people} ${growthRows.length} ${gw.peopleUnit}`:'';
 const familyTitle=familyHeading(t.title,model.homes.map(h=>model.info[h]?.surnameKey));
 return <div className={'shell v-'+currentView} data-feedback-screen={finding?'search':currentView}>
  <PageTop title={familyTitle} home={siteURL('#view=tree')} onHome={()=>go(home)} notice={profile().family.fictional?t.fictionalDemo:undefined} navigation={<nav className="tabs-top" aria-label={t.title}>{tabs.map(([k,l])=><button className={currentView===k?'active':''} key={k} onClick={()=>show(k)}>{l}</button>)}</nav>} search={<SearchButton open={finding} label={t.find} onClick={()=>Find(!finding)}/>} language={<LanguagePicker languages={profile().family.languages} language={language} label={t.language} onChange={changeLanguage}/>}/>
  {finding&&<SearchSheet data={data} model={model} group={group} row={id=>row(id,kinOf(id))} labels={labels} onClose={()=>Find(false)}/>}
  {currentView==='tree'&&<div className="tree-body">
   <div className="growth-summary">{growthSummary}</div>
   <TreeStage model={model} me={me} id={personId} go={go} jump={pid=>{setUndo({name:model.info[personId].short});go(pid)}} onUse={seenHint} labels={labels} onLayout={l=>setVisible(l.visible)}>
    {mini&&<MiniMap ov={mini} model={model} visible={visible} center={personId} onOpen={()=>Map_(true)} label={t.map}/>}
    {hint&&<p className="hint" role="note">{<><span className="hint-wide">{fine?t.hintDesktop:t.hint}</span><span className="hint-narrow">{t.hint}</span></>}</p>}
   </TreeStage>
   <PersonPanel data={data} model={model} id={personId} go={go} labels={labels} language={language} expanded={expanded} setExpanded={Expand} me={me} setMe={setMe} openFeed={openFeed}/>
  </div>}
  {map&&overview&&<OverviewDialog ov={overview} model={model} visible={visible} center={personId} go={pid=>{if(pid!==personId)setUndo({name:model.info[personId].short});go(pid,true)}} onClose={()=>Map_(false)} labels={labels} language={language} me={me}/>}
  {undo&&<button className="person-undo" onClick={()=>{history.back();setUndo(null)}}>← {t.backToPerson.replace('{name}',undo.name)}</button>}
  {currentView==='stories'&&<Stories data={data} model={model} go={go} labels={labels} language={language} openFeed={openFeed}/>}
  {view==='world'&&<WorldMap atlas={data.worldMap} language={language} go={go} openFeed={openFeed} feeds={data.feeds||[]}/>}
  {feed&&(()=>{const f=(data.feeds||[]).find((x:Feed)=>x.id===feed.id);return f?<FeedViewer feed={f} step={feed.step} setStep={n=>openFeed(f.id,n)} onClose={closeFeed} go={go} model={model} labels={labels} language={language} changeLanguage={changeLanguage} me={me} setMe={setMe}/>:null})()}
  {view==='kinship'&&<KinshipWords model={model} me={me} language={language} labels={labels} go={go}/>}
  {view==='families'&&<Families data={data} model={model} connected={connected} group={group} go={go} labels={labels} language={language} row={row}/>}
  {currentView==='photos'&&<section className="page photos"><h1>{t.photoTitle}</h1><p className="lead">{t.photoHint}</p>
   {album.some(a=>!a.grave)&&<><h2 className="album-head">{t.photosReal}</h2>{albumGrid(album.filter(a=>!a.grave))}</>}
   {period.length>0&&<><h2 className="album-head">{t.photosPeriod}</h2><p className="lead">{t.photosPeriodHint}</p><div className="album period">{period.map(a=><button key={a.asset} onClick={()=>go(a.person,true)}>{/* eslint-disable-next-line @next/next/no-img-element */}<img src={a.asset} alt={a.caption} loading="lazy"/><p>{a.caption}<small>{model.info[a.person]?.short}</small></p></button>)}</div></>}
   {album.some(a=>a.grave)&&<><h2 className="album-head">{t.photosGraves}</h2>{albumGrid(album.filter(a=>a.grave))}</>}
  </section>}
  <nav className="tabs-bottom" aria-label={t.title}>{tabs.map(([k,l])=><button className={currentView===k?'active':''} key={k} onClick={()=>show(k)}><Icon name={k}/>{l}</button>)}</nav>
 </div>
}
