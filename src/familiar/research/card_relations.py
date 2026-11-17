# START_MODULE_CONTRACT: MOD-PERSON-CARD-RELATIONS
# PURPOSE: Preserve the reader relationship calculation and Russian phrases for author diagnostics.
# PRD_REF: docs/PRD.md#PERSON-CARD
# INVARIANTS:
# - tentative reader paths keep their uncertainty marker; unrelated people have no invented kinship [review: engine lead]
# CHANGES_WITH:
# - MOD-PERSON-CARD-OVERVIEW (Node stdin protocol)
# :END_MODULE_CONTRACT
SCRIPT = r'''// Extracted from the pilot reader tree model; calculation and phrase functions preserved.
export function connectionLevel(edge) {
    return edge.status === 'verified' || edge.status === 'export' ? 1 : edge.status === 'hypothesis' && edge.likelihood === 'probable' ? 2 : 3;
}
export const connectionStatus = (edge) => connectionLevel(edge) === 3 ? 'hypothesis' : connectionLevel(edge) === 2 ? 'probable' : edge.status || 'export';
const REJECTED = ['rejected', 'disproved'];
const RANK = { verified: 0, export: 1, conflict: 2, hypothesis: 3 };
const rank = (s) => RANK[s] ?? 2;
const MAYBE = { ru: 'возможно, ', pl: 'możliwe: ', en: 'possibly ', sv: 'möjligen ' };
const PL_GEN = { ojciec: 'ojca', matka: 'matki', rodzic: 'rodzica', dziadek: 'dziadka', babcia: 'babci', brat: 'brata', siostra: 'siostry', wuj: 'wuja', ciocia: 'cioci', kuzyn: 'kuzyna', kuzynka: 'kuzynki', syn: 'syna', córka: 'córki', wnuk: 'wnuka', wnuczka: 'wnuczki', mąż: 'męża', żona: 'żony', bratanek: 'bratanka', bratanica: 'bratanicy', przodek: 'przodka', krewny: 'krewnego', krewna: 'krewnej', dziecko: 'dziecka' };
const RU_GEN = { отец: 'отца', мать: 'матери', дочь: 'дочери', предок: 'предка', родитель: 'родителя', ребёнок: 'ребёнка' };
export function genitive(word, lang) { return genitive0(word, lang); }
function genitive0(word, lang) {
    if (lang === 'en')
        return word + "'s";
    if (lang === 'sv')
        return /[sxz]$/.test(word) ? word : word + 's';
    return word.split(' ').map(w => {
        if (lang === 'pl') {
            for (const [k, v] of Object.entries(PL_GEN))
                if (w.endsWith(k))
                    return w.slice(0, -k.length) + v;
            return w;
        }
        for (const [k, v] of Object.entries(RU_GEN))
            if (w.endsWith(k))
                return w.slice(0, -k.length) + v;
        if (/ый$/.test(w))
            return w.slice(0, -2) + 'ого';
        if (/ий$/.test(w))
            return w.slice(0, -2) + 'его';
        if (/ая$/.test(w))
            return w.slice(0, -2) + 'ой';
        if (/[кгхжшчщ]а$/.test(w))
            return w.slice(0, -1) + 'и';
        if (/а$/.test(w))
            return w.slice(0, -1) + 'ы';
        if (/я$/.test(w))
            return w.slice(0, -1) + 'и';
        if (/ь$/.test(w))
            return w.slice(0, -1) + 'я';
        return w + 'а';
    }).join(' ');
}
export function relationPhrase(r, labels, lang0) {
    const lang = lang0 === 'sv' ? 'en' : lang0, sv = lang0 === 'sv';
    const relWord = (n, g, _l) => relWord0(n, g, lang0);
    const genitive = (w, _l) => genitive0(w, lang0);
    const cousinWord = (n, g, _l) => cousinWord0(n, g, lang0);
    const R = labels.rel;
    const gi = (g) => g === 'f' ? 1 : 0;
    const base = (x) => {
        if (x.kind === 'spouse')
            return R.spouse[gi(x.g)];
        if (x.kind === 'ancestor')
            return relWord(x.n1, x.g, lang);
        if (x.kind === 'descendant')
            return x.n2 === 1 ? R.child[gi(x.g)] : x.n2 === 2 ? R.grandchild[gi(x.g)] : R.great.repeat(x.n2 - 2) + R.grandchild[gi(x.g)];
        const key = { '1,1': 'sibling', '2,1': 'uncle', '1,2': 'nephew', '2,2': 'cousin', '3,1': 'greatUncle', '1,3': 'grandNephew', '3,2': 'cousinUncle', '2,3': 'cousinNephew', '3,3': 'secondCousin' }[`${x.n1},${x.n2}`] || 'distant';
        return R[key][gi(x.g)];
    };
    const explain = (key, n = 0) => { const E = labels.relExplain || {}; if (key === 'cousinN')
        return n ? String(E.cousinN || '').replace('{a}', relWord(n, 'm', lang)) : ''; return E[key] || ''; };
    const withExplain = (w, e) => e ? `${w} (${e})` : w;
    let text;
    if (r.kind === 'self')
        text = R.self;
    else if (r.spouseOf) {
        const w = base(r.spouseOf), g = r.spouseOf.g;
        text = lang === 'en' ? `${R.your[0]} ${genitive(w, lang)} ${R.spouse[gi(r.g)]}` : `${R.spouse[gi(r.g)]} ${R.yourGen[gi(g)]} ${genitive(w, lang)}`;
    }
    else if (r.viaSpouse) {
        const w = base(r);
        text = lang === 'en' ? `${R.your[0]} ${genitive(R.spouse[gi(r.viaSpouse)], lang)} ${w}` : `${w} ${R.yourGen[gi(r.viaSpouse)]} ${R.spouseGen[gi(r.viaSpouse)]}`;
    }
    else if (r.kind === 'collateral' && r.n1 === r.n2 && r.n1 >= 4) {
        const w = cousinWord(r.n1, r.g, lang);
        text = `${R.your[gi(r.g)]} ${withExplain(w, explain('cousinN', r.n1))}`;
    }
    else if (r.kind === 'collateral' && r.n1 !== r.n2 && (r.n1 >= 3 || r.n2 >= 3) && !sv && (lang === 'ru' || lang === 'en')) {
        text = `${R.your[gi(r.g)]} ${collateralWord(r.n1, r.n2, r.g, lang, r.cousinG)}`;
    }
    else if (r.kind === 'collateral' && (r.n1 > 3 || r.n2 > 3)) {
        const owner = r.n1 === 1 ? R.sibling[gi(r.collateralG || 'm')] : relWord(r.n1 - 1, r.branchG || 'm', lang);
        const sibling = R.sibling[gi(r.n2 === 1 ? r.g : r.collateralG || 'm')];
        const of = (word, whose, g) => lang === 'en' ? `${R.your[0]} ${genitive(whose, lang)} ${word}` : `${word} ${R.yourGen[gi(g)]} ${genitive(whose, lang)}`;
        if (r.n1 === 1)
            text = of(base({ ...r, kind: 'descendant', n2: r.n2 - 1 }), owner, r.collateralG || 'm');
        else if (r.n2 === 1)
            text = of(sibling, owner, r.branchG || 'm');
        else {
            const descendant = base({ ...r, kind: 'descendant', n2: r.n2 - 1 });
            const ancestry = of(sibling, owner, r.branchG || 'm');
            text = lang === 'en' ? `${descendant} of ${ancestry}` : `${descendant} ${of(genitive(sibling, lang), owner, r.branchG || 'm')}`;
        }
    }
    else {
        const w = base(r);
        const key = r.kind === 'collateral' ? { '3,1': 'greatUncle', '1,3': 'grandNephew', '3,2': 'cousinUncle', '2,3': 'cousinNephew', '3,3': 'secondCousin' }[`${r.n1},${r.n2}`] || '' : '';
        text = `${R.your[gi(r.g)]} ${withExplain(w, key === 'secondCousin' ? explain('cousinN', 3) : explain(key))}`;
    }
    return (r.sure ? '' : (MAYBE[lang0] || MAYBE.ru)) + text;
}
export function kinPhrase(k, labels, lang) {
    const gen = labels.homeGenitive?.[k.home] || k.home;
    const word = k.kind === 'ancestor' ? relWord(k.n, k.g, lang) : k.kind === 'spouse' ? (k.g === 'f' ? labels.wifeOf : labels.husbandOf) : (k.g === 'f' ? labels.daughterOf : k.g === 'm' ? labels.sonOf : labels.childOf);
    const text = labels.genitiveFirst ? `${gen} ${word}` : `${word} ${gen}`;
    return (k.sure ? '' : (MAYBE[lang] || MAYBE.ru)) + text;
}
const ORD_RU = ['', '', 'двоюродн', 'троюродн', 'четвероюродн', 'пятиюродн', 'шестиюродн', 'семиюродн'];
const ordRu = (k, f) => k < 2 ? '' : (ORD_RU[k] || `${k}-юродн`) + (f ? 'ая' : 'ый') + ' ';
const ordRuGen = (k) => k < 2 ? '' : (ORD_RU[k] || `${k}-юродн`) + 'ого ';
function collateralWord(n1, n2, g, lang, cousinG = 'm') {
    const f = g === 'f';
    if (lang === 'en') {
        if (n2 === 1) {
            const d = n1 - 2;
            return `${'great-'.repeat(d)}${f ? 'grandaunt' : 'granduncle'} (a ${relWord(n1 - 1, 'm', lang).replace('grandfather', 'grandparent')}’s ${f ? 'sister' : 'brother'})`;
        }
        if (n1 === 1) {
            const d = n2 - 2;
            return `${'great-'.repeat(d - 1)}${d ? 'grand' : ''}${f ? 'niece' : 'nephew'} (a sibling’s ${relWordDesc(n2 - 1, lang)})`;
        }
        const k = Math.min(n1, n2) - 1, rem = Math.abs(n1 - n2);
        const o = ['', 'first', 'second', 'third', 'fourth', 'fifth'][k] || `${k}th`;
        return `${o} cousin ${rem === 1 ? 'once' : rem === 2 ? 'twice' : rem + ' times'} removed (${n1 > n2 ? `a ${relWord(n1 - n2, 'm', lang).replace('father', 'parent')}’s ${o} cousin` : `a ${o} cousin’s ${relWordDesc(n2 - n1, lang)}`})`;
    }
    if (n1 > n2) {
        const d = n1 - n2;
        const anc = relWord(d, g, lang);
        const k = d === 1 ? n2 : n2 + 1;
        const word = d === 1 ? (f ? 'тётя' : 'дядя') : anc;
        const expl = `${ordRu(n2, f)}${f ? 'сестра' : 'брат'} ${genitive(relWord(d, 'm', lang), lang)}`;
        return `${ordRu(k, f)}${word} (${expl})`.replace('двоюродная тётя (сестра', 'тётя (сестра').replace('двоюродный дядя (брат ', 'дядя (брат ');
    }
    const d = n2 - n1;
    const word = (d === 1 ? '' : d === 2 ? 'внучат' : 'правнучат') + (d === 1 ? '' : (f ? 'ая ' : 'ый ')) + (f ? 'племянница' : 'племянник');
    const who = d === 1 ? (f ? 'дочь' : 'сын') : d === 2 ? (f ? 'внучка' : 'внук') : (f ? 'правнучка' : 'правнук');
    const sister = cousinG === 'f';
    return `${ordRu(n1, f)}${word} (${who} ${sister ? ordRuGen(n1).replace(/ого $/, 'ой ') : ordRuGen(n1)}${sister ? 'сестры' : 'брата'})`;
}
function relWordDesc(n, lang) { if (lang === 'en')
    return n === 1 ? 'child' : `${'great-'.repeat(n - 2)}grandchild`; return n === 1 ? 'ребёнок' : `${'пра'.repeat(n - 2)}внук`; }
const cousinWord0 = cousinWord;
function cousinWord(n, g, lang) {
    const f = g === 'f';
    if (lang === 'sv') {
        return f && n === 2 ? 'kusin' : ['', '', 'kusin', 'tremänning', 'fyrmänning', 'femmänning', 'sexmänning', 'sjumänning'][n] || `${n - 1}:e kusin`;
    }
    if (lang === 'en') {
        const o = ['', '', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh'][n] || `${n - 1}th`;
        return `${o} cousin`;
    }
    if (lang === 'pl') {
        const o = ['', '', 'drugiego', 'trzeciego', 'czwartego', 'piątego', 'szóstego', 'siódmego'][n] || `${n}.`;
        return `${f ? 'kuzynka' : 'kuzyn'} ${o} stopnia`;
    }
    const o = ['', '', 'двою', 'трою', 'четверою', 'пятию', 'шестию', 'семию'][n] || `${n}-ю`;
    return `${o}родн${f ? 'ая сестра' : 'ый брат'}`;
}
const relWord0 = relWord;
function relWord(n, g, lang) {
    const pick = (m, f, x) => g === 'm' ? m : g === 'f' ? f : x;
    if (lang === 'pl') {
        if (n === 1)
            return pick('ojciec', 'matka', 'rodzic');
        if (n === 2)
            return pick('dziadek', 'babcia', 'dziadek lub babcia');
        if (n <= 5) {
            const p = 'pra'.repeat(n - 2);
            return pick(p + 'dziadek', p + 'babcia', 'przodek');
        }
        return `przodek, ${n} pokoleń wstecz`;
    }
    if (lang === 'sv') {
        if (n === 1)
            return pick('far', 'mor', 'förälder');
        if (n === 2)
            return pick('farfar eller morfar', 'farmor eller mormor', 'far- eller morförälder');
        if (n === 3)
            return pick('farfars eller morfars far', 'farmors eller mormors mor', 'förälder till en far- eller morförälder');
        return `förfader, ${n} generationer bakåt`;
    }
    if (lang === 'en') {
        if (n === 1)
            return pick('father', 'mother', 'parent');
        if (n === 2)
            return pick('grandfather', 'grandmother', 'grandparent');
        if (n <= 6) {
            const p = n === 3 ? 'great-' : `${n - 2}× great-`;
            return p + pick('grandfather', 'grandmother', 'grandparent');
        }
        return `ancestor, ${n} generations back`;
    }
    if (n === 1)
        return pick('отец', 'мать', 'родитель');
    if (n === 2)
        return pick('дедушка', 'бабушка', 'дедушка или бабушка');
    if (n <= 5) {
        const p = 'пра'.repeat(n - 2);
        return pick(p + 'дед', p + 'бабушка', 'предок');
    }
    return `предок, ${n} поколений назад`;
}
const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const WORDS = { ru: { abt: '≈', bef: 'до', aft: 'после', from: 'с' }, pl: { abt: '≈', bef: 'przed', aft: 'po', from: 'od' }, en: { abt: '≈', bef: 'before', aft: 'after', from: 'from' }, sv: { abt: '≈', bef: 'före', aft: 'efter', from: 'från' } };
export function relations(data, selected, labels) {
    const info = Object.fromEntries(Object.entries(data.people).map(([id,p])=>{
        const main=(p.name||'').split(' · ')[0], np=p.namePresentation||{};
        const b=(p.events||[]).find(e=>e.tag==='BIRT'&&(e.date||e.place));
        const date=p.cardPresentation?.birth??b?.date;
        const match=/\b(\d{4})\b/.exec(date||'');
        return [id,{name:np.full||main,isWoman:!!np.isWoman,unknownSurname:!!np.surnameUnknown,
          placeholder:/^[\s\-–—]*(удалить|delete|usunąć)\b/i.test(main)||!/\p{L}/u.test(main),
          birth:match?+match[1]:undefined}];
    }));
    const inOriginal = (id) => !!data.cardStatuses?.[id]?.in_original_tree;
    const firmStatus = (e) => e.status === 'hypothesis' && e.sources?.includes('snapshot') && inOriginal(e.child) && inOriginal(e.parent) && !data.people[e.parent]?.relationshipUncertain ? 'export' : e.status;
    const up = new Map(), down = new Map();
    const push = (m, k, v) => { const a = m.get(k); a ? a.push(v) : m.set(k, [v]); };
    (data.edges || []).filter((e) => !REJECTED.includes(e.status) && info[e.child] && info[e.parent] && e.child !== e.parent && !info[e.child].placeholder && !info[e.parent].placeholder).sort((a, b) => connectionLevel({ ...a, status: firmStatus(a) }) - connectionLevel({ ...b, status: firmStatus(b) }) || rank(a.status) - rank(b.status)).forEach((e) => { push(up, e.child, e); const kids = down.get(e.parent); if (!kids?.includes(e.child))
        push(down, e.parent, e.child); });
    const byYear = (a, b) => (info[a].birth ?? 9999) - (info[b].birth ?? 9999) || info[a].name.localeCompare(info[b].name, 'ru');
    const parentCache = new Map();
    function parents(id) {
        let r = parentCache.get(id);
        if (r)
            return r;
        const edges = up.get(id) || [];
        const father = edges.find(e => e.role === 'отец'), mother = edges.find(e => e.role === 'мать');
        const rest = edges.filter(e => e !== father && e !== mother);
        const slots = [father ? { id: father.parent, status: firmStatus(father), likelihood: father.likelihood, sources: father.sources, role: 'отец' } : null, mother ? { id: mother.parent, status: firmStatus(mother), likelihood: mother.likelihood, sources: mother.sources, role: 'мать' } : null];
        const extra = [];
        for (const e of rest) {
            const s = { id: e.parent, status: firmStatus(e), likelihood: e.likelihood, sources: e.sources, role: e.role === 'отец' || e.role === 'мать' ? e.role : '' };
            if (e.role === 'отец' || e.role === 'мать') {
                extra.push(s);
                continue;
            }
            if (!slots[0])
                slots[0] = s;
            else if (!slots[1])
                slots[1] = s;
            else
                extra.push(s);
        }
        r = { slots, extra: extra.filter((s, i, a) => a.findIndex(x => x.id === s.id) === i && s.id !== slots[0]?.id && s.id !== slots[1]?.id) };
        parentCache.set(id, r);
        return r;
    }
    const relationshipEvidence = (id) => [...new Set((data.edges || []).filter((e) => (e.child === id || e.parent === id) && connectionLevel(e) === 2).flatMap((e) => e.sources || []))];
    const children = (id) => [...(down.get(id) || [])].sort(byYear);
    const hasParents = (id) => !!(parents(id).slots[0] || parents(id).slots[1]);
    const partners = new Map();
    const addPartner = (a, b, kids, family) => { if (!info[a] || !info[b] || a === b)
        return; for (const [x, y] of [[a, b], [b, a]]) {
        let m = partners.get(x);
        if (!m)
            partners.set(x, m = new Map());
        const o = m.get(y);
        m.set(y, { kids: (o?.kids || 0) + kids, family: (o?.family || false) || family });
    } };
    (data.families || []).forEach((f) => addPartner(f.husband, f.wife, 0, true));
    (data.associations || []).filter((a) => a.type === 'spouse' && !REJECTED.includes(a.status)).forEach((a) => addPartner(a.from, a.to, 0, true));
    Object.keys(info).forEach(c => { const [f, m] = parents(c).slots; if (f && m)
        addPartner(f.id, m.id, 1, false); });
    const husbands = new Set((data.families || []).map((f) => f.husband));
    const spouses = (id) => [...(partners.get(id) || new Map()).entries()].sort((a, b) => b[1].kids - a[1].kids || Number(b[1].family) - Number(a[1].family) || byYear(a[0], b[0])).map(([pid]) => pid);
    const siblings = (id) => { const set = new Set(); const { slots } = parents(id); slots.forEach(s => s && children(s.id).forEach(c => c !== id && set.add(c))); (data.associations || []).filter((a) => a.type === 'sibling' && !REJECTED.includes(a.status)).forEach((a) => { if (a.from === id && info[a.to])
        set.add(a.to); if (a.to === id && info[a.from])
        set.add(a.from); }); return [...set].sort(byYear); };
    const ancCache = new Map();
    const ancestorsOf = (id) => { let m = ancCache.get(id); if (m)
        return m; m = new Map(); const q = [id]; m.set(id, { n: 0, g: '', sure: true }); for (let i = 0; i < q.length; i++) {
        const x = q[i];
        const cur = m.get(x);
        parents(x).slots.forEach(s => { if (s && !m.has(s.id)) {
            m.set(s.id, { n: cur.n + 1, g: s.role === 'отец' ? 'm' : s.role === 'мать' ? 'f' : '', sure: cur.sure && connectionLevel(s) < 3 });
            q.push(s.id);
        } });
    } ancCache.set(id, m); return m; };
    const sex = (id) => info[id].isWoman ? 'f' : info[id].unknownSurname && !info[id].name ? '' : 'm';
    const relation = (me, id) => {
        if (!info[me] || !info[id])
            return null;
        if (me === id)
            return { kind: 'self', n1: 0, n2: 0, g: sex(id), sure: true };
        const blood = (a, b) => {
            const A = ancestorsOf(a), B = ancestorsOf(b);
            const up = A.get(b);
            if (up)
                return { kind: 'ancestor', n1: up.n, n2: 0, g: up.g || sex(b), sure: up.sure };
            const down = B.get(a);
            if (down)
                return { kind: 'descendant', n1: 0, n2: down.n, g: sex(b), sure: down.sure };
            let best = null;
            for (const [x, ra] of A) {
                const rb = B.get(x);
                if (!rb || !ra.n || !rb.n)
                    continue;
                if (!best || ra.n + rb.n < best.n1 + best.n2)
                    best = { kind: 'collateral', n1: ra.n, n2: rb.n, g: sex(b), branchG: sex([...A].find(([p, r]) => r.n === ra.n - 1 && parents(p).slots.some(s => s?.id === x))?.[0] || a), collateralG: sex([...B].find(([p, r]) => r.n === rb.n - 1 && parents(p).slots.some(s => s?.id === x))?.[0] || b), cousinG: rb.n > ra.n ? sex([...B].find(([p, r]) => r.n === rb.n - ra.n && ancestorsOf(p).get(x)?.n === ra.n)?.[0] || b) : undefined, sure: ra.sure && rb.sure };
            }
            return best;
        };
        if (spouses(me).includes(id))
            return { kind: 'spouse', n1: 0, n2: 0, g: sex(id), sure: true };
        const direct = blood(me, id);
        if (direct)
            return direct;
        for (const s of spouses(id)) {
            const r = blood(me, s);
            if (r)
                return { ...r, g: sex(id), spouseOf: r, spouseG: sex(s) };
        }
        for (const s of spouses(me)) {
            const r = blood(s, id);
            if (r)
                return { ...r, viaSpouse: sex(s) || 'm' };
        }
        return null;
    };
    return selected.map(id => { const r = relation(data.root, id); return { id, host: data.root, relation: r, words: r ? relationPhrase(r, labels, "ru") : "родство с хозяином семьи не установлено" }; });
}

import {readFileSync} from "node:fs";
const {graph,selected}=JSON.parse(readFileSync(0,"utf8"));
console.log(JSON.stringify(relations(graph,selected,{"rel":{"self":"это вы","your":["ваш","ваша"],"yourGen":["вашего","вашей"],"spouse":["муж","жена"],"spouseGen":["мужа","жены"],"child":["сын","дочь"],"grandchild":["внук","внучка"],"great":"пра","sibling":["брат","сестра"],"uncle":["дядя","тётя"],"nephew":["племянник","племянница"],"cousin":["двоюродный брат","двоюродная сестра"],"greatUncle":["двоюродный дед","двоюродная бабушка"],"grandNephew":["внучатый племянник","внучатая племянница"],"cousinUncle":["двоюродный дядя","двоюродная тётя"],"cousinNephew":["двоюродный племянник","двоюродная племянница"],"secondCousin":["троюродный брат","троюродная сестра"],"distant":["дальний родственник","дальняя родственница"]},"relExplain":{"greatUncle":"брат или сестра дедушки или бабушки","grandNephew":"внук или внучка брата или сестры","cousinUncle":"двоюродный брат или сестра родителя","cousinNephew":"ребёнок двоюродного брата или сестры","cousinN":"общий предок — {a}"}})));



'''

