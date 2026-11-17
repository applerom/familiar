import {termPhrase,kinshipLexicon,kinshipTerm} from './kinship';
import {growth} from './growth';
import type {Confirmation} from './confirmation';
export type Row=Record<string,any>;
export type Info={connector?:boolean;connectorNote?:string;connectorBasis?:Row;growth:ReturnType<typeof growth>;confirmation?:Confirmation;id:string;name:string;short:string;treeName:string;clanSurname?:string;alt:string;note:string;fullName:string;providedName?:string;maidenSurname?:string;maidenShown:string;showMaiden:boolean;unknownSurname:boolean;isWoman:boolean;placeholder:boolean;unnamed?:boolean;story:boolean;surnameKey:string;birth?:number;death?:number;approx:boolean;guess?:BirthGuess;sex:'m'|'f'|'';place:string;life:string;placeRole:string;birthText:string;deathText:string;birthKind:string;deathKind:string;connectionNote:Row;connectionShort:Row;dateBasis:Row;dateReference:Row};
/** An orientation year the engine gives a person nobody recorded a birth for (setting tree.first_child_age); never a fact. */
export type BirthGuess={year:number;exact:number;relation:'child'|'parent'|'spouse'|'sibling';anchors:{id:string;year:number;guessed:boolean;age:number;offset:number}[]};
export type Kin={home:string;homeId:string;kind:'ancestor'|'spouse'|'child';n:number;g:'m'|'f'|'';sure:boolean};
export type Relation={kind:'self'|'spouse'|'ancestor'|'descendant'|'collateral';n1:number;n2:number;g:'m'|'f'|'';branchG?:'m'|'f'|'';collateralG?:'m'|'f'|'';cousinG?:'m'|'f'|'';sure:boolean;path?:string[];viewerG?:'m'|'f'|'';special?:string;spouseOf?:Relation;spouseG?:'m'|'f'|'';viaSpouse?:'m'|'f'|''};
export type Slot={id:string;status:string;role:string;likelihood?:string;weight?:number;sources?:string[]};
/** Visitor confidence is independent of the research workflow status. */
export function connectionLevel(edge:{status?:string;likelihood?:string;weight?:number}){
 if(typeof edge.weight==='number')return edge.weight<.3?3:edge.weight<.5?2:1;
 return edge.status==='verified'||edge.status==='export'?1:edge.status==='hypothesis'&&edge.likelihood==='probable'?2:3;
}
export const connectionStatus=(edge:{status?:string;likelihood?:string;weight?:number})=>connectionLevel(edge)===3?'hypothesis':connectionLevel(edge)===2?'probable':typeof edge.weight==='number'?'export':edge.status||'export';
const REJECTED=['rejected','disproved'];
const RANK:Record<string,number>={verified:0,export:1,conflict:2,hypothesis:3};
const rank=(s:string)=>RANK[s]??2;
/**
 * The four ancestor lines, one hue each: blue, rose, indigo, teal. Picked so the four stay apart for protan, deutan and
 * tritan vision (simulated, min ΔE ≥ 10) and away from the colours that already mean something here: sage = no line,
 * green = checkmark, amber = "you are here", red = "сведения расходятся". Light theme only (the app has no dark theme).
 */
