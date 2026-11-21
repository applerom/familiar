import {inLanguage} from './reader-profile';
/** Card texts a translator carried into the reader's language arrive as language rows; the reader sees one language. */
export function localizeGraph(data:any,lang:string){
 const t=(v:any)=>v&&typeof v==='object'&&!Array.isArray(v)?inLanguage(v,lang):v;
 const fact=(f:any)=>({...f,label:t(f.label),text:t(f.text),basis:t(f.basis)});
 const people=Object.fromEntries(Object.entries<any>(data.people||{}).map(([id,p])=>[id,{...p,summary:t(p.summary),
  facts:p.facts?.map(fact),retiredFacts:p.retiredFacts?.map(fact),events:p.events?.map((e:any)=>({...e,place:t(e.place)})),
  cardPresentation:p.cardPresentation&&{...p.cardPresentation,place:t(p.cardPresentation.place)}}]));
 const sources=Object.fromEntries(Object.entries<any>(data.sources||{}).map(([id,s])=>[id,{...s,title:t(s.title),asset:s.assetIn?.[lang]||s.asset}]));
 const research=data.research&&{...data.research,updates:data.research.updates?.map(fact),highlights:data.research.highlights?.map(fact)};
 return {...data,people,sources,...(research?{research}:{})};
}
