'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {useZoomPan} from './use-zoom-pan';
import type {Row} from './model';
import type {Region} from './portrait';
export type Doc={sid:string;sourceSid?:string;title:string;reading?:string;asset:string;originalAsset?:string;photo:boolean;view?:'fullPage'|'detail';kind?:number;href?:string;hrefLabel?:string;crop?:Region};
/** Full-screen viewer for scans and photos: zoom with wheel / pinch / buttons, move between a person's documents. */
export default function Lightbox({docs,index,setIndex,onClose,labels}:{docs:Doc[];index:number;setIndex:(i:number)=>void;onClose:()=>void;labels:Row}){
 const box=useRef<HTMLDivElement>(null);const content=useRef({w:1,h:1});const [ready,setReady]=useState(false);
 const {t,setT,moving,zoomBy}=useZoomPan(box,{min:.2,max:8,content,margin:100});
 const doc=docs[index];
 // a print re-shot by phone shows only the print: the frame is the crop, the original bytes stay whole
 const [nat,setNat]=useState<{w:number;h:number}|null>(null);const c=doc.crop;
 const fit=useCallback((w=content.current.w,h=content.current.h)=>{const el=box.current;if(!el||!w)return;const k=Math.min(el.clientWidth/w,el.clientHeight/h,1.6);setT({k,x:(el.clientWidth-w*k)/2,y:(el.clientHeight-h*k)/2})},[setT]);
 useEffect(()=>{setReady(false);setNat(null)},[index]);
 useEffect(()=>{const key=(e:KeyboardEvent)=>{if(e.key==='Escape')onClose();else if(e.key==='ArrowRight'&&index<docs.length-1)setIndex(index+1);else if(e.key==='ArrowLeft'&&index>0)setIndex(index-1)};addEventListener('keydown',key);return()=>removeEventListener('keydown',key)},[index,docs.length,onClose,setIndex]);
 useEffect(()=>{const el=box.current;if(!el)return;const o=new ResizeObserver(()=>fit());o.observe(el);return()=>o.disconnect()},[fit]);
 return <div className="lightbox" role="dialog" aria-modal="true" aria-label={doc.title}>
  <div className="lb-head"><div><small>{index+1} / {docs.length}{doc.hrefLabel?' · '+labels.storyPic:''}</small><p>{doc.title}</p></div><button onClick={onClose} aria-label={labels.close}>×</button></div>
  <div ref={box} className={'lb-stage'+(moving?' moving':'')} onDoubleClick={()=>fit()}>
   {/* eslint-disable-next-line @next/next/no-img-element */}
   {c?<div key={doc.sid} className={'lb-crop'+(ready?' ready':'')} style={{width:nat?c[2]*nat.w:0,height:nat?c[3]*nat.h:0,transform:`translate(${t.x}px,${t.y}px) scale(${t.k})`}}>
    {/* eslint-disable-next-line @next/next/no-img-element */}
    <img src={doc.asset} alt={doc.title} draggable={false} className="ready" style={nat?{left:-c[0]*nat.w,top:-c[1]*nat.h,width:nat.w,height:nat.h}:undefined} onLoad={e=>{const i=e.currentTarget,w=i.naturalWidth,h=i.naturalHeight;setNat({w,h});content.current={w:c[2]*w,h:c[3]*h};fit(c[2]*w,c[3]*h);setReady(true)}}/>
   </div>
   :<img key={doc.sid} src={doc.asset} alt={doc.title} draggable={false} className={ready?'ready':''} style={{transform:`translate(${t.x}px,${t.y}px) scale(${t.k})`}} onLoad={e=>{const i=e.currentTarget;content.current={w:i.naturalWidth,h:i.naturalHeight};fit(i.naturalWidth,i.naturalHeight);setReady(true)}}/>}
  </div>
  {doc.reading&&<p className="lb-reading">{doc.reading}</p>}
  <div className="lb-foot">
   <button onClick={()=>setIndex(index-1)} disabled={index===0} aria-label={labels.prev}>‹</button>
   <button onClick={()=>zoomBy(1/1.4)} aria-label={labels.zoomOut}>−</button><button onClick={()=>zoomBy(1.4)} aria-label={labels.zoomIn}>+</button><button onClick={()=>fit()} aria-label={labels.recenter}>⤢</button>
   <a href={doc.href||doc.originalAsset||doc.asset} target="_blank" rel="noreferrer">{doc.hrefLabel||labels.openOriginal} ↗</a>
   <button onClick={()=>setIndex(index+1)} disabled={index>=docs.length-1} aria-label={labels.next}>›</button>
  </div>
 </div>
}
