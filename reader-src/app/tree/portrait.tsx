'use client';
import {useEffect,useRef,useState,type CSSProperties} from 'react';
import type {Row} from './model';
/** A region of a picture in its own coordinates: x, y, width, height as fractions of the whole. */
export type Region=[number,number,number,number];
/** The photograph that stands for a person: the family's own picture, with the face where the host marked it. */
export type Portrait={sid:string;asset:string;title:string;face?:Region;crop?:Region;subjects:number;original?:string};
export const region=(v:unknown):Region|undefined=>Array.isArray(v)&&v.length===4&&v.every(n=>typeof n==='number')?v as Region:undefined;
/**
 * The family's photograph of this person, if the reader may see one: a marked face first, then a picture of them
 * alone, then any; a portrait the house restored stands with its original one tap away. A grave and a period
 * illustration never stand for a face.
 */
export function portraitOf(p:Row):Portrait|undefined{
 const own=(p.media||[]).filter((m:Row)=>m.asset&&m.photo&&m.kind==='family-photograph').map((m:Row,i:number)=>({m,i}));
 own.sort((a:Row,b:Row)=>Number(!(a.m.is_portrait||region(a.m.face)))-Number(!(b.m.is_portrait||region(b.m.face)))||(a.m.subjects?.length||1)-(b.m.subjects?.length||1)||a.i-b.i);
 const m=own[0]?.m;
 if(m)return {sid:m.sid,asset:m.asset,title:m.title||m.caption||'',face:region(m.face),crop:region(m.crop),subjects:m.subjects?.length||1};
 const restored=[...(p.media||[]),...(p.illustrations||[])].find((x:Row)=>x.ours?.kind==='photo-restoration'&&x.ours.versions?.length);
 if(!restored)return;
 const v=restored.ours.versions.find((x:Row)=>x.id===restored.ours.primary)||restored.ours.versions[0];
 return v?.asset?{sid:'restored:'+(restored.ours.id||v.asset),asset:v.asset,title:v.caption||restored.caption||'',subjects:1,original:restored.asset}:undefined;
}
/**
 * A part of a picture drawn into its box (the box takes its size from the page): the face region filling a circle,
 * or the cropped print. Without a region the picture covers the box from its upper third, where faces usually are.
 * `fit` shows the whole region inside the box instead of filling it.
 */
export function Face({portrait,className,alt='',fit=false,face=true}:{portrait:Portrait;className?:string;alt?:string;fit?:boolean;face?:boolean}){
 const el=useRef<HTMLSpanElement>(null);
 const [nat,setNat]=useState<{w:number;h:number}|null>(null);
 const [size,setSize]=useState<{w:number;h:number}|null>(null);
 useEffect(()=>{const box=el.current;if(!box)return;const measure=()=>setSize({w:box.clientWidth,h:box.clientHeight});measure();
  const o=new ResizeObserver(measure);o.observe(box);return()=>o.disconnect()},[]);
 const r=(face&&portrait.face)||portrait.crop;
 let style:CSSProperties={width:'100%',height:'100%',objectFit:fit?'contain':'cover',objectPosition:'50% 30%'};
 if(r&&nat&&size?.w){
  const rw=r[2]*nat.w,rh=r[3]*nat.h,s=(fit?Math.min:Math.max)(size.w/rw,size.h/rh);
  style={position:'absolute',maxWidth:'none',width:nat.w*s,height:nat.h*s,left:size.w/2-(r[0]+r[2]/2)*nat.w*s,top:size.h/2-(r[1]+r[3]/2)*nat.h*s};
 }
 return <span ref={el} className={'face'+(className?' '+className:'')}>
  {/* eslint-disable-next-line @next/next/no-img-element */}
  <img src={portrait.asset} alt={alt} draggable={false} loading="lazy" style={{...style,opacity:r&&!(nat&&size?.w)?0:1}}
   onLoad={e=>setNat({w:e.currentTarget.naturalWidth,h:e.currentTarget.naturalHeight})}/>
 </span>;
}
