# START_MODULE_CONTRACT: MOD-PAPER-DATES
# PURPOSE: Spell the full dates of withheld papers as readers would write them.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - the scan uses full calendar dates, preserving unrelated years and quantities [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION
# :END_MODULE_CONTRACT
import re
from datetime import date
from functools import cache
from itertools import product


NUMERIC_DATE = re.compile(r'(?<!\d)(?:\d{4}[-./]\d{1,2}[-./]\d{1,2}|'
                          r'\d{1,2}[-./]\d{1,2}[-./]\d{4})(?!\d)')
MONTH_PACKS = {'en': 'demo-english', 'pl': 'pl', 'ru': 'ru'}
SWEDISH_MONTHS = 'januari februari mars april maj juni juli augusti september oktober november december'.split()


def full_dates(text, named_date, month_numbers):
    for match in NUMERIC_DATE.finditer(text):
        first, middle, last = re.split(r'[-./]', match[0])
        if len(first) == 4:
            orders = [(first, middle, last)]
        else:
            orders = [(last, middle, first), (last, first, middle)]
        for parts in orders:
            try:
                yield date(*map(int, parts))
            except ValueError:
                continue
    if named_date is not None:
        for match in named_date.finditer(text):
            day, month = match.group('day', 'month')
            if day is None:
                day, month = match.group('day_after', 'month_first')
            month_number = month_numbers.get(month.casefold())
            if month_number is None:
                continue
            try:
                yield date(int(match['year']), month_number, int(day))
            except ValueError:
                continue


def numeric_variants(when):
    year = f'{when.year:04}'
    for month, day in product({str(when.month), f'{when.month:02}'},
                              {str(when.day), f'{when.day:02}'}):
        for sep in ('-', '.', '/'):
            yield from (sep.join(order) for order in ((year, month, day), (day, month, year), (month, day, year)))


@cache
def bundled_months(lang):
    from .packs import bundled_root, read

    if lang in MONTH_PACKS:
        return read(bundled_root() / MONTH_PACKS[lang] / 'pack.toml')['host_format']['months']
    return SWEDISH_MONTHS if lang == 'sv' else ()


def written_variants(when, tag, month):
    from num2words import num2words

    lang = tag.split('-')[0].lower()
    try:
        day = num2words(when.day, lang=lang, to='ordinal')
        year = num2words(when.year, lang=lang)
    except NotImplementedError:
        return
    days, years = {str(when.day), f'{when.day:02}', day}, {f'{when.year:04}', year}
    if lang == 'en':
        days.add(num2words(when.day, to='ordinal_num'))
        years.update({num2words(when.year, to='year'), year.replace(' and ', ' ')})
        century, rest = divmod(when.year, 100)
        if 10 <= century < 20 and rest:
            years.add(f'{num2words(century)} hundred {num2words(rest)}')
            years.add(f'{num2words(century)} hundred and {num2words(rest)}')
    elif lang == 'ru':
        days.update(num2words(when.day, lang=lang, to='ordinal', **form)
                    for form in ({'case': 'g'}, {'gender': 'n'}))
        years.add(year.removeprefix('одна '))
        years.update(num2words(when.year, lang=lang, to='ordinal', case=case) for case in ('n', 'g'))
    elif lang == 'pl':
        def genitive(words, number):
            parts = words.split()
            last = 2 if number % 100 > 20 and number % 10 else 1
            return ' '.join(parts[:-last] + [p[:-1] + 'ego' for p in parts[-last:]])
        days.add(genitive(day, when.day))
        years.add(genitive(num2words(when.year, lang=lang, to='ordinal'), when.year))
    elif lang == 'sv':
        century, rest = divmod(when.year, 100)
        if 10 <= century < 20:
            stem = num2words(century, lang=lang)
            tail = num2words(rest, lang=lang) if rest else ''
            years.add(stem + 'hundra' + tail)
            if tail:
                years.add(f'{stem} {tail}')
        years.add(year.replace(' ', ''))
        suffix = 'a' if when.day % 10 in (1, 2) and when.day not in (11, 12) else 'e'
        days.add(f'{when.day}:{suffix}')
    for d, y in product(days, years):
        yield f'{d} {month} {y}'
        if lang == 'en':
            yield f'{d} of {month} {y}'
            yield f'{d} of {month}, {y}'
            yield f'{month} {d} {y}'
            yield f'{month} {d}, {y}'
        elif lang == 'ru':
            yield f'{y} года {month} месяца {d} числа'


def date_variants(instance, withheld, allowed):
    months = {}
    for tag in instance.languages:
        configured = instance.language_pack_data.get(tag, {}).get('data', {}).get('host_format', {}).get('months', ())
        names = configured if len(configured) == 12 else bundled_months(tag.split('-')[0].lower())
        if names:
            months[tag] = names
    month_numbers = {name.casefold(): index for names in months.values()
                     for index, name in enumerate(names, 1)}
    named_date = None
    if month_numbers:
        names = '|'.join(map(re.escape, sorted(month_numbers, key=len, reverse=True)))
        suffix = r'(?:st|nd|rd|th|:[ae])?'
        named_date = re.compile(
            rf'(?<!\w)(?:(?P<day>\d{{1,2}}){suffix}\s+(?:of\s+)?(?P<month>{names})'
            rf'|(?P<month_first>{names})\s+(?P<day_after>\d{{1,2}}){suffix})'
            r',?\s+(?P<year>\d{4})(?!\w)', re.I)
    dates = {when for term in withheld for when in full_dates(term, named_date, month_numbers)}
    dates.difference_update(when for term in allowed for when in full_dates(term, named_date, month_numbers))
    for when in dates:
        yield from numeric_variants(when)
        for tag, names in months.items():
            yield from written_variants(when, tag, names[when.month - 1])
