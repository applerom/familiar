import type {Language} from './i18n';

const NAMES:Record<string,string>={ru:'Русский',pl:'Polski',en:'English',sv:'Svenska'};
/** One language offers no choice, so nothing is shown. */
export default function LanguagePicker({languages,language,label,onChange,names=false}:{languages:Language[];language:Language;label:string;onChange:(language:Language)=>void;names?:boolean}){
 if(languages.length<2)return null;
 return <select className="language-picker" aria-label={label} value={language} onChange={e=>onChange(e.target.value as Language)}>
  {languages.map(l=><option key={l} value={l}>{names?NAMES[l]||l.toUpperCase():l.toUpperCase()}</option>)}
 </select>
}
