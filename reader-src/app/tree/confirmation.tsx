import {inLanguage} from '../reader-profile';
export type Confirmation={level:'document'|'family'|'mention';basis:Record<string,string>;sources?:string[]};
const titles:Record<string,Record<string,string>>={
 ru:{document:'Подтверждено документом',family:'Подтверждено семейными сведениями',mention:'Есть упоминание'},
 pl:{document:'Potwierdzone dokumentem',family:'Potwierdzone wiedzą rodzinną',mention:'Wzmianka w źródle'},
 en:{document:'Confirmed by a record',family:'Confirmed by family knowledge',mention:'Mentioned in a source'},
 sv:{document:'Bekräftat av ett dokument',family:'Bekräftat av familjens kunskap',mention:'Nämns i en källa'}
};
export function confirmationText(value:Confirmation,language:string){return [titles[language]?.[value.level]||titles.en[value.level]||titles.ru[value.level],inLanguage(value.basis,language)].filter(Boolean).join(' · ')}
export default function ConfirmationMark({value,language}:{value?:Confirmation;language:string}){
 if(!value||value.level==='mention')return null;
 const label=confirmationText(value,language);
 return <span className={'confirmation-mark '+value.level} role="img" title={label} aria-label={label}>✓</span>
}
