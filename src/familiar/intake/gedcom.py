# START_MODULE_CONTRACT: MOD-INTAKE-GEDCOM
# PURPOSE: Decode a GEDCOM conservatively and account for every unrepresented tag.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - unsupported tags are counted and recent births without deaths are living [review: engine lead]
# - PHRASE retains literal wording beside its tag path and enumerated value without asserting a relationship [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
import re
from collections import Counter
from datetime import date


def parse(path, ident, years=110, as_of=None):
    if years < 1:
        raise ValueError("living years must be positive")
    today = date.fromisoformat(as_of) if as_of else date.today()
    roots, stack = [], []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"(\d+) (?:(@[^@]+@) )?([A-Za-z0-9_]+)(?: (.*))?", line)
        if not match:
            raise ValueError(f"invalid GEDCOM line {number}; UTF-8 GEDCOM required")
        level, xref, tag, value = match.groups()
        level = int(level)
        if level > len(stack):
            raise ValueError(f"invalid GEDCOM level at line {number}")
        node = {"tag": tag, "value": value or "", "xref": xref, "children": [], "used": False}
        stack = stack[:level]
        (stack[-1]["children"] if stack else roots).append(node)
        stack.append(node)

    def use(n):
        n["used"] = True
        return n["value"]

    def text(n):
        value = use(n)
        for child in n["children"]:
            if child["tag"] in ("CONT", "CONC"):
                value += ("\n" if child["tag"] == "CONT" else "") + text(child)
        return value

    def key(value):
        return value.strip("@")

    def phrases(node, trail=()):
        # A phrase can qualify an unsupported role as well as a known event.
        # Preserve its context as an attributed note, never as inferred kinship.
        trail = (*trail, node['tag'])
        for child in node['children']:
            if child['tag'] == 'PHRASE':
                yield {'text': 'GEDCOM ' + '.'.join(trail) +
                       (' ' + node['value'] if node['value'] else '') + ': ' + text(child),
                       'provenance': [ident]}
            else:
                yield from phrases(child, trail)

    sources = {n['xref']: n for n in roots if n['tag'] == 'SOUR' and n['xref']}

    def citations(node):
        result = []
        for child in node['children']:
            if child['tag'] != 'SOUR':
                continue
            parts = [text(child)]
            source = sources.get(child['value'])
            if source:
                use(source)
                parts.extend(text(f) for f in source['children'] if f['tag'] in {'TITL', 'AUTH', 'PUBL', 'TEXT', 'NOTE'})
            parts.extend(f['tag'] + ': ' + text(f) for f in child['children'] if f['tag'] in {'PAGE', 'QUAY', 'TEXT', 'NOTE'})
            result.append('; '.join(parts))
        return result

    data = {
        "id": ident,
        "people": [],
        "families": [],
        "losses": {},
        "living_rule": f"No death and latest stated birth year > {today.year - years}; no birth defaults living for privacy. As of {today.isoformat()}, threshold {years} years.",
    }
    tags = {
        "BIRT": "birth",
        "DEAT": "death",
        "BAPM": "baptism",
        "BURI": "burial",
        "RESI": "residence",
        "OCCU": "occupation",
        "MARR": "marriage",
        "DIV": "divorce",
        "EVEN": "event",
    }
    for node in roots:
        if node["tag"] in ("HEAD", "TRLR"):
            use(node)  # envelope children remain accounted for as losses
            continue
        if node["tag"] not in ("INDI", "FAM"):
            continue
        use(node)
        if not node["xref"]:
            raise ValueError("INDI and FAM require xrefs")
        row = {"id": key(node["xref"]), "events": [], "provenance": [ident]}
        if node["tag"] == "INDI":
            row.update(names=[], notes=[], sex="u")
        else:
            row.update(children=[])
        if literal_phrases := list(phrases(node)):
            row.setdefault('notes', []).extend(literal_phrases)
        for child in node["children"]:
            tag = child["tag"]
            if tag == "NAME" and node["tag"] == "INDI":
                value = use(child).split("/")
                row["names"].append(
                    {
                        "given": value[0].strip() or "[unknown]",
                        "surname": value[1].strip()
                        if len(value) > 1 and value[1].strip()
                        else "[unknown]",
                        "type": "as-written",
                        "source_text": citations(child) + citations(node),
                        "provenance": [ident],
                    }
                )
                for field in child['children']:
                    if field['tag'] == '_MARNM':
                        row['names'].append(dict(row['names'][-1], surname=text(field), type='married'))
            elif tag == '_MARNM' and node['tag'] == 'INDI':
                given = row['names'][0]['given'] if row['names'] else '[unknown]'
                row['names'].append({'given': given, 'surname': text(child), 'type': 'married', 'provenance': [ident]})
            elif tag == "SEX" and node["tag"] == "INDI":
                row["sex"] = use(child).lower()
            elif tag == "NOTE" and node["tag"] == "INDI":
                row["notes"].append({"text": text(child), "provenance": [ident]})
            elif tag in ("HUSB", "WIFE", "CHIL") and node["tag"] == "FAM":
                value = key(use(child))
                if tag == "CHIL":
                    row["children"].append(value)
                else:
                    row["husband" if tag == "HUSB" else "wife"] = value
            elif tag in tags:
                event = {
                    "type": tags[tag],
                    "tag": tag,
                    "date": "unknown",
                    "value": use(child),
                    "provenance": [ident],
                }
                for field in child["children"]:
                    if field["tag"] in ("DATE", "PLAC", "NOTE"):
                        event[{"DATE": "date", "PLAC": "place", "NOTE": "note"}[field["tag"]]] = (
                            text(field)
                        )
                    elif field['tag'] == 'TYPE' and tag == 'EVEN':
                        event['value'] = text(field)
                event['source_text'] = citations(child) + citations(node)
                row["events"].append(event)
        row['source_text'] = citations(node)
        if node["tag"] == "INDI":
            birth = next((e["date"] for e in row["events"] if e["type"] == "birth"), "")
            birth_years = re.findall(r"\b\d{4}\b", birth)
            row["living"] = not any(e["type"] == "death" for e in row["events"]) and (
                not birth_years or max(map(int, birth_years)) > today.year - years
            )
            data["people"].append(row)
        else:
            data["families"].append(row)
    losses = Counter()

    def count(nodes):
        for node in nodes:
            if not node["used"]:
                losses[node["tag"]] += 1
            count(node["children"])

    count(roots)
    data["losses"] = dict(sorted(losses.items()))
    return data
