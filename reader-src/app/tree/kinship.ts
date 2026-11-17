/*
START_MODULE_CONTRACT: MOD-READER-KINSHIP
PURPOSE: Resolve a qualified tree relation against the language pack's inspectable word table.
PRD_REF: docs/PRD.md#KINSHIP-WORDS
INVARIANTS:
- a word never supplies a missing sex, parent, marriage or spiritual link [review: engine lead]
- dictionary examples consume only the already permitted reader graph [review: engine lead]
CHANGES_WITH:
- regions/CONTRACT.md (kinship table and fallback)
- regions/ru/kinship.json
- regions/pl/kinship.json
- regions/demo-english/kinship.json
:END_MODULE_CONTRACT
*/
import ru from '../../../regions/ru/kinship.json';
import pl from '../../../regions/pl/kinship.json';
import en from '../../../regions/demo-english/kinship.json';
import type {Relation} from './model';
export type Term={id:string;word:string;explanation:string;group:string;archaic?:boolean;match?:Record<string,string|number>[]};
export type Lexicon={title:string;intro:string;example:string;noExample:string;chooseViewer:string;archaic:string;maybe:string;path:string;labels:Record<string,any>;fallback:Record<string,string>;genitive:Record<string,string>;groups:Record<string,string>;terms:Term[]};
const packs:Record<string,Lexicon>={ru,pl,en};
export const kinshipLexicon=(language:string):Lexicon|undefined=>packs[language];
/** A semantic descriptor, independent of language. The table owns every displayed word. */
export function kinshipTerm(r:Relation,language:string):Term|undefined{
 const pack=kinshipLexicon(language);if(!pack)return;
 const source=r.spouseOf||r;
 const key:Record<string,string|number>={kind:source.kind,n1:source.n1,n2:source.n2,g:r.g,
  viewerG:r.viewerG||'',branchG:r.branchG||'',collateralG:r.collateralG||'',viaSpouse:r.viaSpouse||'',
  spouseOf:r.spouseOf?'yes':'',spouseG:r.spouseG||'',special:r.special||''};
 return pack.terms.find(t=>t.match?.some(m=>Object.entries(m).every(([k,v])=>key[k]===v)));
}
export function termPhrase(r:Relation,language:string){const term=kinshipTerm(r,language);return term?(r.sure?'':kinshipLexicon(language)!.maybe)+term.word:undefined}
