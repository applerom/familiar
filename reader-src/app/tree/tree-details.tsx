import {useLayoutEffect,useRef,useState,type CSSProperties} from 'react';
import {plural} from '../i18n';
import type {Layout,Tile} from './layout';
import {humanText,lifeLabel,type Model,type Row} from './model';

export type OpenDeck = {tile: Tile; button: HTMLButtonElement; pinned: boolean};

export function SiblingDeck({deck,model,labels,onEnter,onLeave,onClose,go}: {
  deck: OpenDeck; model: Model; labels: Row; onEnter: () => void; onLeave: () => void;
  onClose: () => void; go: (id: string) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const popover = box.current!;
    const canvas = popover.parentElement!.getBoundingClientRect();
    const badge = deck.button.getBoundingClientRect();
    const tile = deck.button.parentElement!.getBoundingClientRect();
    const width = popover.offsetWidth, height = popover.offsetHeight;
    const x = badge.left + badge.width / 2 - canvas.left - width / 2;
    const y = tile.bottom - canvas.top + 6;
    popover.style.left = `${Math.max(8, Math.min(canvas.width - width - 8, x))}px`;
    popover.style.top = `${y + height <= canvas.height - 62 ? y : Math.max(6, badge.top - canvas.top - height - 4)}px`;
    if (deck.pinned) popover.querySelector<HTMLButtonElement>('.deck-person:not([aria-current])')?.focus({preventScroll: true});
  }, [deck]);
  return <div ref={box} id="tree-sibling-deck" className="sibling-deck" role="region" aria-label={labels.treeDeck}
    onPointerEnter={onEnter} onPointerLeave={onLeave}>
    <header><strong>{labels.treeDeck}</strong>
      {deck.pinned && <button className="deck-close" aria-label={labels.close} onClick={onClose}>×</button>}
    </header>
    <div className="deck-people">
      {deck.tile.siblings.map(id => {
        const person = model.info[id];
        const year = person.birth !== undefined ? humanText(person.birthText, labels.languageCode) : '';
        const style = {'--b': model.tone(id)?.color} as CSSProperties;
        return <button key={id} className="deck-person" aria-current={id === deck.tile.id ? 'true' : undefined}
          disabled={id === deck.tile.id} style={style} title={person.fullName}
          aria-label={[person.fullName,year].filter(Boolean).join(' ')} onClick={() => go(id)}>
          <strong>{person.givenName || person.treeName}</strong>{year && <small>{year}</small>}
        </button>;
      })}
    </div>
  </div>;
}

/** List each hidden person once, under their parent family or, when unknown, their partner. */
function hiddenFamilies(ids: string[], model: Model, labels: Row) {
  const groups = new Map<string, {title: string; ids: string[]}>();
  for (const id of ids) {
    const parents = model.parents(id).slots.flatMap(p => p ? [p.id] : []);
    const mate = model.spouses(id).find(pid => !model.info[pid].placeholder);
    const family = parents.length ? parents : mate ? [id,mate] : [];
    const key = JSON.stringify([!!parents.length, ...family.slice().sort()]);
    if (!groups.has(key)) groups.set(key, {title: family.map(pid => model.info[pid].short).join(' · ') || labels.treeOther, ids: []});
    groups.get(key)!.ids.push(id);
  }
  return [...groups].sort((a,b) => a[1].title.localeCompare(b[1].title, labels.languageCode));
}

export function TreeCount({layout,model,labels,go,overflow}: {
  layout: Layout | null; model: Model; labels: Row; go: (id: string) => void; overflow: boolean;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [scope,setScope] = useState<'collateral'|'beyond'|null>(null);
  const open = (next: 'collateral'|'beyond') => {
    setScope(next);
    dialog.current?.showModal();
  };
  const visible = layout?.visible.size ?? 0;
  const collateral = layout?.collateral.length ?? 0, beyond = layout?.beyond.length ?? 0;
  const total = visible + collateral + beyond;
  const people = `${total} ${plural(total,labels.personsForms,labels.languageCode)}`;
  const familyGroups = layout && scope ? hiddenFamilies(layout[scope],model,labels) : [];
  return <>
    <div className="tree-count">
      {layout && <div>
        {labels.treeCount.replace('{n}',people)}{' '}
        <span title={labels.treeVisibleHint}>{labels.treeVisible.replace('{n}',visible)}</span>
        {collateral > 0 && <> · <button aria-haspopup="dialog" onClick={() => open('collateral')}>{labels.treeCollateral.replace('{n}',collateral)}</button></>}
        {beyond > 0 && <> · <button aria-haspopup="dialog" onClick={() => open('beyond')}>{labels.treeBeyond.replace('{n}',beyond)}</button></>}
      </div>}
      {overflow && <small className="tree-pan-hint">↔ {labels.treePan}</small>}
    </div>
    <dialog ref={dialog} className="tree-people-dialog" aria-labelledby="hidden-people-heading" onClose={() => setScope(null)}
      onClick={event => { if (event.target === event.currentTarget) dialog.current?.close(); }}>
      <header>
        <h2 id="hidden-people-heading">{scope === 'beyond' ? labels.treeBeyondTitle : labels.treeCollateralTitle}</h2>
        <button aria-label={labels.close} onClick={() => dialog.current?.close()}>×</button>
      </header>
      <div className="tree-people-groups">
        {familyGroups.map(([key,group]) => <section key={key}>
          <h3>{group.title}</h3>
          <ul>{group.ids.sort(model.bySeniority).map(id => {
            const person = model.info[id];
            const life = lifeLabel(person,labels,labels.languageCode);
            return <li key={id}><button onClick={() => { dialog.current?.close(); go(id); }}>
              <strong>{person.treeName}</strong>{life && <small>{life}</small>}
            </button></li>;
          })}</ul>
        </section>)}
      </div>
    </dialog>
  </>;
}
