# START_MODULE_CONTRACT: MOD-DEMO-RUSSIAN-REPLAY
# PURPOSE: Replay the saved invented Russian family's first week and preserve the host texts and privacy controls.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - this replay writes only its explicitly selected new fictional root and report directory [review: engine lead]
# - inputs are invented and original pilot files are never opened [review: cold reviewer]
# CHANGES_WITH:
# - demo-russian/README.md (replay instructions and fictional input provenance)
# :END_MODULE_CONTRACT
import argparse
import base64
import contextlib
import io
import json
import re
import shutil
from pathlib import Path

from familiar.cli import main
from familiar.instance.gate import publication
from familiar.instance.model import Instance
from familiar.tree.builder import build


def replay(root, report):
    inputs = Path(__file__).resolve().parents[1] / 'demo-russian/inputs'
    if root.exists() or report.exists():
        raise ValueError('Choose new family and report directories; replay never replaces them')
    report.mkdir(parents=True)
    log = []

    def command(*args):
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(list(args))
        log.append({'command': ['familiar', *args], 'exit': code, 'stdout': output.getvalue(), 'stderr': error.getvalue()})
        if code:
            raise ValueError(error.getvalue() or output.getvalue())
        return output.getvalue()

    def cli(*args):
        return command('--root', str(root), *args)

    def put(relative, value):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def read(name):
        return json.loads((inputs / name).read_text(encoding='utf-8'))

    command('instance', 'init', str(root), '--language', 'ru', '--address', 'informal',
            '--title', 'Семья Корнеевых-Шмидт (вымышленная)')
    config = root / 'familiar.toml'
    config.write_text(config.read_text(encoding='utf-8').replace('languages = ["ru"]',
                      'languages = ["ru"]\nfictional = true'), encoding='utf-8')
    config.write_text(re.sub(r'(?m)^id = .*$', 'id = "russian-invented-week"',
                            config.read_text(encoding='utf-8')), encoding='utf-8')
    # A tiny blank image is openly a placeholder, never a facsimile of a record.
    image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=')
    original = report / 'fictional-placeholder.png'
    original.write_bytes(image)
    cli('intake', 'memory', str(inputs / 'day1-memory.toml'))
    cli('intake', 'paper', str(inputs / 'day1-paper-svidetelstvo.toml'), '--original', str(original))
    (report / 'day1-summary.txt').write_text(cli('family', 'summary'), encoding='utf-8')
    candidates = json.loads(cli('intake', 'gedcom', str(inputs / 'day2-export-myheritage.ged'), '--id', 'export-wagner-2026-11'))
    before = build(Instance(root), view='working')
    decisions = read('day2-identity-decisions.json')
    put('tree/identity-decisions.json', decisions)
    merged = build(Instance(root), view='working')
    put('tree/identity-decisions.json', {})
    assert build(Instance(root), view='working') == before
    put('tree/identity-decisions.json', decisions)
    for name in sorted(inputs.glob('day3-*.json')):
        category, filename = name.name[5:].split('-', 1)
        folder = {'version': 'versions', 'case': 'cases', 'request': 'family/questions'}[category]
        put(f'{folder}/{filename}', read(name.name))
    (report / 'day3-letter.txt').write_text(cli('family', 'requests', 'nina-spravka', '--text'), encoding='utf-8')
    request = json.loads((root / 'family/questions/nina-spravka.json').read_text(encoding='utf-8'))
    request.update(state='asked', asked_at='2026-11-12')
    put('family/questions/nina-spravka.json', request)
    (report / 'day4-next.txt').write_text(cli('family', 'next'), encoding='utf-8')
    cli('intake', 'paper', str(inputs / 'day5-paper-spravka.toml'), '--original', str(original))
    put('family/answers/nina-spravka-answer.json', read('day5-answer-nina.json'))
    request.update(state='answered', answer='nina-spravka-answer')
    put('family/questions/nina-spravka.json', request)
    put('versions/emma-origin.json', read('day5-version-emma-origin.json'))
    put('cases/emma-origin.json', read('day5-case-emma-origin.json'))
    cli('feed', 'new', 'volga-1941')
    meta = read('day6-feed.json')
    meta['persons']['LYUDMILA'] = 'irina-2026-11-12-lyudmila'
    # The lead also contains the living daughter's birth place, despite not naming her.
    sentences = re.split(r'(?<=\.) ', meta['lead'], maxsplit=1)
    meta['prose'] = {key: [{'people': ['EMMA'], 'text': meta[key]}] for key in ('title', 'period', 'line')}
    meta['prose']['lead'] = [{'people': ['EMMA'], 'text': sentences[0]},
                             {'people': ['LYUDMILA'], 'text': sentences[1]}]
    put('feeds/volga-1941/feed.json', meta)
    chapters = read('day6-chapters-with-document.json')
    # The same prose, divided by subjects; nothing is rewritten to assert a death.
    chapter = chapters[0]
    blocks = chapter['text'].split('\n\n')
    parent_sentences = re.split(r'(?<=\.) ', blocks[1])
    chapter['prose'] = {'title': [{'people': ['EMMA'], 'text': chapter['title']}],
                        'text': [{'people': ids, 'text': text} for ids, text in zip(
                            [['EMMA'], ['GOTTLIEB'], ['MARIA'], ['FRIEDRICH'], ['EMMA']],
                            [blocks[0], *parent_sentences, blocks[2]])],
                        'more': [{'people': ['FRIEDRICH'] if 'брат' in text else ['EMMA'], 'text': text}
                                 for text in chapter['more'].split('\n')],
                        'ask': [{'people': ['EMMA'], 'text': chapter['ask']}]}
    put('feeds/volga-1941/chapters.json', chapters)
    docs = read('day6-documents.json')
    fields = ['Место рождения', 'Куда выселена']
    record_path = root / 'records/spravka-emma-1994.json'
    record = json.loads(record_path.read_text(encoding='utf-8'))
    record['field_subjects'] = {key: ['irina-2026-11-12-emma'] for key in fields}
    put('records/spravka-emma-1994.json', record)
    document = docs['spravka-emma-1994']
    document['excerpt'] = fields
    for snippet in document['snippets']:
        snippet['read'] = record['fields'][snippet['field']]
    put('feeds/volga-1941/documents.json', docs)
    cli('instance', 'check', '--json')
    cli('feed', 'check', '--all', '--json')
    (report / 'day6-page.txt').write_text(cli('feed', 'pages', 'volga-1941', '--text'), encoding='utf-8')
    reader = publication(Instance(root), 'feeds').data()
    reader_text = reader[0]['chapters'][0]['text']['ru']
    assert 'Эмме Шмидт было десять лет' in reader_text and 'Младшему брату было шесть лет' not in reader_text
    assert 'Отец, Готлиб, собирал' in reader_text and 'Мать, Мария, зашивала' in reader_text
    assert 'скрыта' in reader_text
    assert 'Её дочь родится' not in reader[0]['lead']['ru']
    # Full record still refuses even if the author clears the subjects list.
    del document['excerpt']
    put('feeds/volga-1941/documents.json', docs)
    try:
        publication(Instance(root), 'feeds')
    except ValueError as exc:
        assert 'Living person document' in str(exc) or 'living person document' in str(exc)
        full_refused = str(exc)
    else:
        raise AssertionError('Full living document escaped')
    document['excerpt'] = fields
    put('feeds/volga-1941/documents.json', docs)
    cli('feed', 'review', 'volga-1941', '--out', str(report / 'reading'))
    # A replay cannot certify that an independent person read these bytes.
    # Keep a preview generation; independent confirmation is not simulated here.
    cli('feed', 'build', 'volga-1941', '--out', str(report / 'reader-feeds'))
    put_report = {'fictional': True, 'before_merge': len(before['people']), 'after_merge': len(merged['people']),
                  'merge_undo_exact': True, 'candidates': candidates['candidates'], 'full_document_refused': full_refused,
                  'life': {pid: p['life_assessment'] for pid, p in merged['people'].items()},
                  'reader': reader, 'commands': log}
    (report / 'replay.json').write_text(json.dumps(put_report, ensure_ascii=False, indent=2), encoding='utf-8')
    original.unlink()
    shutil.rmtree(report / 'reading')
    return put_report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.out.resolve(), args.report.resolve())
    print(json.dumps({key: result[key] for key in ('before_merge', 'after_merge', 'merge_undo_exact')}, ensure_ascii=False))
