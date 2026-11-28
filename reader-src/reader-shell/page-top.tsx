import {createRoot} from 'react-dom/client';
import PageTop,{familyHeading,namesItself} from '../app/page-top';
import {loadProfile,loadReader,profile,siteURL} from '../app/reader-profile';
import {localizeGraph} from '../app/localize';
import {buildModel} from '../app/tree/model';
import {translations} from '../app/i18n';

// Supplemental pages share the component; the page's own language names the family and the people's forms.
(async()=>{
 await loadProfile();
 const p=profile(),own=document.documentElement.lang as typeof p.family.source_language,language=p.family.languages.includes(own)?own:p.family.source_language,t=translations[language];
 const title=typeof p.family.title==='string'?p.family.title:p.family.title[language]||p.family.title[p.family.source_language]||t.title;
 let heading=title;
 if(!namesItself(title)){const data=localizeGraph((await loadReader()).data,language),model=buildModel(data,t);heading=familyHeading(title,model.homes.map(h=>model.info[h]?.surnameKey))}
 createRoot(document.getElementById('page-top')!).render(<PageTop home={siteURL('#view=tree')} title={heading} more={t.moreMenu} notice={p.family.fictional?t.fictionalDemo:undefined}/>);
})();
