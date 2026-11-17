import type {Model} from './model';
export type Size='xl'|'l'|'m'|'c'|'dot'|'tiny'|'pill'|'kids'|'up'|'ring';
export type Node={id:string;key:string;x:number;y:number;w:number;h:number;size:Size;gen:number;status:string;branch:number;color:string;kin:boolean;center:boolean;count:number;other:string;label:string};
export type Link={key:string;d:string;gen:number;status:string;kind:'parent'|'union'|'child';color?:string};
export type Layout={nodes:Node[];links:Link[];width:number;height:number;box:{x0:number;x1:number;y0:number;y1:number};fogs:{x:number;y:number}[];couple:boolean;level:number;visible:Set<string>};
const MAX_LEVEL=9;
const curve=(x1:number,y1:number,x2:number,y2:number)=>`M${x1},${y1} C${x1},${(y1+y2)/2} ${x2},${(y1+y2)/2} ${x2},${y2}`;
type T={id:string;status:string;gen:number;kids:T[];w:number;x:number;child?:T};
/** Ancestor tree of `root`, `up` generations deep, never listing a person twice. */
function ancestors(m:Model,root:string,up:number,seen:Set<string>){
 const build=(id:string,gen:number,status:string):T=>{const t:T={id,status,gen,kids:[],w:1,x:0};if(gen<up)m.parents(id).slots.forEach(s=>{if(s&&!seen.has(s.id)){seen.add(s.id);const k=build(s.id,gen+1,m.connectionStatus(s));k.child=t;t.kids.push(k)}});t.w=t.kids.length?t.kids.reduce((a,k)=>a+k.w,0):1;return t};
 return build(root,0,'export');
}
// parents of the person get equal room (so they stay readable); further up, wide branches get more
function place(t:T,a:number,b:number){t.x=(a+b)/2;if(!t.kids.length)return;const weight=(k:T)=>t.gen===0?1:k.w+1;const total=t.kids.reduce((s,k)=>s+weight(k),0);let at=a;for(const k of t.kids){const share=(b-a)*weight(k)/total;place(k,at,at+share);at+=share}}
const flat=(t:T,out:T[]=[])=>{out.push(t);t.kids.forEach(k=>flat(k,out));return out};
/** How many generations can this person show on a stage of this width, and how many fit its height by default. */
export function levelRange(m:Model,center:string,W:number,H:number){
 let max=1,auto=1;const mate=m.spouses(center)[0];
 for(let L=1;L<=MAX_LEVEL;L++){
  const seen=new Set([center,mate].filter(Boolean) as string[]);
  const trees=[ancestors(m,center,L,seen),...(mate?[ancestors(m,mate,L,seen)]:[])];
  const rows=new Map<number,number>();trees.forEach(t=>flat(t).forEach(n=>rows.set(n.gen,(rows.get(n.gen)||0)+1)));
  const deepest=Math.max(...rows.keys());if(deepest<L&&L>1)break;
  const widest=Math.max(...[...rows].filter(([g])=>g>0).map(([,c])=>c),0);if(widest*10>W-24&&L>1)break;
  max=L;const cap=W<560?3:W<1000?4:5;if(L<=cap&&(layoutTree(m,center,W,L).height<=H/.82||L<=2))auto=L;
 }
 return {max,auto:Math.min(auto,max)};
}
/**
 * A window onto the tree. The person and partner sit side by side, ancestors rise above them and take the room they are
 * given (full cards, small cards, round avatars, dots), children hang below. `level` is how many generations go up.
 */
