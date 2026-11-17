import {createRoot} from 'react-dom/client';
import PageTop,{familyHeading} from '../app/page-top';
import {loadReader,profile,siteURL} from '../app/reader-profile';
import {buildModel} from '../app/tree/model';
import {translations} from '../app/i18n';

// Supplemental pages share the component, but have no local tree search or translation.
loadReader().then(({data})=>{
 const p=profile(),language=p.family.source_language,t=translations[language];
 const title=typeof p.family.title==='string'?p.family.title:p.family.title[language]||t.title;
 const model=buildModel(data,t);
 createRoot(document.getElementById('page-top')!).render(<PageTop home={siteURL('#view=tree')} title={familyHeading(title,model.homes.map(h=>model.info[h]?.surnameKey))} notice={p.family.fictional?t.fictionalDemo:undefined}/>);
});
