import {useMemo} from 'react';
import {kinshipLexicon,kinshipTerm,type Term} from './tree/kinship';
import {isPerson,describeRelation,inLawWords,relationPhrase,type Model,type Relation,type Row} from './tree/model';

/** Words every child knows need no explanation beside them; a rarer one carries it. */
const EVERYDAY=/^(ancestor-[12]|descendant-[12]|collateral-1|uncle|nephew|spouse)-/;
export function kinNote(relation:Relation,language:string){const term=kinshipTerm(relation,language);return term&&!EVERYDAY.test(term.id)?term.explanation:''}
/** The way from the reader to this person, name by name. */
const way=(relation:Relation,model:Model)=>(relation.path||[]).filter(id=>isPerson(model.info[id])).map(id=>model.info[id].short);
const Way=({names,label}:{names:string[];label:string})=><ol className="kinship-path" aria-label={label}>{names.map((name,k)=><li key={k}>{name}</li>)}</ol>;
/** A kinship word where it occurs: a tap says what it means and shows the way in this family's own tree. */
export function KinshipExplanation({relation,model,labels,language}:{relation:Relation;model:Model;labels:Row;language:string}){
 const pack=kinshipLexicon(language),term=kinshipTerm(relation,language),inLaw=term?undefined:inLawWords(relation,language);
 if(!pack)return <span>{relationPhrase(relation,labels,language)}</span>;
 const names=way(relation,model);
 return <details className="kinship-explanation" key={language+relation.path?.join(':')}>
  <summary>{relationPhrase(relation,labels,language)}</summary>
  <div>{term&&<p><b>{term.word}</b>: {term.explanation}{term.archaic&&<> · <em>{pack.archaic}</em></>}</p>}
  {!term&&inLaw&&<p><b>{inLaw.base!.word}</b>: {inLaw.base!.explanation}<br/>{describeRelation(relation,labels,language,true)}</p>}
  {names.length>1&&<Way names={names} label={pack.path}/>}
  {term&&<a href={'#view=kinship&word='+encodeURIComponent(term.id)}>{pack.all} →</a>}</div>
 </details>;
}

/** The words this family needs, each with its own person. A word nobody in the shown tree answers to is not listed. */
export default function KinshipWords({model,me,language,go}:{model:Model;me:string;language:string;go:(id:string,details?:boolean)=>void}){
 const pack=kinshipLexicon(language),from=me&&model.info[me]&&!model.info[me].placeholder?me:model.homes[0]||'';
 const examples=useMemo(()=>{
  const found=new Map<string,{id:string;relation:Relation}>();
  if(!pack||!from)return found;
  for(const person of Object.values(model.info)){
   if(!isPerson(person)||person.id===from)continue;
   const relation=model.relation(from,person.id);if(!relation)continue;
   const term=kinshipTerm(relation,language);if(term&&!found.has(term.id))found.set(term.id,{id:person.id,relation});
  }
  return found;
 },[model,from,language,pack]);
 if(!pack||!examples.size)return null;
 const row=(term:Term)=>{const {id,relation}=examples.get(term.id)!,names=way(relation,model);return <article id={'word-'+term.id} key={term.id} className="kinship-word">
  <h3>{term.word}{term.archaic&&<small> · {pack.archaic}</small>}</h3><p>{term.explanation}</p>
  {names.length>2&&<Way names={names} label={pack.path}/>}
  <button className="chip" onClick={()=>go(id,true)}><b>{model.info[id].short}</b></button>
 </article>};
 const groups=Object.entries(pack.groups).map(([group,title])=>({title,terms:pack.terms.filter(t=>t.group===group&&examples.has(t.id))})).filter(g=>g.terms.length);
 return <section className="page kinship-words"><h1>{pack.title}</h1><p className="lead">{pack.intro.replace('{name}',model.info[from].short)}</p>
  {groups.map(g=><section key={g.title}><h2>{g.title}</h2><div className="kinship-grid">{g.terms.map(row)}</div></section>)}
 </section>;
}