export const BRANCH_COLORS=['#3d6db5','#b0457e','#4a3f94','#2a8794'];
/** The same hues mixed 60/40 with the paper: blood kin of one line who are not direct ancestors (brothers, sisters, their descendants). */
export const BRANCH_TINTS=['#87a3ca','#cc8ba9','#8f87b6','#7cb2b6'];
export const NEUTRAL='#9fb09c';
export type Tone={line:number;kin:boolean;color:string};
/** An imported tag, or a research event of that kind that is not a version. */
const isEvent=(e:Row,tag:string,kind:string)=>e.tag===tag||(e.type===kind&&![...REJECTED,'hypothesis'].includes(e.status));
function year(date:string){const m=/\b(\d{4})\b/.exec(date||'');return m?+m[1]:undefined}
function splitName(name:string){const i=name.indexOf(' · ');return i<0?{main:name,note:''}:{main:name.slice(0,i),note:name.slice(i+3)}}
const COUNTRIES=new Set(['беларусь','белоруссия','belarus','białoruś','польша','polska','poland','россия','russia','российская империя','russian empire','литва','lithuania','lietuva','ссср','ussr','usa','сша','united states','united states of america','germany','германия','deutschland']);
export function shortPlace(place:string){const parts=(place||'').split(/[,;]/).map(p=>p.trim()).filter(p=>p&&!COUNTRIES.has(p.toLocaleLowerCase().replace(/\.$/,''))).map(p=>p.replace(/\s+(Польша|Polska|Poland|Беларусь|Belarus)$/i,''));return (parts.find(p=>!/(область|обл\.|район|р-н|губерния|powiat|województwo)/i.test(p))||parts[0]||'').replace(/\s*\(.*$/,'').trim()}
const APPROX_DATE=/^(ABT\b|EST\b|CAL\b|≈|~|about\b|circa\b|ca\.|около|примерно|прибл\.?|ok\.|około|cirka)/i;
function compactDate(date:string){const y=year(date);if(y===undefined)return '';const q=(date||'').trim();return APPROX_DATE.test(q)?'≈'+y:/^(BEF|до)/i.test(q)?'BEF '+y:/^(AFT|после)/i.test(q)?'AFT '+y:String(y)}
export const translated=(value:any,lang:string)=>typeof value==='string'?value:value?.[lang]||value?.en||value?.ru||'';
/** "1974–…" for the dead or the long-ago born; "род. 1974" for someone born in living memory with no death recorded. */
export function lifeLabel(p:Info,labels:Row,lang:string){const b=p.birthText?humanText(p.birthText,lang):'',d=p.deathText?humanText(p.deathText,lang):'';if(b&&!d&&(p.birth??p.guess?.year??0)>=1920&&labels.born)return `${labels.born} ${b}`;return b||d?`${b||'…'}–${d||'…'}`:translated(p.dateReference,lang)}
type GuessWords={rel:Record<BirthGuess['relation'],[string,string,string]>;age:(g:string,n:number)=>string;spouse:(g:string,n:number)=>string;sibling:string;guessed:string;later:string};
const ruYears=(n:number)=>n%10===1&&n%100!==11?'год':n%10>=2&&n%10<=4&&(n%100<10||n%100>=20)?'года':'лет';
const plYears=(n:number)=>n===1?'rok':n%10>=2&&n%10<=4&&(n%100<10||n%100>=20)?'lata':'lat';
const GUESS:Record<string,GuessWords>={
 ru:{rel:{child:['сын','дочь','ребёнок'],parent:['отец','мать','родитель'],spouse:['муж','жена','супруг'],sibling:['брат','сестра','брат или сестра']},
  age:(g,n)=>`${g==='m'?'отцу':g==='f'?'матери':'родителю'} при первом ребёнке тогда обычно было около ${n} ${n%10===1&&n%100!==11?'года':'лет'}`,
  spouse:(g,n)=>n===0?'супруги тогда обычно бывали ровесниками':`${g==='f'?'жёны':g==='m'?'мужья':'супруги'} тогда обычно бывали ${n>0?'моложе':'старше'} ${g==='f'?'мужей':g==='m'?'жён':'друг друга'} на ${Math.abs(n)} ${ruYears(Math.abs(n))}`,
  sibling:'братья и сёстры обычно близки по возрасту',guessed:'тоже оценка',later:'Найдётся запись — год заменится.'},
 pl:{rel:{child:['syn','córka','dziecko'],parent:['ojciec','matka','rodzic'],spouse:['mąż','żona','małżonek'],sibling:['brat','siostra','rodzeństwo']},
  age:(g,n)=>`${g==='m'?'ojciec miał':g==='f'?'matka miała':'rodzic miał'} wtedy przy pierwszym dziecku zwykle około ${n} lat`,
  spouse:(g,n)=>n===0?'małżonkowie byli wtedy zwykle rówieśnikami':g==='f'?`żony były wtedy zwykle o ${Math.abs(n)} ${plYears(Math.abs(n))} ${n>0?'młodsze':'starsze'} od mężów`:`${g==='m'?'mężowie':'małżonkowie'} byli wtedy zwykle o ${Math.abs(n)} ${plYears(Math.abs(n))} ${n>0?'młodsi':'starsi'}${g==='m'?' od żon':''}`,
  sibling:'rodzeństwo jest zwykle w zbliżonym wieku',guessed:'też szacunek',later:'Gdy znajdzie się zapis, zastąpi ten rok.'},
 en:{rel:{child:['son','daughter','child'],parent:['father','mother','parent'],spouse:['husband','wife','spouse'],sibling:['brother','sister','sibling']},
  age:(g,n)=>`a ${g==='m'?'father':g==='f'?'mother':'parent'} was then usually about ${n} at the first child`,
  spouse:(g,n)=>n===0?'spouses were then usually of an age':`${g==='f'?'wives':g==='m'?'husbands':'spouses'} were then usually about ${Math.abs(n)} years ${n>0?'younger':'older'}`,
  sibling:'brothers and sisters are usually close in age',guessed:'also a guess',later:'A record, once found, replaces this year.'},
 sv:{rel:{child:['son','dotter','barn'],parent:['far','mor','förälder'],spouse:['make','maka','make eller maka'],sibling:['bror','syster','syskon']},
  age:(g,n)=>`en ${g==='m'?'far':g==='f'?'mor':'förälder'} var då oftast omkring ${n} år vid första barnet`,
  spouse:(g,n)=>n===0?'makar var då oftast jämngamla':`${g==='f'?'hustrur':g==='m'?'män':'makar'} var då oftast omkring ${Math.abs(n)} år ${n>0?'yngre':'äldre'}`,
  sibling:'syskon är oftast nära i ålder',guessed:'också en uppskattning',later:'När en uppteckning hittas ersätter den året.'}};
/** Why a guessed birth year is what it is: the dated relatives it rests on and the rule of the time, in plain words. */
export function guessBasis(p:Info,m:{info:Record<string,Info>},lang:string){
 const g=p.guess;if(!g)return '';const w=GUESS[lang]||GUESS.en;const at=(s:string)=>s==='m'?0:s==='f'?1:2;
 const who=g.anchors.map(a=>{const i=m.info[a.id];return `${w.rel[g.relation][at(i?.sex||'')]} ${i?.short||'…'} — ${a.guessed?'≈':''}${a.year}${a.guessed?` (${w.guessed})`:''}`}).join(', ');
 const rule=g.relation==='child'?w.age(p.sex,g.anchors[0].age):g.relation==='spouse'?w.spouse(p.sex,g.anchors[0].age):g.relation==='sibling'?w.sibling:g.anchors.map(a=>w.age(m.info[a.id]?.sex||'',a.age)).join('; ');
 return `${who.slice(0,1).toLocaleUpperCase(lang)+who.slice(1)}; ${rule}. ${w.later}`;
}
export function placeLabel(p:Info,labels:Row){return p.place?(p.placeRole&&p.placeRole!=='birth'?(labels.placeRoles?.[p.placeRole]||labels.placeRoles?.record)+' ':'')+p.place:''}
export function lifeFactText(text:string,lang:string){const parts=(text||'').split(' · ');return humanText(parts.map((p,i)=>i>0?p.split(',').map(x=>x.trim()).filter(x=>!COUNTRIES.has(x.toLocaleLowerCase().replace(/\.$/,''))).join(', '):p).filter(Boolean).join(' · '),lang)}
const MAYBE:Record<string,string>={ru:kinshipLexicon('ru')!.maybe,pl:kinshipLexicon('pl')!.maybe,en:kinshipLexicon('en')!.maybe,sv:'möjligen '};
/** The family surname a person is grouped under: a woman's own maiden surname when known, otherwise the surname shown. */
const cleanSurname=(s:string)=>String(s||'').replace(/\s*[(\[].*$/,'').replace(/\?/g,'').trim();
const SURNAME=/^\p{Lu}[\p{L}'’-]+$/u;// a real surname, not a note such as "записано" or "[предварительное]"
function surnameKey(np:Row,short:string){if(np.maidenSurname){const s=cleanSurname(np.maidenSurname);return SURNAME.test(s)?s:''}if(np.surnameUnknown||(np.isWoman&&np.isWife&&!np.maidenSurname))return '';const parts=short.split(' ').filter(x=>/\p{L}/u.test(x));const s=parts.length>1?parts[parts.length-1]:'';return SURNAME.test(s)?s:''}
/** A relation word joined with a home person's name in the right order for the language. */
/** An ancestor line is named by its surname, not by the reader. */
/** «Род …» in Russian takes the family in the genitive plural: Корнеев → Корнеевых (the invented demo family).
 *  Latin-script surnames retain their literal spelling. */
export function clanGenitive(s:string){if(!/^[А-ЯЁ][а-яё-]+$/.test(s))return s;
 if(/(ский|цкий|ской|цкой|ская|цкая)$/.test(s))return s.replace(/(ий|ой|ая)$/,'их');
 if(/(ов|ев|ёв|ин|ын)$/.test(s))return s+'ых';if(/(ова|ева|ёва|ина|ына)$/.test(s))return s.slice(0,-1)+'ых';
 if(/(ич|ш|ж|щ|ч)$/.test(s))return s+'ей';return s}
export function lineTitle(l:{id:string},model:Model,labels:Row){const i=model.info[l.id];const s=i?.surnameKey||i?.short?.split(' ').pop()||'';const t=String(labels.lineOf||'{s}');return t.replace('{s}',t.startsWith('Род ')?clanGenitive(s):s)}
export function withHome(word:string,home:string,labels:Row){const gen=labels.homeGenitive?.[home]||home;return labels.genitiveFirst?`${gen} ${word}`:`${word} ${gen}`}
/** Genitive of a relation word: "прадеда", "бабушки", "двоюродного брата"; Polish from a table, English with 's. */
export function genitive(word:string,lang:string){return genitive0(word,lang)}
function genitive0(word:string,lang:string){
 if(lang==='en')return word+"'s";
 if(lang==='sv')return /[sxz]$/.test(word)?word:word+'s';
 return word.split(' ').map(w=>{
  if(lang==='pl'){for(const [k,v] of Object.entries(kinshipLexicon('pl')!.genitive))if(w.endsWith(k))return w.slice(0,-k.length)+v;return w}
  for(const [k,v] of Object.entries(kinshipLexicon('ru')!.genitive))if(w.endsWith(k))return w.slice(0,-k.length)+v;
  if(/ый$/.test(w))return w.slice(0,-2)+'ого';if(/ий$/.test(w))return w.slice(0,-2)+'его';if(/ая$/.test(w))return w.slice(0,-2)+'ой';
  if(/[кгхжшчщ]а$/.test(w))return w.slice(0,-1)+'и';if(/а$/.test(w))return w.slice(0,-1)+'ы';if(/я$/.test(w))return w.slice(0,-1)+'и';if(/ь$/.test(w))return w.slice(0,-1)+'я';return w+'а'}).join(' ');
}
/** "ваш прадед" / "жена вашего дедушки" / "your wife's mother": a relation to the viewer as words. */
export function relationPhrase(r:Relation,labels:Row,lang0:string){
 const precise=termPhrase(r,lang0);if(precise)return precise;
 return describeRelation(r,labels,lang0);
}
/** Descriptive fallback for a language or relationship missing from the pack. */
export function describeRelation(r:Relation,labels:Row,lang0:string){
 const lexicon=kinshipLexicon(lang0);
 if(lexicon){
  const source=r.spouseOf||r,key=source.kind==='self'?'self':source.kind==='spouse'?'spouse':source.kind==='ancestor'?'ancestor':source.kind==='descendant'?'descendant':'collateral';
  let relative=substitute(lexicon.fallback[key],{n:source.kind==='ancestor'?source.n1:source.n2,n1:source.n1,n2:source.n2});
  if(lang0==='en')relative=relative.replace(/\b1 generations\b/g,'1 generation');
  const text=r.special?(lexicon.fallback[r.special]||lexicon.fallback[r.special.startsWith('step')?'step':'spiritual']):r.spouseOf?substitute(lexicon.fallback.spouseOf,{relative}):r.viaSpouse?substitute(lexicon.fallback.viaSpouse,{relative}):relative;
  return (r.sure?'':lexicon.maybe)+text;
 }
 const lang=lang0==='sv'?'en':lang0,sv=lang0==='sv';const relWord=(n:number,g:'m'|'f'|'',_l:string)=>relWord0(n,g,lang0);const genitive=(w:string,_l:string)=>genitive0(w,lang0);const cousinWord=(n:number,g:'m'|'f'|'',_l:string)=>cousinWord0(n,g,lang0);
 const R=labels.rel;const gi=(g:string)=>g==='f'?1:0;
 const base=(x:Relation):string=>{
  if(x.kind==='spouse')return R.spouse[gi(x.g)];
  if(x.kind==='ancestor')return relWord(x.n1,x.g,lang);
  if(x.kind==='descendant')return x.n2===1?R.child[gi(x.g)]:x.n2===2?R.grandchild[gi(x.g)]:R.great.repeat(x.n2-2)+R.grandchild[gi(x.g)];
  const key=({'1,1':'sibling','2,1':'uncle','1,2':'nephew','2,2':'cousin','3,1':'greatUncle','1,3':'grandNephew','3,2':'cousinUncle','2,3':'cousinNephew','3,3':'secondCousin'} as Record<string,string>)[`${x.n1},${x.n2}`]||'distant';
  return R[key][gi(x.g)]};
 const explain=(key:string,n=0):string=>{const E=labels.relExplain||{};if(key==='cousinN')return n?String(E.cousinN||'').replace('{a}',relWord(n,'m',lang)):'';return E[key]||''};
 const withExplain=(w:string,e:string)=>e?`${w} (${e})`:w;
 let text:string;
 if(r.kind==='self')text=R.self;
 else if(r.spouseOf){const w=base(r.spouseOf),g=r.spouseOf.g;text=lang==='en'?`${R.your[0]} ${genitive(w,lang)} ${R.spouse[gi(r.g)]}`:`${R.spouse[gi(r.g)]} ${R.yourGen[gi(g)]} ${genitive(w,lang)}`}
 else if(r.viaSpouse){const w=base(r);text=lang==='en'?`${R.your[0]} ${genitive(R.spouse[gi(r.viaSpouse)],lang)} ${w}`:`${w} ${R.yourGen[gi(r.viaSpouse)]} ${R.spouseGen[gi(r.viaSpouse)]}`}
 else if(r.kind==='collateral'&&r.n1===r.n2&&r.n1>=4){const w=cousinWord(r.n1,r.g,lang);text=`${R.your[gi(r.g)]} ${withExplain(w,explain('cousinN',r.n1))}`}
 else if(r.kind==='collateral'&&r.n1!==r.n2&&(r.n1>=3||r.n2>=3)&&!sv&&(lang==='ru'||lang==='en')){text=`${R.your[gi(r.g)]} ${collateralWord(r.n1,r.n2,r.g,lang,r.cousinG)}`}
 else if(r.kind==='collateral'&&(r.n1>3||r.n2>3)){
  // Describe the known generation instead of losing it as "distant relative".
  const owner=r.n1===1?R.sibling[gi(r.collateralG||'m')]:relWord(r.n1-1,r.branchG||'m',lang);
  const sibling=R.sibling[gi(r.n2===1?r.g:r.collateralG||'m')];
  const of=(word:string,whose:string,g:string)=>lang==='en'?`${R.your[0]} ${genitive(whose,lang)} ${word}`:`${word} ${R.yourGen[gi(g)]} ${genitive(whose,lang)}`;
  if(r.n1===1)text=of(base({...r,kind:'descendant',n2:r.n2-1}),owner,r.collateralG||'m');
  else if(r.n2===1)text=of(sibling,owner,r.branchG||'m');
  else{
   const descendant=base({...r,kind:'descendant',n2:r.n2-1});
   const ancestry=of(sibling,owner,r.branchG||'m');
   text=lang==='en'?`${descendant} of ${ancestry}`:`${descendant} ${of(genitive(sibling,lang),owner,r.branchG||'m')}`;
  }
 }
 else{const w=base(r);const key=r.kind==='collateral'?({'3,1':'greatUncle','1,3':'grandNephew','3,2':'cousinUncle','2,3':'cousinNephew','3,3':'secondCousin'} as Record<string,string>)[`${r.n1},${r.n2}`]||'':'';text=`${R.your[gi(r.g)]} ${withExplain(w,key==='secondCousin'?explain('cousinN',3):explain(key))}`}
 return (r.sure?'':(MAYBE[lang0]||MAYBE.ru))+text;
}
/** One kinship entry as words. */
export function kinPhrase(k:Kin,labels:Row,lang:string){
 const gen=labels.homeGenitive?.[k.home]||k.home;
 const word=k.kind==='ancestor'?relWord(k.n,k.g,lang):k.kind==='spouse'?(k.g==='f'?labels.wifeOf:labels.husbandOf):(k.g==='f'?labels.daughterOf:k.g==='m'?labels.sonOf:labels.childOf);
 const text=labels.genitiveFirst?`${gen} ${word}`:`${word} ${gen}`;
 return (k.sure?'':(MAYBE[lang]||MAYBE.ru))+text;
}
/** Pack table first, then a neutral generation description. No guessed gender. */
const substitute=(text:string,values:Record<string,string|number>)=>text.replace(/\{(\w+)\}/g,(_,key)=>String(values[key]??''));
function collateralWord(n1:number,n2:number,g:'m'|'f'|'',lang:string,_cousinG:'m'|'f'|''='m'){
 const r:Relation={kind:'collateral',n1,n2,g,sure:true};const t=kinshipTerm(r,lang);
 const pack=kinshipLexicon(lang);return t?`${t.word} (${t.explanation})`:substitute(pack?.fallback.collateral||'',{n1,n2});
}
const cousinWord0=cousinWord;
function cousinWord(n:number,g:'m'|'f'|'',lang:string){
 if(lang==='sv')return ['','','kusin','tremänning','fyrmänning','femmänning','sexmänning','sjumänning'][n]||`${n-1}:e kusin`;
 return kinshipTerm({kind:'collateral',n1:n,n2:n,g,sure:true},lang)?.word||substitute(kinshipLexicon(lang)?.fallback.cousin||'',{n});
}
const relWord0=relWord;
function relWord(n:number,g:'m'|'f'|'',lang:string){
 if(lang==='sv'){const pick=(m:string,f:string,x:string)=>g==='m'?m:g==='f'?f:x;
  if(n===1)return pick('far','mor','förälder');if(n===2)return pick('farfar eller morfar','farmor eller mormor','far- eller morförälder');if(n===3)return pick('farfars eller morfars far','farmors eller mormors mor','förälder till en far- eller morförälder');return `förfader, ${n} generationer bakåt`}
 return kinshipTerm({kind:'ancestor',n1:n,n2:0,g,sure:true},lang)?.word||substitute(kinshipLexicon(lang)?.fallback.ancestor||'',{n});
}
const MONTHS=['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'];
const WORDS:Record<string,{abt:string;bef:string;aft:string;from:string}>={ru:{abt:'≈',bef:'до',aft:'после',from:'с'},pl:{abt:'≈',bef:'przed',aft:'po',from:'od'},en:{abt:'≈',bef:'before',aft:'after',from:'from'},sv:{abt:'≈',bef:'före',aft:'efter',from:'från'}};
/** Turns raw GEDCOM-style text ("20 JUN 1974", "ABT 1951", "@F500014@") into plain words. */
export function humanText(text:string,lang:string){
 const w=WORDS[lang]||WORDS.ru;const fmt=(o:Intl.DateTimeFormatOptions,d:Date)=>new Intl.DateTimeFormat(lang,{...o,timeZone:'UTC'}).format(d);
 return (text||'')
  .replace(/\s*[·,]?\s*@[A-Z]\d+@/g,'')
  .replace(/^Дата не указана\s*·\s*/,'')
  .replace(/\bFROM (\d{4}) TO (\d{4})\b/g,'$1–$2')
  .replace(/\b(?:about|circa|EST|CAL)\s+(?=\d)/gi,w.abt)
  .replace(/\b(ABT|BEF|AFT) /g,(_,k)=>(k==='ABT'?w.abt:k==='BEF'?w.bef+' ':w.aft+' ').replace('≈','≈'))
  .replace(/\b(\d{1,2}) ([A-Z]{3}) (\d{4})\b/g,(s,d,mo,y)=>MONTHS.includes(mo)?fmt({day:'numeric',month:'long',year:'numeric'},new Date(Date.UTC(+y,MONTHS.indexOf(mo),+d))):s)
  .replace(/\b([A-Z]{3}) (\d{4})\b/g,(s,mo,y)=>MONTHS.includes(mo)?fmt({month:'long',year:'numeric'},new Date(Date.UTC(+y,MONTHS.indexOf(mo),1))):s)
  .replace(/≈ /g,'≈').replace(/\s+·\s+·\s+/g,' · ').trim();
}
export type Model=ReturnType<typeof buildModel>;
export function buildModel(data:Row,labels:Row={}){
 const info:Record<string,Info>={};
 for(const [id,p] of Object.entries<Row>(data.people)){
  const {main,note}=splitName(p.name||'');const np={...p.namePresentation};
  const ownerLabel=typeof p.placeholder==='string'&&p.placeholder.trim()?p.placeholder:'';
  const connector=!!ownerLabel&&!(p.names||[]).some((n:Row)=>n.given?.trim());
  // Explicit display decisions win; otherwise use sex or the recorded family role.
  np.isWoman??=p.sex==='f'||p.sex==='F'||(data.families||[]).some((f:Row)=>f.wife===id);
  const display=ownerLabel||np.display||main||labels.unknownName||'Name not recorded';const full=ownerLabel||np.full||display;const ev:Row[]=p.events||[];const b=ev.find(e=>isEvent(e,'BIRT','birth')&&(e.date||e.place));const d=ev.find(e=>isEvent(e,'DEAT','death')&&e.date);
  const cp=p.cardPresentation||{};const bd=cp.birth??b?.date,dd=cp.death??d?.date;
  const birth=year(bd),death=year(dd),approx=APPROX_DATE.test((bd||'').trim())||/^(BEF|AFT|до|после)/i.test((bd||'').trim());
  const guess:BirthGuess|undefined=birth===undefined&&p.birthGuess?.year?p.birthGuess:undefined;
  const birthText=compactDate(bd)||(guess?'≈'+guess.year:''),deathText=compactDate(dd);const life=birthText||deathText?`${birthText||'…'}–${deathText||'…'}`:'';
  const alt=ownerLabel?'':[...main.matchAll(/\(([^)]*)\)/g)].map(m=>m[1].trim()).filter(Boolean).join(', ');
  const short=ownerLabel||display.replace(/\s*\([^)]*\)/g,'').replace(/\s+/g,' ').trim()||display;
  // a GEDCOM placeholder ("- удалить") is kept in the data but never shown as a person
  const placeholder=!ownerLabel&&/^[\s\-–—]*(удалить|delete|usunąć)\b/i.test(main);
  // the maiden surname is worth a line only when it differs from the surname already shown
  const maidenClean=cleanSurname(np.maidenSurname);const maidenShown=!ownerLabel&&maidenClean&&!short.toLocaleLowerCase().endsWith(maidenClean.toLocaleLowerCase())?maidenClean:'';
  const ownerSurname=cleanSurname(p.names?.find((n:Row)=>n.surname)?.surname||ownerLabel.split('(')[0]);
  const story=typeof p.story==='string'?p.story.trim():!!(p.story?.ru||p.story?.pl||p.story?.en||p.story?.sv);
  const g=growth(data,id,connector);if(connector&&!g.documents.length&&!g.hasMedia){g.found=false;g.confirmed=[]}const basis=g.confirmed.map(s=>data.sources[s]?.title).filter(Boolean).join(' · ');
  info[id]={connector,connectorNote:connector?ownerLabel:undefined,growth:g,confirmation:g.confirmed.length?{level:'document',basis:{ru:basis,en:basis,pl:basis,sv:basis},sources:g.confirmed}:p.confirmation,id,name:full,treeName:ownerLabel||p.treeName||short,clanSurname:p.surnameDisplay?.form,providedName:ownerLabel||undefined,story:!!story,fullName:full,maidenSurname:np.maidenSurname||undefined,maidenShown,showMaiden:!ownerLabel&&!!(np.isWoman&&(np.isWife||np.maidenSurname)),unknownSurname:!!np.surnameUnknown,isWoman:!!np.isWoman,placeholder,surnameKey:p.surnameDisplay?.form|| (ownerLabel?(SURNAME.test(ownerSurname)?ownerSurname:''):main?surnameKey(np,short):''),short,alt,note:ownerLabel?'':note,birth,death,approx:approx||!!guess,guess,sex:/^m$/i.test(p.sex||'')?'m':/^f$/i.test(p.sex||'')||np.isWoman?'f':(data.families||[]).some((f:Row)=>f.husband===id)?'m':'',place:shortPlace(cp.place??b?.place),life,placeRole:cp.placeRole||'birth',birthText,deathText,birthKind:cp.birthKind||'source',deathKind:cp.deathKind||'source',connectionNote:cp.connectionNote||{},connectionShort:cp.connectionShort||{},dateBasis:cp.dateBasis||{},dateReference:cp.dateReference||{}}
 }
 // An unnamed connector is shown by the placeholder the family data carries, literally; the engine never builds
 // a replacement (no child's surname, no transliteration, no feminine form).
 for(const [id,p] of Object.entries<Row>(data.people)){
  if(!info[id].connector)continue;
  const links=(data.edges||[]).filter((e:Row)=>e.parent===id&&info[e.child]&&!REJECTED.includes(e.status));
  const label=String(p.placeholder).trim();
  Object.assign(info[id],{name:label,short:label,treeName:label,fullName:label,providedName:undefined,connectorNote:undefined,connectorBasis:links.find((e:Row)=>e.basis)?.basis||{}});
 }
 // A link the family already knew (both people in the original family tree) is shown as firm.
 // Probable documentary synthesis is also firm; suitable/unspecified/conflicting links remain tentative.
 const inOriginal=(id:string)=>!!data.cardStatuses?.[id]?.in_original_tree;
 const firmStatus=(e:Row)=>info[e.parent]?.connector||info[e.child]?.connector?'hypothesis':e.status==='hypothesis'&&e.sources?.includes('snapshot')&&inOriginal(e.child)&&inOriginal(e.parent)&&!data.people[e.parent]?.relationshipUncertain?'export':e.status;
 const up=new Map<string,Row[]>(),down=new Map<string,string[]>();
 const push=<T,>(m:Map<string,T[]>,k:string,v:T)=>{const a=m.get(k);a?a.push(v):m.set(k,[v])};
 (data.edges||[]).filter((e:Row)=>!REJECTED.includes(e.status)&&info[e.child]&&info[e.parent]&&e.child!==e.parent&&!info[e.child].placeholder&&!info[e.parent].placeholder).sort((a:Row,b:Row)=>connectionLevel({...a,status:firmStatus(a)})-connectionLevel({...b,status:firmStatus(b)})||rank(a.status)-rank(b.status)).forEach((e:Row)=>{push(up,e.child,e);const kids=down.get(e.parent);if(!kids?.includes(e.child))push(down,e.parent,e.child)});
 const byYear=(a:string,b:string)=>(info[a].birth??9999)-(info[b].birth??9999)||info[a].name.localeCompare(info[b].name,'ru');
 const roleOf=(pid:string)=>{const s=String(data.people[pid]?.sex||'').toLowerCase();return s==='m'||(s!=='f'&&!info[pid]?.isWoman&&(data.families||[]).some((f:Row)=>f.husband===pid))?'отец':s==='f'||info[pid]?.isWoman?'мать':''};
 const parentCache=new Map<string,{slots:[Slot|null,Slot|null];extra:Slot[]}>();
 function parents(id:string){
  let r=parentCache.get(id);if(r)return r;
  const edges=(up.get(id)||[]).map(e=>e.role==='отец'||e.role==='мать'?e:{...e,role:roleOf(e.parent)});const father=edges.find(e=>e.role==='отец'),mother=edges.find(e=>e.role==='мать');
  const rest=edges.filter(e=>e!==father&&e!==mother);const slots:[Slot|null,Slot|null]=[father?{id:father.parent,status:firmStatus(father),likelihood:info[father.parent]?.connector||info[id]?.connector?undefined:father.likelihood,sources:father.sources,weight:father.weight,role:'отец'}:null,mother?{id:mother.parent,status:firmStatus(mother),likelihood:info[mother.parent]?.connector||info[id]?.connector?undefined:mother.likelihood,sources:mother.sources,weight:mother.weight,role:'мать'}:null];
  const extra:Slot[]=[];
  for(const e of rest){const s={id:e.parent,status:firmStatus(e),likelihood:info[e.parent]?.connector||info[id]?.connector?undefined:e.likelihood,sources:e.sources,weight:e.weight,role:e.role==='отец'||e.role==='мать'?e.role:''};if(e.role==='отец'||e.role==='мать'){extra.push(s);continue}if(!slots[0])slots[0]=s;else if(!slots[1])slots[1]=s;else extra.push(s)}
  // alternative candidates for a taken slot are kept as extras, one per person
  r={slots,extra:extra.filter((s,i,a)=>a.findIndex(x=>x.id===s.id)===i&&s.id!==slots[0]?.id&&s.id!==slots[1]?.id)};parentCache.set(id,r);return r
 }
 const relationshipEvidence=(id:string)=>[...new Set((data.edges||[]).filter((e:Row)=>(e.child===id||e.parent===id)&&connectionLevel(e)===2).flatMap((e:Row)=>e.sources||[]))] as string[];
 const children=(id:string)=>[...(down.get(id)||[])].sort(byYear);
 const hasParents=(id:string)=>!!(parents(id).slots[0]||parents(id).slots[1]);
 // Keep the union's qualification alongside navigation. Shared children alone do not establish a marriage.
 const partners=new Map<string,Map<string,{kids:number;family:boolean}>>();
 const unionLinks=new Map<string,Row>();const unionKey=(a:string,b:string)=>JSON.stringify([a,b].sort());
 const addPartner=(a:string,b:string,kids:number,family:boolean,link:Row)=>{if(!info[a]||!info[b]||a===b||REJECTED.includes(link.status))return;
  const key=unionKey(a,b);const old=unionLinks.get(key);const qualified={...link,status:link.derived===true?'hypothesis':link.status||'export'};
  if(!old||connectionLevel(qualified)<connectionLevel(old))unionLinks.set(key,qualified);
  for(const [x,y] of [[a,b],[b,a]]){let m=partners.get(x);if(!m)partners.set(x,m=new Map());const o=m.get(y);m.set(y,{kids:(o?.kids||0)+kids,family:(o?.family||false)||family})}};
 (data.families||[]).forEach((f:Row)=>addPartner(f.husband,f.wife,0,true,f));
 (data.associations||[]).filter((a:Row)=>a.type==='spouse').forEach((a:Row)=>addPartner(a.from,a.to,0,true,a));
 Object.keys(info).forEach(c=>{const [f,m]=parents(c).slots;if(f&&m)addPartner(f.id,m.id,1,false,{status:'hypothesis'})});
 const spouseConnection=(a:string,b:string):Row=>unionLinks.get(unionKey(a,b))||{status:'hypothesis'};
 const husbands=new Set<string>((data.families||[]).map((f:Row)=>f.husband));
 const spouses=(id:string)=>[...(partners.get(id)||new Map()).entries()].sort((a,b)=>b[1].kids-a[1].kids||Number(b[1].family)-Number(a[1].family)||byYear(a[0],b[0])).map(([pid])=>pid);
 const siblings=(id:string)=>{const set=new Set<string>();const {slots}=parents(id);slots.forEach(s=>s&&children(s.id).forEach(c=>c!==id&&set.add(c)));(data.associations||[]).filter((a:Row)=>a.type==='sibling'&&!REJECTED.includes(a.status)).forEach((a:Row)=>{if(a.from===id&&info[a.to])set.add(a.to);if(a.to===id&&info[a.from])set.add(a.from)});return [...set].sort(byYear)};
 // the four lines running up from the two home people, used for colour only
 // the home couple is the root of the export and the root's first partner, so no person id is written into the code
 const branch=new Map<string,number>();const homes:string[]=[data.root,spouses(data.root)[0]].filter((x,i,a)=>x&&info[x]&&a.indexOf(x)===i);const lines:{id:string;color:string;home:string;role:string;status:string}[]=[];
 homes.forEach(h=>parents(h).slots.forEach(s=>{if(!s)return;const idx=lines.length;lines.push({id:s.id,color:BRANCH_COLORS[idx%4],home:h,role:s.role,status:connectionStatus(s)});const todo=[s.id];while(todo.length){const x=todo.pop()!;if(branch.has(x))continue;branch.set(x,idx);parents(x).slots.forEach(p=>p&&todo.push(p.id))}}));
 // relationships to a home person: ancestors by distance, partner, child; honest about candidate links
 const reach=new Map<string,Map<string,{n:number;g:'m'|'f'|'';sure:boolean;path?:string[]}>>();
 homes.forEach(h=>{const m=new Map<string,{n:number;g:'m'|'f'|'';sure:boolean;path?:string[]}>();const q=[h];m.set(h,{n:0,g:'',sure:true});for(let i=0;i<q.length;i++){const x=q[i];const cur=m.get(x)!;parents(x).slots.forEach(s=>{if(s&&!m.has(s.id)){m.set(s.id,{n:cur.n+1,g:s.role==='отец'?'m':s.role==='мать'?'f':'',sure:cur.sure&&connectionLevel(s)<3});q.push(s.id)}})}reach.set(h,m)});
 const kinship=(id:string):Kin[]=>{const out:Kin[]=[];
  for(const h of homes){if(h===id)continue;const r=reach.get(h)!.get(id);const hn=info[h].short.split(' ')[0];const s=String(data.people[id]?.sex||'').toLowerCase();const g:'m'|'f'|''=s==='m'||s==='f'?s:'';
   if(r){out.push({home:hn,homeId:h,kind:'ancestor',n:r.n,g:r.g,sure:r.sure});continue}
   if(spouses(h)[0]===id)out.push({home:hn,homeId:h,kind:'spouse',n:0,g,sure:true});
   else if(children(h).includes(id))out.push({home:hn,homeId:h,kind:'child',n:0,g,sure:connectionLevel(parents(id).slots.find(s=>s?.id===h)||{})<3})}
  return out};
 const ancestorsCount=(id:string)=>{const seen=new Set<string>();const todo=[id];while(todo.length){const x=todo.pop()!;parents(x).slots.forEach(p=>{if(p&&!seen.has(p.id)){seen.add(p.id);todo.push(p.id)}})}return seen.size};
 // all ancestors of one person with the distance, the sex of the ancestor and whether every link on the way is firm
 const ancCache=new Map<string,Map<string,{n:number;g:'m'|'f'|'';sure:boolean;path?:string[]}>>();
 const ancestorsOf=(id:string)=>{let m=ancCache.get(id);if(m)return m;m=new Map();const q=[id];m.set(id,{n:0,g:'',sure:true,path:[id]});for(let i=0;i<q.length;i++){const x=q[i];const cur=m.get(x)!;parents(x).slots.forEach(s=>{if(s&&!m!.has(s.id)){m!.set(s.id,{n:cur.n+1,g:s.role==='отец'?'m':s.role==='мать'?'f':'',sure:cur.sure&&connectionLevel(s)<3,path:[...(cur.path||[]),s.id]});q.push(s.id)}})}ancCache.set(id,m);return m};
 // blood kin of exactly one line who are not its direct ancestors: brothers and sisters of ancestors and their descendants.
 // Anyone who descends from two or more lines (the home couple's children, brothers and sisters) and every in-law stays neutral.
 const kin=new Map<string,number>();
 for(const id of Object.keys(info)){if(branch.has(id)||homes.includes(id)||info[id].placeholder)continue;const found=new Set<number>();for(const a of ancestorsOf(id).keys()){const b=branch.get(a);if(b!==undefined)found.add(b)}if(found.size===1)kin.set(id,[...found][0])}
 /** The colour a person carries: full hue for a direct ancestor of a line, a light tint for other blood kin of that line, none otherwise. */
 const tone=(id:string):Tone|null=>{const b=branch.get(id);if(b!==undefined)return {line:b,kin:false,color:BRANCH_COLORS[b%4]};const k=kin.get(id);return k===undefined?null:{line:k,kin:true,color:BRANCH_TINTS[k%4]}};
 const sex=(id:string):'m'|'f'|''=>{const p=data.people[id];if(!p)return '';const s=String(p.sex||'').toLowerCase();return s==='m'||s==='f'?s:p.namePresentation?.isWoman===true?'f':(data.families||[]).some((f:Row)=>f.husband===id)?'m':(data.families||[]).some((f:Row)=>f.wife===id)?'f':''};
 /** How `id` is related to the person looking at the tree (`me`): blood relations, partners of relatives, relatives of the partner. */
 const rawRelation=(me:string,id:string):Relation|null=>{
  if(!info[me]||!info[id])return null;if(me===id)return {kind:'self',n1:0,n2:0,g:sex(id),sure:true};
  const blood=(a:string,b:string):Relation|null=>{const A=ancestorsOf(a),B=ancestorsOf(b);
   const up=A.get(b);if(up)return {kind:'ancestor',n1:up.n,n2:0,g:up.g||sex(b),sure:up.sure,path:up.path};
   const down=B.get(a);if(down)return {kind:'descendant',n1:0,n2:down.n,g:sex(b),sure:down.sure,path:down.path?.slice().reverse()};
   let best:Relation|null=null;for(const [x,ra] of A){const rb=B.get(x);if(!rb||!ra.n||!rb.n)continue;if(!best||ra.n+rb.n<best.n1+best.n2)best={kind:'collateral',n1:ra.n,n2:rb.n,g:sex(b),branchG:sex([...A].find(([p,r])=>r.n===ra.n-1&&parents(p).slots.some(s=>s?.id===x))?.[0]||a),collateralG:sex([...B].find(([p,r])=>r.n===rb.n-1&&parents(p).slots.some(s=>s?.id===x))?.[0]||b),cousinG:rb.n>ra.n?sex([...B].find(([p,r])=>r.n===rb.n-ra.n&&ancestorsOf(p).get(x)?.n===ra.n)?.[0]||b):undefined,sure:ra.sure&&rb.sure,path:[...(ra.path||[]),...(rb.path||[]).slice(0,-1).reverse()]}}
   return best};
  if(spouses(me).includes(id))return {kind:'spouse',n1:0,n2:0,g:sex(id),sure:connectionLevel(spouseConnection(me,id))<3,path:[me,id]};
  const direct=blood(me,id);if(direct)return direct;
  for(const s of spouses(id)){const r=blood(me,s);if(r)return {...r,g:sex(id),spouseOf:r,spouseG:sex(s),path:[...(r.path||[]),id],sure:r.sure&&connectionLevel(spouseConnection(s,id))<3}}
  for(const s of spouses(me)){const r=blood(s,id);if(r)return {...r,viaSpouse:sex(s),path:[me,...(r.path||[])],sure:r.sure&&connectionLevel(spouseConnection(me,s))<3}}
  // Parents of a child's spouse; husbands of sisters. These require two marriage links.
  for(const child of children(me))for(const partner of spouses(child)){
   const parent=parents(partner).slots.find(p=>p?.id===id);
   if(parent){const own=parents(child).slots.find(p=>p?.id===me);return {kind:'collateral',n1:0,n2:0,g:sex(id),special:'coParentInLaw',path:[me,child,partner,id],sure:!!own&&connectionLevel(own)<3&&connectionLevel(parent)<3&&connectionLevel(spouseConnection(child,partner))<3}}
  }
  if(sex(me)==='m'&&sex(id)==='m')for(const wife of spouses(me).filter(p=>sex(p)==='f'))for(const sister of siblings(wife).filter(p=>sex(p)==='f')){
   const kin=blood(wife,sister);if(kin&&spouses(sister).includes(id))return {kind:'collateral',n1:0,n2:0,g:'m',special:'coBrotherInLaw',path:[me,...(kin.path||[]),id],sure:kin.sure&&connectionLevel(spouseConnection(me,wife))<3&&connectionLevel(spouseConnection(sister,id))<3};
  }
  // A step or spiritual relation is never guessed from missing parent data.
  const directed:Record<string,[string,string]>={godparent:['godparent','godchild'],step_parent:['stepParent','stepChild'],step_sibling:['stepSibling','stepSibling'],coparent:['coparent','coparent']};
  for(const link of data.associations||[]){const kinds=directed[link.type];if(!kinds||REJECTED.includes(link.status))continue;
   const forward=link.from===me&&link.to===id,reverse=link.to===me&&link.from===id;
   if(forward||reverse)return {kind:'collateral',n1:0,n2:0,g:sex(id),special:kinds[forward?0:1],path:[me,id],sure:connectionLevel(link)<3};
  }
  return null};
 const relation=(me:string,id:string):Relation|null=>{
  const r=rawRelation(me,id);if(!r)return null;
  r.viewerG=sex(me);
  // A single recorded common parent does not prove that the other parents differ.
  if(r.kind==='collateral'&&r.n1===1&&r.n2===1&&!r.spouseOf&&!r.viaSpouse){
   const a=parents(me).slots,b=parents(id).slots;
   if(a.every(Boolean)&&b.every(Boolean)){
    const sameFather=a[0]!.id===b[0]!.id,sameMother=a[1]!.id===b[1]!.id;
    if(sameFather!==sameMother){r.special=sameFather?'halfFather':'halfMother';r.sure=r.sure&&[...a,...b].every(s=>connectionLevel(s!)<3)}
   }
  }
  if(r.path&&r.n1===2&&r.n2===1&&!r.spouseOf&&!r.viaSpouse)r.branchG=sex(r.path[1]);
  if(r.path&&r.n1===1&&r.n2===2&&!r.spouseOf&&!r.viaSpouse)r.collateralG=sex(r.path[r.path.length-2]);
  return r;
 };
 const primary=data.defaultViewer||data.narrator||data.root||homes[0],lang=labels.languageCode||'ru';
 for(const [pid,p] of Object.entries<Row>(data.people)){
  if(typeof p.placeholder==='string'&&p.placeholder.trim())continue;
  const n=p.names?.[0];if(!n||n.given||!('given' in n))continue;
  const r=primary&&info[primary]?relation(primary,pid):null;
  if(!r||r.kind==='self')continue;
  const viewer=data.people[primary]?.names?.[0]?.given||info[primary].short.split(' ')[0];
  const owner=labels.homeGenitive?.[viewer]||(lang==='en'?viewer+"'s":genitive(viewer,lang));
  const possessives=new Set<string>([...(labels.rel?.your||[]),...(labels.rel?.yourGen||[])].map(s=>s.toLocaleLowerCase()));
  const formal=relationPhrase({...r,sure:true},labels,lang).split(' ').filter(w=>!possessives.has(w.toLocaleLowerCase())).join(' ');
  const word=r.kind==='ancestor'&&!r.spouseOf&&!r.viaSpouse?relWord(r.n1,r.g,lang):formal;
  if(!word)continue;
  const kin=labels.genitiveFirst?`${owner} ${word}`:`${word} ${owner}`;
  const name=n?.surname?`${n.surname} (${kin})`:kin;
  Object.assign(info[pid],{name,short:name,fullName:name,alt:'',note:'',unnamed:true});
 }
 return {connectionLevel,connectionStatus,relationshipEvidence,info,parents,children,hasParents,spouses,spouseConnection,siblings,husbands,branch,kin,tone,lines,ancestorsCount,homes,kinship,relation,ancestorsOf};
}
