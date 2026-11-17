# START_MODULE_CONTRACT: MOD-INTAKE-SHEET
# PURPOSE: Read addressed spreadsheet cells without network access or spreadsheet dependencies.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - rich strings, links and raw numeric values remain inspectable alongside displayed dates [review: engine lead]
# CHANGES_WITH:
# - MOD-INTAKE-TABLE
# :END_MODULE_CONTRACT
import csv
import io
import posixpath
import re
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def column(n):
    result = ''
    while n:
        n, rest = divmod(n - 1, 26)
        result = chr(65 + rest) + result
    return result


def cells(blob, suffix):
    if suffix.lower() in {'.csv', '.tsv'}:
        text = blob.decode('utf-8-sig')
        delimiter = '\t' if suffix.lower() == '.tsv' else csv.Sniffer().sniff(text[:8192], delimiters=',;\t').delimiter
        return [{'sheet': 'Sheet1', 'row': r, 'col': column(c), 'address': f'Sheet1!{column(c)}{r}', 'text': v}
                for r, row in enumerate(csv.reader(io.StringIO(text), delimiter=delimiter), 1)
                for c, v in enumerate(row, 1) if v != '']
    if suffix.lower() != '.xlsx':
        raise ValueError('Expected UTF-8 CSV/TSV or XLSX')
    try:
        with ZipFile(io.BytesIO(blob)) as archive:
            return _xlsx(archive)
    except (BadZipFile, ET.ParseError, KeyError) as exc:
        raise ValueError(f'Invalid XLSX: {exc}') from exc


def _xlsx(z):
    def xml(name):
        return ET.fromstring(z.read(name))

    def strings(node):
        return ''.join(t.text or '' for t in node.findall('.//s:t', NS))

    shared = [strings(s) for s in xml('xl/sharedStrings.xml')] if 'xl/sharedStrings.xml' in z.namelist() else []
    formats, styles = {}, []
    if 'xl/styles.xml' in z.namelist():
        root = xml('xl/styles.xml')
        formats = {int(n.attrib['numFmtId']): n.attrib['formatCode'] for n in root.findall('s:numFmts/s:numFmt', NS)}
        styles = [int(n.attrib.get('numFmtId', 0)) for n in root.findall('s:cellXfs/s:xf', NS)]
    wb = xml('xl/workbook.xml')
    epoch = wb.find('s:workbookPr', NS)
    epoch1904 = epoch is not None and epoch.attrib.get('date1904') in {'1', 'true'}
    targets = {n.attrib['Id']: n.attrib['Target'] for n in xml('xl/_rels/workbook.xml.rels')}
    result = []
    for sheet in wb.findall('s:sheets/s:sheet', NS):
        target = targets[sheet.attrib[f'{{{REL}}}id']]
        path = posixpath.normpath('xl/' + target) if not target.startswith('/') else target.lstrip('/')
        root = xml(path)
        relpath = posixpath.dirname(path) + '/_rels/' + posixpath.basename(path) + '.rels'
        links = {n.attrib['Id']: n.attrib['Target'] for n in xml(relpath)} if relpath in z.namelist() else {}
        hyperlinks = {n.attrib['ref']: links.get(n.attrib.get(f'{{{REL}}}id'), n.attrib.get('location', ''))
                      for n in root.findall('s:hyperlinks/s:hyperlink', NS)}
        for n in root.findall('s:sheetData/s:row/s:c', NS):
            ref = n.attrib['r']
            raw = n.findtext('s:v', '', NS)
            kind = n.attrib.get('t')
            text = shared[int(raw)] if kind == 's' else strings(n) if kind == 'inlineStr' else raw
            formula = n.findtext('s:f', '', NS)
            if not text and not formula and ref not in hyperlinks:
                continue
            cell = {'sheet': sheet.attrib['name'], 'row': int(re.search(r'\d+', ref)[0]),
                    'col': re.match('[A-Z]+', ref)[0], 'address': sheet.attrib['name'] + '!' + ref, 'text': text}
            if formula:
                cell['formula'] = formula
            if ref in hyperlinks:
                cell['link'] = hyperlinks[ref]
            style = int(n.attrib.get('s', 0))
            fmt = styles[style] if style < len(styles) else 0
            code = formats.get(fmt, '')
            if kind not in {'s', 'inlineStr', 'b', 'e', 'str'} and raw:
                cell['raw_number'] = raw
                cell['number_format'] = code or str(fmt)
                # Only supported date-only displays are rendered. Others are explicit losses.
                if fmt in {14, 15, 16, 17} or re.search('[dy]', re.sub(r'"[^"]*"|\[[^]]*\]', '', code), re.IGNORECASE):
                    serial = float(raw)
                    if not epoch1904 and int(serial) == 60:
                        cell['display_gap'] = 'Excel fictitious 1900-02-29'
                    else:
                        base = datetime(1904, 1, 1) if epoch1904 else datetime(1899, 12, 31)
                        dt = base + timedelta(days=serial - (not epoch1904 and serial >= 60))
                        cell['date'] = dt.date().isoformat()
                        if code.lower() == 'd mmmm yyyy':
                            months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
                            cell['text'] = f'{dt.day} {months[dt.month - 1]} {dt.year}'
                            cell['display_rule'] = 'Russian rendering assumed; workbook has no display locale'
                        elif fmt == 14:
                            cell['text'] = f'{dt.month:02}/{dt.day:02}/{dt.year % 100:02}'
                            cell['display_rule'] = 'Builtin 14 assumed m/d/yy; Excel locale may differ'
                        else:
                            cell['display_gap'] = 'Unsupported date display format; raw value and ISO date retained'
            result.append(cell)
    return result
