import {useEffect,useRef,useState,type ReactNode} from 'react';
import './page-top.css';

/** Everything that is not one of the four places of the lower row waits here, one tap away on every page.
 *  A desk brings its own links (investigation, remark, private notice) as static HTML; they are shown in place. */
function More({label,children}:{label:string;children?:ReactNode}){
 const [open,setOpen]=useState(false);const box=useRef<HTMLDivElement>(null),slot=useRef<HTMLDivElement>(null);
 useEffect(()=>{const desk=document.getElementById('desk-more');if(desk&&slot.current){desk.hidden=false;slot.current.append(desk)}},[]);
 useEffect(()=>{if(!open)return;
  const away=(e:Event)=>{if(!box.current?.contains(e.target as Node))setOpen(false)},key=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.stopImmediatePropagation();setOpen(false)}};
  addEventListener('pointerdown',away);addEventListener('keydown',key,true);addEventListener('hashchange',close);
  function close(){setOpen(false)}
  return()=>{removeEventListener('pointerdown',away);removeEventListener('keydown',key,true);removeEventListener('hashchange',close)}},[open]);
 return <div className="page-more" ref={box}>
  <button className="page-more-btn" aria-expanded={open} aria-controls="page-more-panel" onClick={()=>setOpen(!open)}>{label}</button>
  <div id="page-more-panel" className="page-more-panel" hidden={!open} onClick={e=>{if((e.target as HTMLElement).closest('a,button'))setOpen(false)}}><div ref={slot} className="page-more-desk"/>{children}</div>
 </div>
}

/** The same page frame for the reader and supplemental desk screens: the family's name leads home. */
export default function PageTop({title,home,onHome,navigation,search,language,notice,more,moreItems}:{title:string;home:string;onHome?:()=>void;navigation?:ReactNode;search?:ReactNode;language?:ReactNode;notice?:string;more?:string;moreItems?:ReactNode}){
 return <>{notice&&<aside className="page-fictional" role="note">{notice}</aside>}<header className="page-top"><a className="page-brand" href={home} onClick={onHome?e=>{e.preventDefault();onHome()}:undefined}><span className="page-logo" aria-hidden="true"><svg viewBox="0 0 28 28"><circle cx="14" cy="14" r="11" fill="none" stroke="currentColor" strokeWidth="1.5"/><circle cx="19" cy="9" r="3"/></svg></span><span>{title}</span></a>{navigation}{search&&<span className="page-search">{search}</span>}{language&&<span className="page-language">{language}</span>}{more&&<More label={more}>{moreItems}</More>}</header></>;
}

export function familyHeading(title:string,homes:string[]){
 return /^Familiar(?:\s*[—–-].*)?$/i.test(title)?[...new Set(homes.filter(Boolean))].join(' · ')||title:title;
}
/** Only a family without a name of its own needs its people for the heading. */
export const namesItself=(title:string)=>!/^Familiar(?:\s*[—–-].*)?$/i.test(title);
