import {useCallback,useEffect,useRef,useState,type RefObject} from 'react';
export type T={k:number;x:number;y:number};
type Opts={min:number;max:number;margin?:number;content:RefObject<{w:number;h:number}>;horizontalWheel?:boolean;onStep?:(direction:number,at:{x:number;y:number})=>void};
/**
 * Mouse drag, wheel, touch drag and two-finger pinch for one stage. Clicks that end a drag are swallowed.
 * `focal` is where the current wheel or pinch gesture points (null while dragging). A transform set from outside
 * in the middle of a gesture is taken as the new starting point at once, so the gesture goes on from it.
 */
export function useZoomPan(stage:RefObject<HTMLElement|null>,{min,max,margin=70,content,horizontalWheel=false,onStep}:Opts){
 const step=useRef(onStep);step.current=onStep;
 const [t,setState]=useState<T>({k:1,x:0,y:0});const [moving,setMoving]=useState(false);const tRef=useRef(t);tRef.current=t;const focal=useRef<{x:number;y:number}|null>(null);const placed=useRef<T|null>(null);
 const apply=useCallback((n:T)=>{tRef.current=n;setState(n)},[]);
 const setT=useCallback((n:T)=>{placed.current=n;apply(n)},[apply]);
 const clamp=useCallback((n:T):T=>{const el=stage.current,c=content.current;if(!el||!c)return n;const k=Math.min(max,Math.max(min,n.k));const sw=el.clientWidth,sh=el.clientHeight;const w=c.w*k,h=c.h*k;
  return {k,x:Math.min(sw-margin,Math.max(margin-w,n.x)),y:Math.min(sh-margin,Math.max(margin-h,n.y))}},[stage,content,min,max,margin]);
 const zoomAt=useCallback((factor:number,px:number,py:number,from:T=tRef.current)=>{const k=Math.min(max,Math.max(min,from.k*factor));const r=k/from.k;apply(clamp({k,x:px-(px-from.x)*r,y:py-(py-from.y)*r}))},[clamp,min,max,apply]);
 const zoomBy=useCallback((factor:number)=>{const el=stage.current;if(el)zoomAt(factor,el.clientWidth/2,el.clientHeight/2)},[stage,zoomAt]);
 useEffect(()=>{
  const el=stage.current;if(!el)return;
  const pts=new Map<number,{x:number;y:number}>();let start:{x:number;y:number;t:T}|null=null;let pinch:{d:number;t:T;mx:number;my:number}|null=null;let dragged=false;let swallow=false;let wheelTimer:ReturnType<typeof setTimeout>|undefined;let turned=0,locked=0;
  const rel=(e:{clientX:number;clientY:number})=>{const r=el.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top}};
  const dist=()=>{const [a,b]=[...pts.values()];return {d:Math.hypot(a.x-b.x,a.y-b.y),mx:(a.x+b.x)/2,my:(a.y+b.y)/2}};
  const down=(e:PointerEvent)=>{if((e.target as Element).closest('[data-pan-ignore]')||e.pointerType==='mouse'&&e.button!==0)return;if(e.isPrimary){pts.clear();pinch=null}pts.set(e.pointerId,rel(e));if(pts.size===1){start={...rel(e),t:{...tRef.current}};dragged=false;focal.current=null}else if(pts.size===2){const {d,mx,my}=dist();pinch={d,t:{...tRef.current},mx,my};placed.current=null;focal.current={x:mx,y:my};dragged=true;setMoving(true);
    // the picture may be redrawn under the fingers: the stage itself keeps both pointers
    for(const pid of pts.keys())try{el.setPointerCapture(pid)}catch{}}};
  const move=(e:PointerEvent)=>{if(!pts.has(e.pointerId))return;pts.set(e.pointerId,rel(e));
   if(pts.size>=2&&pinch){const {d,mx,my}=dist();if(placed.current){pinch={d,t:placed.current,mx,my};placed.current=null}focal.current={x:mx,y:my};const k=Math.min(max,Math.max(min,pinch.t.k*d/pinch.d));const r=k/pinch.t.k;apply(clamp({k,x:mx-(pinch.mx-pinch.t.x)*r,y:my-(pinch.my-pinch.t.y)*r}));return}
   if(!start)return;const p=rel(e);const dx=p.x-start.x,dy=p.y-start.y;
   if(!dragged&&Math.hypot(dx,dy)>7){dragged=true;setMoving(true);try{el.setPointerCapture(e.pointerId)}catch{}}
   if(dragged)apply(clamp({k:start.t.k,x:start.t.x+dx,y:start.t.y+dy}))};
  const up=(e:PointerEvent)=>{if(!pts.delete(e.pointerId))return;
   if(pts.size===1&&pinch){const [p]=[...pts.values()];start={...p,t:{...tRef.current}};pinch=null;return}
   if(pts.size===0){if(dragged){swallow=true;setTimeout(()=>{swallow=false},80)}start=null;pinch=null;dragged=false;setMoving(false)}};
  const click=(e:MouseEvent)=>{if(swallow){e.stopPropagation();e.preventDefault()}};
  const wheel=(e:WheelEvent)=>{
   e.preventDefault();const p=rel(e);const units=e.deltaMode===1?16:e.deltaMode===2?el.clientHeight:1;
   const sideways=horizontalWheel&&!e.ctrlKey&&(e.shiftKey||Math.abs(e.deltaX)>Math.abs(e.deltaY));
   // With a step handler the plain wheel never scales pixels: one turn of the wheel is one step. A long spin
   // or a trackpad swipe stays one step until the wheel rests.
   if(step.current&&!sideways&&!e.ctrlKey){const now=performance.now();if(now<locked){turned=0;locked=Math.max(locked,now+160);return}
    turned+=e.deltaY*units;if(Math.abs(turned)>=40){step.current(turned>0?1:-1,p);turned=0;locked=now+260}return}
   setMoving(true);clearTimeout(wheelTimer);wheelTimer=setTimeout(()=>setMoving(false),140);
   if(sideways){
    focal.current=null;apply(clamp({...tRef.current,x:tRef.current.x-(e.deltaX||e.deltaY)*units}));
   }else{focal.current=p;zoomAt(Math.exp(-e.deltaY*units*(e.ctrlKey?.01:.0016)),p.x,p.y)}
  };
  el.addEventListener('pointerdown',down);el.addEventListener('pointermove',move);el.addEventListener('pointerup',up);el.addEventListener('pointercancel',up);el.addEventListener('click',click,true);el.addEventListener('wheel',wheel,{passive:false});
  return()=>{el.removeEventListener('pointerdown',down);el.removeEventListener('pointermove',move);el.removeEventListener('pointerup',up);el.removeEventListener('pointercancel',up);el.removeEventListener('click',click,true);el.removeEventListener('wheel',wheel);clearTimeout(wheelTimer)};
 },[stage,clamp,zoomAt,min,max,apply,horizontalWheel]);
 return {t,setT,moving,zoomBy,zoomAt,focal};
}