export function layoutTree(m:Model,center:string,W:number,level:number):Layout{
 const cardHeight=(id:string,w:number,base:number,large=false)=>{
  const textWidth=Math.max(30,w-28),font=large?16:13.5;
  return Math.max(m.info[id].connector?48:base,Math.ceil(m.info[id].treeName.length*font*.63/textWidth)*font*1.25+(m.info[id].connector?20:42))};
 const pad=12;const mate=m.spouses(center)[0];const couple=!!mate;const narrow=W<560;
 let leftId=center,rightId=mate||'';if(couple&&!m.husbands.has(center)&&m.husbands.has(mate)){leftId=mate;rightId=center}
 const seen=new Set([center,mate].filter(Boolean) as string[]);
 const roots=couple?[ancestors(m,leftId,level,seen),ancestors(m,rightId,level,seen)]:[ancestors(m,center,level,seen)];
 const halves=couple?[[pad,W/2],[W/2,W-pad]]:[[pad,W-pad]];
 roots.forEach((r,i)=>place(r,halves[i][0],halves[i][1]));
 const all=roots.flatMap(r=>flat(r));const byGen=new Map<number,T[]>();all.forEach(t=>(byGen.get(t.gen)||byGen.set(t.gen,[]).get(t.gen)!).push(t));
 const maxGen=Math.max(...byGen.keys());
 // size every ancestor by the room its neighbours leave it
 type S={t:T;size:Size;w:number;h:number;label:string};const sized=new Map<string,S>();
 for(const [g,row] of byGen){if(g===0)continue;row.sort((a,b)=>a.x-b.x);
  row.forEach((t,i)=>{const l=i?(t.x-row[i-1].x)/2:t.x-pad,r=i<row.length-1?(row[i+1].x-t.x)/2:W-pad-t.x;const aw=2*Math.min(l,r)*.94;const i2=m.info[t.id];
   let size:Size,w:number,h:number;
   if(aw>=150){size='l';w=Math.min(aw,230);h=76}
   else if(aw>=84){size='m';w=aw;h=78}
   else if(aw>=40){size='dot';w=h=Math.min(aw*.78,40)}
   else{size='tiny';w=h=Math.max(8,Math.min(aw*.8,16))}
   const sur=i2.providedName||i2.short.split(' ').filter(x=>/\p{L}/u.test(x)).slice(-1)[0]||'';
   if(size==='l'||size==='m')h=cardHeight(t.id,w,h);
   sized.set(t.id,{t,size,w,h:size==='dot'&&aw>=62?h+16:h,label:size==='dot'&&aw>=62?sur:''})})}
 const c0={w:couple?Math.min(W/2*.92,250):Math.min(W*.66,270),h:couple?(narrow?92:84):88};
 c0.h=Math.max(...[center,mate].filter(Boolean).map(id=>cardHeight(id,c0.w,c0.h,true)));
 // vertical rows, oldest on top
 const rowH=new Map<number,number>();rowH.set(0,c0.h);for(let g=1;g<=maxGen;g++)rowH.set(g,Math.max(...(byGen.get(g)||[]).map(t=>sized.get(t.id)!.h),0));
 const gap=(g:number)=>g<=1?50:rowH.get(g)!>=60&&rowH.get(g-1)!>=60?42:26;
 const topRow=byGen.get(maxGen)||[];const hasMoreTop=maxGen>0&&topRow.some(t=>m.hasParents(t.id));
 const rowY:number[]=[];let y=pad+(hasMoreTop?30:0);for(let g=maxGen;g>=0;g--){rowY[g]=y;y+=rowH.get(g)!+(g>0?gap(g):0)}
 const nodes:Node[]=[];const links:Link[]=[];const fogs:{x:number;y:number}[]=[];const visible=new Set<string>();
 const mk=(id:string,x:number,y:number,w:number,h:number,size:Size,gen:number,status:string,extra:Partial<Node>={})=>{if(size!=='ring'&&size!=='up')visible.add(id);const tone=m.tone(id);nodes.push({id,key:id+(['pill','kids','ring','up'].includes(size)?':'+size:''),x,y,w,h,size,gen,status,branch:m.branch.get(id)??-1,color:tone?.color||'',kin:!!tone?.kin,center:id===center,count:0,other:'',label:'',...extra})};
 const cx0=new Map<string,number>();
 // center row
 const cy=rowY[0];const xs=roots.map(r=>r.x);const ids=couple?[leftId,rightId]:[center];
 ids.forEach((id,i)=>{cx0.set(id,xs[i]);mk(id,xs[i]-c0.w/2,cy,c0.w,c0.h,'xl',0,'export')});
 const cxm=W/2;const cmid=cy+c0.h/2;
 if(couple){const status=m.connectionStatus(m.spouseConnection(center,mate));mk(center+':ring',cxm-13,cmid-13,26,26,'ring',0,status);links.push({key:'union',d:`M${xs[0]+c0.w/2},${cmid} L${xs[1]-c0.w/2},${cmid}`,gen:0,status,kind:'union'})}
 // ancestors
 for(const [g,row] of byGen){if(g===0)continue;for(const t of row){const s=sized.get(t.id)!;const yy=rowY[g]+(rowH.get(g)!-s.h)/2;
  mk(t.id,t.x-s.w/2,yy,s.w,s.h,s.size,g,t.status,{label:s.label});
  const ch=t.child!;const cs=ch.gen===0?{y:cy,h:c0.h,x:cx0.get(ch.id)!}:{y:rowY[ch.gen]+(rowH.get(ch.gen)!-sized.get(ch.id)!.h)/2,h:0,x:ch.x};
  links.push({key:ch.id+'>'+t.id,d:curve(cs.x,cs.y,t.x,yy+(s.size==='dot'?s.w:s.h)),gen:g,status:t.status,kind:'parent',color:m.tone(t.id)?.color});
  if(g===maxGen&&m.hasParents(t.id)){fogs.push({x:t.x,y:yy});const n=m.ancestorsCount(t.id);if(s.size!=='tiny')mk(t.id,t.x-18,yy-27,36,19,'up',g,'export',{count:n})}}}
 // other partners
 const extras=m.spouses(center).slice(couple?1:0).filter(x=>x!==mate);
 const cb=cy+c0.h;let originX=cxm,originY=couple?cmid+13:cb;
 const pw=(id:string)=>Math.max(84,Math.min(176,m.info[id].treeName.length*6.6+44));
 let px=cx0.get(center)!-8;
 extras.slice(0,3).forEach(id=>{const w=pw(id);mk(id,px,cb+6,w,44,'pill',0,m.connectionStatus(m.spouseConnection(center,id)));px+=w+6});
 // children
 const kids=m.children(center);
 if(kids.length){
  const avail=W-pad*2,gp=10,minW=narrow?104:130;const cols=Math.max(1,Math.min(kids.length,Math.floor((avail+gp)/(minW+gp))));const cw=Math.min(narrow?160:176,(avail-(cols-1)*gp)/cols);const ch=Math.max(...kids.map(id=>cardHeight(id,cw,80))),stride=ch+30;
  const top=cb+(extras.length?56:couple?44:50);
  kids.forEach((id,i)=>{const r=Math.floor(i/cols),c=i%cols;const inRow=Math.min(cols,kids.length-r*cols);const x=cxm-(inRow*cw+(inRow-1)*gp)/2+c*(cw+gp);const yy=top+r*stride;
   const slot=m.parents(id).slots.find(sl=>sl?.id===center);const other=extras.length?(m.parents(id).slots.map(sl=>sl?.id).find(pid=>pid&&pid!==center)||''):'';
   mk(id,x,yy,cw,ch,'c',-1,slot?m.connectionStatus(slot):'export',{other:other?(m.info[other].providedName||m.info[other].short.split(' ')[0]):''});
   links.push({key:center+'>'+id,d:curve(originX,originY,x+cw/2,yy),gen:1,status:slot?m.connectionStatus(slot):'export',kind:'child'});
   const n=m.children(id).length;if(n)mk(id,x+cw/2-24,yy+ch-5,48,20,'kids',-1,'export',{count:n})});
 }
 const x0=Math.min(...nodes.map(n=>n.x)),x1=Math.max(...nodes.map(n=>n.x+n.w)),y0=Math.min(...nodes.map(n=>n.y)),y1=Math.max(...nodes.map(n=>n.y+n.h));
 return {nodes,links,width:W,height:y1+pad,box:{x0,x1,y0,y1},fogs,couple,level,visible};
}
