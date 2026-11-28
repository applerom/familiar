"""The placed beats of an authored chapter."""
import copy

from familiar.reader.experiences import chapter_game


FRAME_KINDS = {'period-picture', 'drawing', 'map', 'family-photograph'}
PLAY_CATALOGS = {'game': 'games', 'spots': 'spots', 'pano': 'panos'}


def placed_play(spec, chapter, play):
    if not isinstance(spec, dict):
        return None
    kind, key = spec.get('kind'), spec.get('key')
    if not isinstance(kind, str) or kind not in PLAY_CATALOGS or not isinstance(key, str):
        return None
    item = play.get(PLAY_CATALOGS[kind], {}).get(key)
    if not item:
        return None
    if kind == 'game':
        return {'kind': kind, 'key': key, 'game': chapter_game(chapter, item)}
    # Follow the chapter's attributed image, never a bare path from play.json.
    for original in [chapter.get('picture'), *chapter.get('figures', [])]:
        if not original:
            continue
        picture = copy.deepcopy(original)
        for image in (picture, picture.get('ours') or {}):
            if image.get('asset') == key:
                image[kind] = copy.deepcopy(item)
                return {'kind': kind, 'key': key, 'picture': picture}
    return None


def frame(spec):
    if not isinstance(spec, dict):
        return None
    ratio, kind, says = spec.get('ratio'), spec.get('kind'), spec.get('says')
    if (isinstance(ratio, list) and len(ratio) == 2
            and all(type(n) is int and n > 0 for n in ratio)
            and isinstance(kind, str) and kind in FRAME_KINDS
            and isinstance(says, str) and says.strip() and len(says.splitlines()) == 1):
        return {'ratio': ratio, 'kind': kind, 'says': says.strip()}
    return None


def drafts(feeds):
    return [f"{feed['id']}/{chapter['id']}" for feed in feeds for chapter in feed['chapters']
            if any('placeholder' in row for row in chapter.get('flow', []))]


def require_finished(feeds):
    if pending := drafts(feeds):
        raise ValueError('Draft frames are home-only. Replace or remove flow placeholders before releasing: '
                         + ', '.join(pending))
