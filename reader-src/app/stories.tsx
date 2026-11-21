'use client';
import {useMemo} from 'react';
import {inLanguage} from './reader-profile';
import {kinPhrase,lifeLabel,lineTitle,placeLabel,type Model,type Row} from './tree/model';
import type {Language} from './i18n';
import {FeedCovers,type Feed} from './feed';
const GRAVE=/памятник|могил|надгроб|grave|nagrob|· документ$/i;
/** The simple, child-first part of a story: the text before the `---` line, or the whole story. */
export function storyText(story:any,language:string){return inLanguage(story,language)}
export function storyParts(text:string){const [simple,more]=text.split(/\n-{3,}\n/);return {simple:(simple||'').trim(),more:(more||'').trim()}}
/** The picture that opens a story: a period picture, a family photograph, else the readable crop of the person's own record. */
export function storyPicture(p:Row):{asset:string;kind:'period'|'photo'|'record'}|null{
 const ill=(p.illustrations||[]).find((s:Row)=>s.asset);if(ill)return {asset:ill.asset,kind:'period'};
 const photo=(p.media||[]).find((m:Row)=>m.photo&&m.asset&&m.type!=='grave'&&!GRAVE.test(m.title||''));if(photo)return {asset:photo.asset,kind:'photo'};
 const crop=(p.media||[]).find((m:Row)=>!m.photo&&m.asset&&m.originalAsset&&m.originalAsset!==m.asset);if(crop)return {asset:crop.asset,kind:'record'};
 return null;
}
const cap=(s:string)=>s.charAt(0).toLocaleUpperCase()+s.slice(1);
/** One page with every story: grouped by the four ancestor lines, oldest first, each with its picture and a first taste of the text. */
export default function Stories({data,model,go,labels,language,openFeed}:{data:Row;model:Model;go:(id:string,details?:boolean)=>void;labels:Row;language:Language;openFeed:(id:string)=>void}){
 const groups=useMemo(()=>{
  const by=new Map<number,string[]>();
  for(const [id,i] of Object.entries(model.info)){if(!i.story||i.placeholder)continue;const tone=model.tone(id);const key=tone?tone.line:-1;(by.get(key)||by.set(key,[]).get(key)!).push(id)}
  const byYear=(a:string,b:string)=>(model.info[a].birth??9999)-(model.info[b].birth??9999)||model.info[a].short.localeCompare(model.info[b].short,language);
  const out=model.lines.map((l,idx)=>({key:idx,color:l.color,title:lineTitle(l,model,labels),people:(by.get(idx)||[]).sort(byYear)})).filter(g=>g.people.length);
  const rest=(by.get(-1)||[]).sort(byYear);if(rest.length)out.push({key:-1,color:'#9fb09c',title:labels.othersGroup,people:rest});
  return out},[model,labels,language]);
 const updates:Row[]=(data.research?.updates||[]).slice(0,3);
 const card=(id:string)=>{const p=data.people[id];const i=model.info[id];const pic=storyPicture(p);const {simple}=storyParts(storyText(p.story,language));const tone=model.tone(id);const kin=model.kinship(id).map(k=>kinPhrase(k,labels,language))[0];
  const line=[lifeLabel(i,labels,language),placeLabel(i,labels)].filter(Boolean).join(' · ');
  return <button key={id} className={'story-card'+(pic?' pic-'+pic.kind:'')} onClick={()=>go(id,true)}>
   {pic&&/* eslint-disable-next-line @next/next/no-img-element */<img src={pic.asset} alt="" loading="lazy"/>}
   <span className="story-text"><strong>{!pic&&<span className={'av'+(tone?.kin?' line-kin':'')} style={tone?{background:tone.color}:undefined} aria-hidden="true">{i.short.slice(0,1)}</span>}{i.short}</strong>{(line||kin)&&<small>{[line,kin].filter(Boolean).join(' · ')}</small>}<p>{simple}</p><em>{labels.readStory} →</em></span>
  </button>};
 return <section className="page stories">
  <h1>{labels.storiesTitle}</h1><p className="lead">{labels.storiesHint}</p>
  <FeedCovers feeds={(data.feeds||[]).filter((f:Feed)=>f.chapters?.length)} labels={labels} language={language} open={openFeed}/>
  {(groups.length>0||(data.feeds||[]).some((f:Feed)=>f.chapters?.length))&&updates.length>0&&<section className="whats-new"><h2>{labels.whatsNew}</h2>{updates.map((u:Row,k:number)=><button key={k} className="update" onClick={()=>data.people[u.person]&&go(u.person,true)} disabled={!data.people[u.person]}><small>{u.date}</small><b>{u.title}</b><span>{u.text}</span></button>)}</section>}
  {groups.map(g=><section key={g.key} className="story-line" style={{'--b':g.color} as React.CSSProperties}><h2><i aria-hidden="true"/>{g.title}</h2><div className="story-grid">{g.people.map(card)}</div></section>)}
 </section>
}
