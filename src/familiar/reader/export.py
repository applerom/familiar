# START_MODULE_CONTRACT: MOD-READER-EXPORT
# PURPOSE: Deliver reproducible public or explicitly local host-private reader bundles into empty destinations.
# PRD_REF: docs/PRD.md#FORMS
# INVARIANTS:
# - no reader boundary substitutes a narrower family verdict [review: engine lead]
# - export confines all writes to an empty output directory [review: engine lead]
# - a rebuilt bundle has identical graph order and asset bytes [review: engine lead]
# - revoked inputs and changed delivered bytes invalidate consumption [review: engine lead]
# - drafts and unauthorized external links cannot reach the reader [review: engine lead]
# CHANGES_WITH:
# - MOD-FAMILY-GATE (every build and consumption boundary calls require)
# - MOD-FEED-SERVICE (named publication dependencies and stages)
# - docs/reader-export.md
# :END_MODULE_CONTRACT
import json
import re
from urllib.parse import urlsplit

VERSION = 1


def encode(value):
    # Preserve insertion order: layout, gallery and feed ordering are observable.
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


def external_links(value, allowed):
    """Research citations are text; active external links require a declared kind."""
    domains = {'map': {'openstreetmap.org', 'www.openstreetmap.org'},
               'video': {'youtube.com', 'www.youtube.com', 'youtu.be'}}
    def permitted(url, key):
        try:
            parsed = urlsplit(url)
            return (key in {'url', 'href'} and parsed.scheme == 'https' and not parsed.username and not parsed.password
                    and parsed.port in (None, 443) and any(parsed.hostname in domains.get(kind, set()) for kind in allowed))
        except ValueError:
            return False
    def walk(node, key=''):
        if isinstance(node, dict):
            return {k: walk(v, k) for k, v in node.items() if not (
                isinstance(v, str) and re.match(r'^(?:https?:)?//', v, re.IGNORECASE) and not permitted(v, k))}
        if isinstance(node, list):
            return [walk(child, key) for child in node]
        if isinstance(node, str):
            if re.match(r'^(?:https?:)?//', node, re.IGNORECASE) and permitted(node, key):
                return node
            if key in {'url', 'href', 'link', 'asset', 'full', 'orig', 'cover'} and re.match(r'(?:javascript|data|file|ftp|mailto):', node, re.IGNORECASE):
                raise ValueError('active non-web URI in reader data')
            return re.sub(r'(?:https?:)?//[^\s<>"\')\]]+', '[reference retained in research]', node, flags=re.IGNORECASE)
        return node
    return walk(value)


def output_path(instance, out):
    from familiar.instance.writer import _output_root
    out = _output_root(instance, out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError('output must be an empty directory')
    return out


from familiar.instance.gate import boundary


@boundary('output')
def export(instance, out=None, *, host_private=False):
    from familiar.instance.gate import publication
    from familiar.instance.writer import publish
    if host_private and out is None:
        raise ValueError('host-private reader requires a separate explicit --output directory')
    out = output_path(instance, out if out is not None else instance.path('export'))
    result = publication(instance, 'reader-private' if host_private else 'reader')
    if host_private:
        from familiar.instance.writer import save_private_reader
        save_private_reader(instance, out, result)
    else:
        publish(instance, out, result)
    return result.data()


@boundary('consume')
def verify(instance, out=None):
    from familiar.instance.writer import generation_status, read_generation
    out = out if out is not None else instance.path('export')
    files = read_generation(instance, out)
    return json.loads(files['bundle.json']) | generation_status(instance, out)
