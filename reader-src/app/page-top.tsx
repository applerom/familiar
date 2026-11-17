import type {ReactNode} from 'react';
import './page-top.css';

/** The same page frame for the reader and supplemental desk screens. */
export default function PageTop({title,home,onHome,navigation,search,language,notice}:{title:string;home:string;onHome?:()=>void;navigation?:ReactNode;search?:ReactNode;language?:ReactNode;notice?:string}){
 return <>{notice&&<aside className="page-fictional" role="note">{notice}</aside>}<header className="page-top"><a className="page-brand" href={home} onClick={onHome?e=>{e.preventDefault();onHome()}:undefined}><span className="page-logo" aria-hidden="true"><svg viewBox="0 0 28 28"><circle cx="14" cy="14" r="11" fill="none" stroke="currentColor" strokeWidth="1.5"/><circle cx="19" cy="9" r="3"/></svg></span><span>{title}</span></a>{navigation}<span className="page-search">{search}</span><span className="page-language">{language}</span></header></>;
}

export function familyHeading(title:string,homes:string[]){
 return /^Familiar(?:\s*[—–-].*)?$/i.test(title)?[...new Set(homes.filter(Boolean))].join(' · ')||title:title;
}
