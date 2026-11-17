# START_MODULE_CONTRACT: MOD-PACK-CALENDAR
# PURPOSE: Convert an explicitly identified calendar date only within a loaded region pack's coverage.
# PRD_REF: docs/PRD.md#REGION-PACK
# INVARIANTS:
# - Julian century leap days convert by day number and uncovered places remain gaps [review: engine lead]
# CHANGES_WITH:
# - regions/CONTRACT.md
# :END_MODULE_CONTRACT
from datetime import date

from .packs import pack_file, read


def calendar(instance, text, country, style):
    y, m, d = map(int, text.split('-'))
    if not 1 <= y <= 9999 or not 1 <= m <= 12:
        raise ValueError('invalid date')
    leap = y % 4 == 0 and (style == 'julian' or y % 100 != 0 or y % 400 == 0)
    lengths = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if not 1 <= d <= lengths[m - 1]:
        raise ValueError('invalid day')
    pack = next((p for p in reversed(instance.packs)
                 if country in p['data'].get('pack', {}).get('countries', [])
                 and len(p['data']['pack'].get('years', [])) == 2
                 and p['data']['pack']['years'][0] <= y <= p['data']['pack']['years'][1]), None)
    if pack is None:
        return {'gap': 'No region pack covers this country and year.', 'country': country, 'year': y}
    file = pack['data']['pack'].get('files', {}).get('chronology')
    rows = read(pack_file(pack, file)).get('calendar', []) if file else []
    basis = [r for r in rows if country in r['countries'] and r['years'][0] <= y <= r['years'][1]]
    if not basis:
        return {'pack': pack['id'], 'gap': 'Pack has no calendar coverage for this date.'}
    a = (14 - m) // 12
    yy, mm = y + 4800 - a, m + 12 * a - 3
    jdn = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4
    jdn -= 32083
    if style == 'gregorian':
        jdn = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    modern = date.fromordinal(jdn - 1721425)
    c = jdn + 32082
    jy = (4 * c + 3) // 1461
    e = c - 1461 * jy // 4
    jm = (5 * e + 2) // 153
    jd = e - (153 * jm + 2) // 5 + 1
    julian = f'{jy - 4800 + jm // 10:04d}-{jm + 3 - 12 * (jm // 10):02d}-{jd:02d}'
    return {'pack': pack['id'], 'input_style': style, 'julian': julian,
            'gregorian': modern.isoformat(), 'weekday': modern.strftime('%A'),
            'basis': basis, 'style_note': 'Input style is supplied by the reader; pack context does not establish a register style.',
            'church_season': {'gap': 'No computable church season or fast table in this pack.'}}
