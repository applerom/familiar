# START_MODULE_CONTRACT: MOD-INTAKE-NAMES
# PURPOSE: Offer explainable identity candidates across scripts and all attributed name forms.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - spelling similarity proposes candidates and never changes canonical identity [review: engine lead]
# CHANGES_WITH:
# - MOD-INTAKE-CORE (candidate evidence)
# :END_MODULE_CONTRACT
import re
import unicodedata
from difflib import SequenceMatcher


def _form(value):
    cyr = dict(zip('абвгдеёзийклмнопрстуфхыэ',
                   ('a','b','v','g','d','e','e','z','i','i','k','l','m','n','o','p','r','s','t','u','f','h','y','e')))
    cyr.update({'ж':'zh','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ю':'yu','я':'ya','ь':'','ъ':''})
    value = ''.join(cyr.get(c, c) for c in value.casefold())
    value = ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))
    for a, b in [('sch','sh'), ('tsch','ch'), ('lj','l'), ('dj','d'), ('jj','i'), ('j','i'), ('w','v'), ('y','i')]:
        value = value.replace(a,b)
    return re.sub(r'[^a-z]', '', value)


def _overlap(first, second):
    for a in first:
        for b in second:
            given_a, given_b = (a.get('given') or '').split(), (b.get('given') or '').split()
            if not given_a or not given_b:
                continue
            ga, gb = _form(given_a[0]), _form(given_b[0])
            sa, sb = _form(a.get('surname') or ''), _form(b.get('surname') or '')
            if not ga or not gb or not sa or not sb:
                continue
            if (min(SequenceMatcher(None, ga, gb).ratio(), SequenceMatcher(None, sa, sb).ratio()) >= .78):
                return {'given': [a['given'], b['given']], 'surname': [a['surname'], b['surname']],
                        'comparison': 'all name forms; script transliteration and spelling similarity; not identity evidence'}
    return None
