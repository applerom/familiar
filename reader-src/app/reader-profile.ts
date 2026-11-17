import type {Language} from './i18n';
export type ReaderProfile={schema_version:1;family:{id:string;title:string|Partial<Record<Language,string>>;source_language:Language;languages:Language[];fictional:boolean};data:string;reader_names?:Partial<Record<Language,Record<string,string>>>;legacy_storage?:boolean;host?:{feedback?:'disabled'|'api'}};
let active:ReaderProfile|undefined;
let account='';
export function profile(){if(!active)throw Error('Reader profile is not loaded');return active}
/** Private delivery is labelled by the engine, in the family's language pack. */
export function privateNotice(){return typeof document==='undefined'?'':document.getElementById('host-private-notice')?.textContent||''}
export function feedbackEnabled(){const p=profile();return !document.querySelector('meta[name="familiar-static-demo"]')&&(!!document.getElementById('desk-footer')||!p.family.fictional&&(p.host?.feedback==='api'||(p.host?.feedback===undefined&&p.legacy_storage===true)))}
export function siteURL(path:string){return new URL(path,new URL('../',import.meta.url)).href}
const keys=['family-me','family-language','tree-hint-seen','reader-feed-mode','reader-play-mute','reader-chest'];
export function storageKey(key:string){const p=profile();return `familiar:${encodeURIComponent(p.family.id)}:${p.family.fictional?'fictional':'private'}:${account?account+':':''}${key}`}
export const readerStorage={getItem:(key:string)=>localStorage.getItem(storageKey(key)),setItem:(key:string,value:string)=>localStorage.setItem(storageKey(key),value),removeItem:(key:string)=>localStorage.removeItem(storageKey(key))};
export async function loadReader(url=siteURL('reader-profile.json')){
 const response=await fetch(url);if(!response.ok)throw Error('Reader profile unavailable');const p=await response.json() as ReaderProfile;
 if(p.schema_version!==1||!p.family?.id||!p.family.title||!p.family.languages?.length||!p.family.languages.includes(p.family.source_language)||p.family.languages.some(l=>!['ru','pl','en','sv'].includes(l))||!p.data||p.family.fictional&&p.legacy_storage)throw Error('Invalid reader profile');
 active=p;
 const identity=await (window as any).familiarDeskIdentity;
 if(identity?.sub){account=identity.sub;try{if(readerStorage.getItem('desk-login')!==identity.login){readerStorage.setItem('family-me',identity.person||'');readerStorage.setItem('desk-login',identity.login)}}catch{}}
 if(p.legacy_storage)try{for(const key of keys){const old=localStorage.getItem(key);if(old!==null&&readerStorage.getItem(key)===null)readerStorage.setItem(key,old)}}catch{}
 const r=await fetch(new URL(p.data,new URL(url,location.href)));if(!r.ok)throw Error('Reader data unavailable');const x=await r.json() as Record<string,any>;
 if(!x.people||typeof x.people!=='object'||Array.isArray(x.people))throw Error('Invalid reader graph');
 return {profile:p,data:{edges:[],families:[],sources:{},cardStatuses:{},feeds:[],associations:[],...x}};
}
