# START_MODULE_CONTRACT: MOD-READER-EXPERIENCES
# PURPOSE: Carry declared family atlases and interactive chapter media into the checked reader.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - public routes contain only visible stops and attributed deceased participants [review: engine lead]
# - games cannot restore a document or image removed from their enclosing chapter [review: engine lead]
# - interactive data never executes family-supplied code [review: engine lead]
# CHANGES_WITH:
# - MOD-PUBLICATION (typed atlas, game and panorama fields)
# - MOD-INSTANCE-MODEL (world_map input location)
# :END_MODULE_CONTRACT
import copy
import json
import re
from datetime import date


def play(instance, graph):
    for feed in graph['feeds']:
        path = instance.path('feeds') / feed['id'] / 'play.json'
        data = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
        for chapter in feed.get('chapters', []):
            for picture in [chapter.get('picture'), *chapter.get('figures', []),
                            *[e.get('picture') for e in chapter.get('extras', [])]]:
                for image in [picture, picture.get('ours')] if picture else []:
                    if not image:
                        continue
                    for source, target in [('spots', 'spots'), ('panos', 'pano')]:
                        if image.get('asset') in data.get(source, {}):
                            image[target] = copy.deepcopy(data[source][image['asset']])
            if game := data.get('games', {}).get(f"{feed['id']}/{chapter['id']}"):
                chapter['game'] = chapter_game(chapter, game)


def chapter_game(chapter, game):
    result = copy.deepcopy(game)
    _protect_route(chapter, result)
    return result


def _visible_route(route, images):
    if not isinstance(route, dict):
        return False
    asset = route.get('asset')
    points = route.get('points')
    if not isinstance(asset, str) or asset not in images:
        return False
    if not isinstance(points, list) or len(points) < 2:
        return False
    for point in points:
        if not isinstance(point, dict):
            return False
        for axis in ('x', 'y'):
            coordinate = point.get(axis)
            if type(coordinate) not in (int, float) or not 0 <= coordinate <= 100:
                return False
    return True


def _protect_route(chapter, game):
    if 'route' not in game:
        return
    pictures = [chapter.get('picture'), *chapter.get('figures', [])]
    images = {image['asset'] for picture in pictures if picture
              for image in (picture, picture.get('ours')) if image and image.get('asset')}
    if not _visible_route(game['route'], images):
        game.pop('route')


def protect_game_media(graph):
    """A game uses only the pictures and paper cut-outs its chapter can show."""
    for feed in graph.get('feeds', []):
        for chapter in feed.get('chapters', []):
            assets = {r.get('asset') for r in chapter.get('records', [])}
            assets.update(p.get('asset') for r in chapter.get('records', []) for p in r.get('parts', []))
            for placed in [chapter, *(beat.get('do', {}) for beat in chapter.get('flow', []))]:
                game = placed.get('game', {})
                truth = game.get('truth', {})
                if truth.get('record') not in assets:
                    truth.pop('record', None)
                _protect_route(chapter, game)


def world(instance, graph, *, host_private=False):
    path = instance.path('world_map')
    if not path.is_file():
        return
    from familiar.rules.cascade import Registry
    from familiar.rules.roles import method_root
    source = json.loads(path.read_text(encoding='utf-8'))
    if source.get('schema_version') != 1:
        raise ValueError('world_map.schema_version: expected 1')
    findings = []
    for collection in ('people', 'places', 'homes', 'paths'):
        seen = set()
        for index, row in enumerate(source[collection]):
            location = f'world_map.{collection}[{index}]'
            identifier = row.get('id')
            if not isinstance(identifier, str) or not identifier or identifier in seen:
                findings.append(location + '.id: expected unique nonempty string')
            seen.add(identifier)
            for field, limit in (('lat', 90), ('lon', 180)):
                if field in row and (type(row[field]) not in (int, float) or not -limit <= row[field] <= limit):
                    findings.append(location + f'.{field}: coordinate out of range')
            if collection in ('places', 'paths') and (type(row.get('weight')) not in (int, float) or not 0 <= row['weight'] <= 1):
                findings.append(location + '.weight: expected probability')
    if findings:
        raise ValueError('\n'.join(findings))
    cutoff = date.today().year - Registry(method_root() / 'rules', instance).resolve_setting('privacy.living_years').value
    aliases = graph.get('identityAliases', {})
    people, hidden, errors = {}, set(), []
    for row in source['people']:
        pid = aliases.get(row.get('person_id'), row.get('person_id'))
        if pid and pid not in graph['people']:
            errors.append(f"world_map.people.{row['id']}.person_id: unknown {pid}")
        years = [int(y) for y in re.findall(r'\b(?:1\d{3}|20\d{2})\b', str(row.get('birth', '')))]
        dead = (graph['people'].get(pid, {}).get('life_assessment', {}).get('status') == 'dead' if pid else
                row.get('card_status') == 'namesake' and (bool(row.get('death')) or bool(years and max(years) < cutoff)))
        private = row.get('privacy') == 'living-possible' or not dead
        if private and not host_private:
            hidden.add(row['id'])
        safe = {k: copy.deepcopy(row[k]) for k in ('id', 'name', 'kin', 'card_status') if k in row}
        if pid and (host_private or not private):
            safe['person_id'] = pid
        people[row['id']] = safe
    places = []
    all_stops = {p['id'] for p in source['places']} | {h['id'] for h in source['homes']}
    for row in source['places']:
        if set(row['people']) - people.keys():
            errors.append(f"world_map.places.{row['id']}.people: unknown participant")
        visible = [p for p in row['people'] if p not in hidden]
        if not visible:
            continue
        safe = {k: copy.deepcopy(row[k]) for k in ('id', 'place', 'lat', 'lon', 'years', 'interest', 'group', 'km_from_home', 'regional', 'evidence', 'story', 'chapter') if k in row}
        safe.update(people=visible, uncertain=row['weight'] < .8)
        if len(visible) != len(row['people']):
            for key in ('years', 'story', 'chapter', 'interest', 'evidence'):
                safe.pop(key, None)
        if (chapter := safe.get('chapter')) and not any(f['id'] == chapter['feed'] and any(c['id'] == chapter['id'] for c in f['chapters']) for f in graph['feeds']):
            errors.append(f"world_map.places.{row['id']}.chapter: unknown chapter")
        places.append(safe)
    valid = {p['id'] for p in places} | {h['id'] for h in source['homes']}
    routes = []
    for row in source['paths']:
        if row['person'] not in people or set(row['stops']) - all_stops:
            errors.append(f"world_map.paths.{row['id']}: unknown person or stop")
        stops = [s for s in row['stops'] if s in valid]
        if row['person'] in hidden or len(stops) < 2:
            continue
        routes.append({**{k: copy.deepcopy(row[k]) for k in ('id', 'person', 'years', 'group')},
                       'stops': stops, 'uncertain': row['weight'] < .8 or any(p['uncertain'] for p in places if p['id'] in stops)})
    if errors:
        raise ValueError('\n'.join(errors))
    used_people = {p for place in places for p in place['people']}
    used_stops = {s for route in routes for s in route['stops']}
    graph['worldMap'] = {'schema_version': 1, 'people': {p: people[p] for p in people if p in used_people},
                         'places': places, 'paths': routes, 'unlocated': [],
                         'homes': [h for h in source['homes'] if h['group'] == 'family' or h['id'] in used_stops]}
