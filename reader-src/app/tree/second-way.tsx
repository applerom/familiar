'use client';
import type {Model,Row} from './model';
/** One calm line about a second way up the data admit: "son or grandson of A; if grandson, through B", or another parent. */
export function SecondWay({model,id,labels,go}:{model:Model;id:string;labels:Row;go:(id:string)=>void}){
 const r=model.secondWay(id);const words=labels.secondWay;if(!r||!words||!model.info[r.via])return null;
 const g=r.role==='мать'?'f':'m';const text=String(words[r.kind]?.[g]||'');if(!text)return null;
 const name=(pid:string)=><button className="link" onClick={()=>go(pid)}>{model.info[pid].short}</button>;
 const parts=text.split(/(\{a\}|\{b\})/);
 return <small className="second-way">{parts.map((t,i)=>t==='{b}'?<span key={i}>{name(r.via)}</span>:t==='{a}'?<span key={i}>{r.above?name(r.above):null}</span>:t)}</small>;
}
