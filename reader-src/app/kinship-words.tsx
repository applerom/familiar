import {useMemo} from 'react';
import {kinshipLexicon,kinshipTerm,type Term} from './tree/kinship';
import {relationPhrase,type Model,type Relation,type Row} from './tree/model';

/** The public reader graph is the only source of names and example paths. */
export function KinshipExplanation({relation,model,labels,language}:{relation:Relation;model:Model;labels:Row;language:string}){
 const pack=kinshipLexicon(language),term=kinshipTerm(relation,language);
 if(!pack)return <span>{relationPhrase(relation,labels,language)}</span>;
 const path=(relation.path||[]).filter(id=>model.info[id]&&!model.info[id].placeholder).map(id=>model.info[id].short).join(' → ');
 return <details className="kinship-explanation" key={language+relation.path?.join(':')}>
  <summary title={term?`${term.word}: ${term.explanation}`:undefined}>{relationPhrase(relation,labels,language)}</summary>
  {term&&<p><b>{term.word}</b>: {term.explanation}{term.archaic&&<> · <em>{pack.archaic}</em></>}</p>}
  {path&&<p className="kinship-path"><b>{pack.path}</b><br/>{path}</p>}
  <a href={'#view=kinship'+(term?'&word='+encodeURIComponent(term.id):'')}>{pack.title} →</a>
 </details>;
}

export default function KinshipWords({model,me,language,labels,go}:{model:Model;me:string;language:string;labels:Row;go:(id:string,details?:boolean)=>void}){
 const pack=kinshipLexicon(language);
 const examples=useMemo(()=>{
  const found=new Map<string,{id:string;relation:Relation}>();
  if(!pack||!model.info[me]||model.info[me].placeholder)return found;
  for(const person of Object.values(model.info)){
   if(person.placeholder||person.id===me)continue;
   const relation=model.relation(me,person.id);if(!relation)continue;
   const term=kinshipTerm(relation,language);if(term&&!found.has(term.id))found.set(term.id,{id:person.id,relation});
  }
  return found;
 },[model,me,language,pack]);
 if(!pack)return null;
 const termRow=(term:Term)=>{const example=examples.get(term.id);return <article id={'word-'+term.id} key={term.id} className="kinship-word">
  <h3>{term.word}{term.archaic&&<small> · {pack.archaic}</small>}</h3><p>{term.explanation}</p>
  {example?<p className="kinship-example">{pack.example}: <button className="link" onClick={()=>go(example.id,true)}>{model.info[example.id].short}</button>{!example.relation.sure&&<> · {pack.maybe.trim()}</>}<small>{(example.relation.path||[]).map(id=>model.info[id]?.short).filter(Boolean).join(' → ')}</small></p>:<p className="note">{model.info[me]?pack.noExample:pack.chooseViewer}</p>}
 </article>};
 return <section className="page kinship-words"><h1>{pack.title}</h1><p className="lead">{pack.intro}</p>
  {model.info[me]&&<p className="kinship-viewer">{labels.meFrom}: <button className="link" onClick={()=>go(me,true)}>{model.info[me].short}</button></p>}
  <nav className="kinship-groups" aria-label={pack.title}>{Object.entries(pack.groups).map(([id,title])=><a key={id} href={'#view=kinship&group='+id} onClick={()=>requestAnimationFrame(()=>document.getElementById('kin-group-'+id)?.scrollIntoView())}>{title}</a>)}</nav>
  {Object.entries(pack.groups).map(([group,title])=><section key={group} id={'kin-group-'+group}><h2>{title}</h2><div className="kinship-grid">{pack.terms.filter(t=>t.group===group).sort((a,b)=>Number(examples.has(b.id))-Number(examples.has(a.id))||a.word.localeCompare(b.word,language)).map(termRow)}</div></section>)}
 </section>;
}
