
(function(){"use strict";
/* Motion of the report pages, only where it helps to read the results (window.TSMOTION):
   - stage: a figure's marks move from a start that shows what the value means (an interval opens from its estimate,
     a stacked bar builds up outcome by outcome, a dumbbell moves from before to after) to the drawn values;
   - emphasis: pointing at a status in a legend dims the marks and tags of every other status.
   No motion under prefers-reduced-motion, with data-still on <html> (the full report: nothing moves on scroll) or without IntersectionObserver. Every transition ends on the attributes the
   figure was drawn with, so a saved SVG or a printed page is the same as without motion (finish(), beforeprint).
   waiting(): the elements whose staged marks still wait at their start, to be seen or for the short lead. */
var mq=window.matchMedia?window.matchMedia("(prefers-reduced-motion: reduce)"):null;
var ok=!!(window.IntersectionObserver&&document.documentElement.animate&&!(mq&&mq.matches)&&!document.documentElement.hasAttribute("data-still"));
/* LEAD: a short pause after the figure comes into view, so the eye is on it when the data moves */
var EASE="cubic-bezier(.2,.7,.2,1)",LEAD=250,STAGED=[],MARKS=[];
function clearOpacity(n){n.style.removeProperty("opacity");if(n.getAttribute("style")==="")n.removeAttribute("style")}
function whenSeen(el,fn){var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){io.disconnect();fn()}})},{threshold:0.2});io.observe(el)}
function play(L){if(L.played)return;L.played=1;var d3=window.d3;L.forEach(function(m){
 if(m.fade){clearOpacity(m.n);m.a=m.n.animate([{opacity:0},{opacity:1}],{duration:m.t,delay:m.d,easing:EASE,fill:"backwards"});return}
 var t=d3.select(m.n).transition().delay(m.d).duration(m.t).ease(d3.easeCubicOut);for(var k in m.to)t.attr(k,m.to[k]);
 t.on("end",function(){setTo(m)})})}
/* the drawn strings exactly: d3 writes an interpolated transform in its own form */
function setTo(m){for(var k in m.to)m.n.setAttribute(k,m.to[k])}
function finishStage(L){L.played=1;L.forEach(function(m){if(m.fade){clearOpacity(m.n);if(m.a)m.a.finish();return}
 window.d3.select(m.n).interrupt();setTo(m)})}
function stage(){var L=[];return {
 /* animate the attributes in `from` to the values the mark carries now */
 attr:function(n,from,d,t){if(!ok||!n)return;var to={};for(var k in from){var v=n.getAttribute(k);if(v==null)return;to[k]=v}
  L.push({n:n,from:from,to:to,d:d||0,t:t||360})},
 fade:function(n,d,t){if(ok&&n)L.push({n:n,fade:1,d:d||0,t:t||220})},
 /* put every mark at its start and play when `el` comes into view */
 run:function(el){if(!ok||!L.length||!window.d3)return;
  L.forEach(function(m){if(m.fade)m.n.style.opacity="0";else for(var k in m.from)m.n.setAttribute(k,m.from[k])});
  L.el=el;STAGED.push(L);whenSeen(el,function(){setTimeout(function(){play(L)},LEAD)})}}}
function finish(){STAGED.forEach(finishStage)}
function emphasis(){document.querySelectorAll(".legend [data-k]").forEach(function(item){var k=item.getAttribute("data-k");
 function on(){MARKS.forEach(function(m){if(m.k!==k)m.n.style.opacity="0.18"});
  document.querySelectorAll('.st[class*=" st-"]').forEach(function(c){if(!c.classList.contains("st-"+k))c.classList.add("em-dim")})}
 function off(){MARKS.forEach(function(m){clearOpacity(m.n)});document.querySelectorAll(".em-dim").forEach(function(c){c.classList.remove("em-dim")})}
 item.addEventListener("mouseenter",on);item.addEventListener("focus",on);item.addEventListener("mouseleave",off);item.addEventListener("blur",off)})}
window.addEventListener("beforeprint",finish);
window.TSMOTION={ok:ok,stage:stage,finish:finish,mark:function(n,k){if(n)MARKS.push({n:n,k:k})},
 waiting:function(){return STAGED.filter(function(L){return !L.played}).map(function(L){return L.el})}};
document.addEventListener("DOMContentLoaded",emphasis);
})();
