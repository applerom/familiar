import type {Row} from './model';

// Only direct, attributed assertions can confirm a person. A possible link,
// an index entry, a photograph, or an inference is not a documented event.
const visible=(s:Row|undefined)=>!!s&&!!(s.title||s.asset);
const documentary=(s:Row|undefined)=>visible(s)&&['archive-record','home-paper','record','document','document-scan'].includes(s.kind);
const artifact=(s:Row|undefined)=>visible(s)&&(['archive-record','home-paper','record','document','document-scan','image'].includes(s.kind));
const solid=(r:Row)=>!r.derived&&!['hypothesis','conflict','rejected','disproved','possible','probable'].includes(r.status)&&!['possible','probable'].includes(r.confidence);
const refs=(r:Row)=>[...(r.sources||[]),...(r.provenance||[])];
export function growth(data:Row,id:string,connector=false){
 const p=data.people[id],sources=data.sources||{}, all=new Set<string>();
 for(const row of [...(p.names||[]),...(p.events||[]),...(p.facts||[]),...(connector?[]:(p.notes||[]))]) refs(row).forEach(s=>all.add(s));
 for(const [sid,s] of Object.entries<Row>(sources)) if((s.subjects||[]).includes(id)) all.add(sid);
 for(const m of p.media||[]) if(m.sourceSid||m.sid) all.add(m.sourceSid||m.sid);
 const memory=[...all].some(s=>sources[s]?.kind==='memory')||!!data.cardStatuses?.[id]?.in_original_tree;
 // The tree the family kept (imported by the narrator) is firm memory; research additions are not.
 const treeMemory=!connector&&!!data.cardStatuses?.[id]?.family_memory;
 const firmMemory=treeMemory||!connector&&(p.facts||[]).some((f:Row)=>f.testimony==='firm'&&solid(f));
 const docSources=[...all].filter(s=>artifact(sources[s]));
 const key=(r:Row)=>['birth','marriage','death','BIRT','MARR','DEAT'].includes(r.type||r.tag||r.eventType);
 const claims=[...(p.events||[]),...(p.facts||[])].filter(r=>solid(r)&&key(r));
 const marriages=(data.families||[]).filter((f:Row)=>f.husband===id||f.wife===id).flatMap((f:Row)=>(f.events||[]).filter((e:Row)=>solid(f)&&solid(e)&&key(e)));
 const links=(data.edges||[]).filter((e:Row)=>(e.child===id||e.parent===id)&&solid(e));
 // A paper confirms the people it names: a record that lists its subjects without this person is not theirs.
 const grounds=[...claims,...marriages,...links].flatMap(refs).filter(s=>documentary(sources[s])&&(!sources[s].subjects?.length||sources[s].subjects.includes(id)));
 return {hasMedia:(p.media||[]).some((m:Row)=>!!m.asset&&!m.photo), memory, firmMemory, treeMemory, found:!memory&&docSources.length>0, documents:docSources,
  confirmed:[...new Set(grounds)], manual:p.confirmation?.level&&p.confirmation.level!=='mention'};
}
export const growthWords:Record<string,Row>={
 ru:{tree:'Из семейного дерева',memory:'Со слов семьи',found:'Нашли в документах',docs:'Есть документы',confirmed:'По документу',people:'в дереве',peopleUnit:'человек',memoryCount:'из памяти семьи',foundCount:'нашли в бумагах',confirmedCount:'подтверждено документами'},
 en:{tree:'From the family tree',memory:'From the family’s testimony',found:'Found in documents',docs:'Documents available',confirmed:'From the document',people:'in the tree',peopleUnit:'people',memoryCount:'from family memory',foundCount:'found in papers',confirmedCount:'confirmed by documents'},
 pl:{tree:'Z drzewa rodziny',memory:'Według relacji rodziny',found:'Znaleziono w dokumentach',docs:'Są dokumenty',confirmed:'Według dokumentu',people:'w drzewie',peopleUnit:'osób',memoryCount:'z pamięci rodziny',foundCount:'znaleziono w dokumentach',confirmedCount:'potwierdzono dokumentami'},
 sv:{tree:'Från familjens träd',memory:'Enligt familjens berättelse',found:'Hittad i dokument',docs:'Dokument finns',confirmed:'Enligt dokumentet',people:'i trädet',peopleUnit:'personer',memoryCount:'ur familjens minne',foundCount:'hittade i papper',confirmedCount:'bekräftade av dokument'}
};
