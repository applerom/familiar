import type {Language} from './i18n';

export default function LanguagePicker({languages,language,label,onChange}:{languages:Language[];language:Language;label:string;onChange:(language:Language)=>void}){
 return <select className="language-picker" aria-label={label} value={language} onChange={e=>onChange(e.target.value as Language)}>
  {languages.map(l=><option key={l} value={l}>{l.toUpperCase()}</option>)}
 </select>
}
