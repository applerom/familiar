# START_MODULE_CONTRACT: MOD-DEMO-TABLE
# PURPOSE: Reproduce a fictional unsolicited relatives sheet with rich text, date serials and a variant footnote.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - this fixture contains only invented people and example.org links [review: engine lead]
# CHANGES_WITH:
# - demo-russian/inputs/relatives.csv
# - demo-russian/inputs/relatives.xlsx
# :END_MODULE_CONTRACT
import csv
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from familiar.intake.sheet import column


def main():
    folder = Path(__file__).resolve().parents[1] / 'demo-russian/inputs'
    rows = [
        ['Персона/Степень родства с заявителем', 'Год/месяц рождения', 'Место рождения/смерти', 'Дата смерти', ''],
        ['Орешкин Пётр Савельевич - дедушка по мат линии', 'март (?) 1931', 'деревня Тихая Лоза, Лозовский сельсовет, Боровской район, Н-ская область', '', ''],
        ['Орешкина (Забела) Нина Тимофеевна - бабушка по мат линии', '3 (?) июня 1929(31)', 'то же место', '', ''],
        ['Забела Дарья Игнатьевна - прабабушка по мат линии', '9 мая 1907 года', 'то же место', '', ''],
        ['Забела Тимофей Савельевич', '', 'то же место', '', 'выслан на север, вернули в Городок - > ушел на войну (пропал без вести) https://example.org/record/12345?last_name=%D0%97%D0%B0%D0%B1%D0%B5%D0%BB%D0%BE+'],
        ['Гулик Игнат - прапрадед по мат линии', '-', 'то же место', '1921 (от тифа)', ''],
        ['Гулик анна савична - прапрабабушка', '', '1880?', '1946(?)', ''],
        ['Гулеш Марк - двоюродный прапрадед', '', '', '', ''],
        ['Ветров Олег Олегович - отец', '21287', 'деревня Сухой Бор в Боровском сельсовете Лесного района Н-ской области', '', ''],
        ['Климова (в девичестве) Вера Фоминична - бабушка по отцу', '11000', 'деревня Мокрый Луг в Боровском сельсовете ...', '', ''],
        ['', '', '', '', ''],
        ['* с фамилей Забела - могут быть разночтения: Забела, Забело, Зобело', '', '', '', ''],
    ]
    # CSV carries display strings; unlike XLSX it cannot carry numeric formatting.
    from familiar.intake.sheet import cells
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    sheet, shared = [], []
    for r, row in enumerate(rows, 1):
        content = []
        for c, text in enumerate(row, 1):
            if not text:
                continue
            ref = column(c) + str(r)
            if ref in {'B9', 'B10'}:
                content.append(f'<c r="{ref}" s="1"><v>{text}</v></c>')
            else:
                i = len(shared)
                if ref == 'E5':
                    a, b = text.split(' https://')
                    shared.append('<si><r><t>' + escape(a) + '</t></r><r><t xml:space="preserve"> https://' + escape(b) + '</t></r></si>')
                else:
                    shared.append('<si><t>' + escape(text) + '</t></si>')
                content.append(f'<c r="{ref}" t="s"><v>{i}</v></c>')
        sheet.append(f'<row r="{r}">' + ''.join(content) + '</row>')
    target = folder / 'relatives.xlsx'
    relns = 'http://schemas.openxmlformats.org/package/2006/relationships'
    office = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    with ZipFile(target, 'w', ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
        z.writestr('_rels/.rels', f'<Relationships xmlns="{relns}"><Relationship Id="rId1" Type="{office}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="{office}"><sheets><sheet name="Лист1" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', f'<Relationships xmlns="{relns}"><Relationship Id="rId1" Type="{office}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="{office}/styles" Target="styles.xml"/><Relationship Id="rId3" Type="{office}/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
        z.writestr('xl/sharedStrings.xml', f'<sst xmlns="{ns}">' + ''.join(shared) + '</sst>')
        z.writestr('xl/styles.xml', f'<styleSheet xmlns="{ns}"><numFmts count="1"><numFmt numFmtId="164" formatCode="d mmmm yyyy"/></numFmts><fonts count="1"><font/></fonts><fills count="1"><fill/></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="164" applyNumberFormat="1"/></cellXfs></styleSheet>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}" xmlns:r="{office}"><sheetData>' + ''.join(sheet) + '</sheetData><hyperlinks><hyperlink ref="E5" r:id="link1"/></hyperlinks></worksheet>')
        z.writestr('xl/worksheets/_rels/sheet1.xml.rels', f'<Relationships xmlns="{relns}"><Relationship Id="link1" Type="{office}/hyperlink" Target="https://example.org/record/12345" TargetMode="External"/></Relationships>')
    displays = {c['address'].split('!')[1]: c['text'] for c in cells(target.read_bytes(), '.xlsx')}
    for r, row in enumerate(rows, 1):
        for c, _ in enumerate(row, 1):
            row[c-1] = displays.get(column(c) + str(r), '')
    with (folder / 'relatives.csv').open('w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(rows)


if __name__ == '__main__':
    main()
