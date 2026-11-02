/* The full report works without this script: every tab is shown one below the other and every link is a plain
anchor. With it: one tab at a time (the address #<tab>, #<tab>/<anchor> or #<id> of any element picks the tab and
opens the fold-outs around the target), the table of contents marks the current section, the theme switch cycles
System, Light and Dark and remembers the choice, the model switch (several models only) shows one model's view of the
tabs Models, Tasks and Published spectra and its table of contents, remembers the choice and gives way to an address
whose target lies in another model's view, a run card shows the images and code of its run (copies of the cards
in Diagrams and Code), and the Copy button copies the reproduce commands. */
(function(){
var doc=document,root=doc.documentElement,KEY="tsb-theme";
var $$=function(s,r){return Array.prototype.slice.call((r||doc).querySelectorAll(s))};
root.classList.add("js");

/* theme: no attribute is System; the choice is kept in localStorage when the browser allows it */
var btn=doc.getElementById("theme-switch"),NAMES={"":"system",light:"light",dark:"dark"},NEXT={"":"light",light:"dark",dark:""};
function theme(){return root.getAttribute("data-theme")||""}
function setTheme(t,keep){if(t)root.setAttribute("data-theme",t);else root.removeAttribute("data-theme");
 if(btn)btn.textContent="Theme: "+NAMES[t];
 if(keep){try{if(t)localStorage.setItem(KEY,t);else localStorage.removeItem(KEY)}catch(e){}}}
setTheme(theme(),false);
if(btn)btn.addEventListener("click",function(){setTheme(NEXT[theme()],true)});

/* below 900 px the table of contents is a closed list above the tab; it follows the width of the window */
var narrow=window.matchMedia?window.matchMedia("(max-width:900px)"):null;
function foldToc(){$$("nav.toc details").forEach(function(d){d.open=!narrow.matches})}
if(narrow){foldToc();if(narrow.addEventListener)narrow.addEventListener("change",foldToc);else if(narrow.addListener)narrow.addListener(foldToc)}

/* an address with a broken %-escape is read as it stands */
function dec(s){try{return decodeURIComponent(s)}catch(e){return s}}

/* the height of the top bar keeps anchor targets clear of it */
var bar=doc.querySelector("header.bar");
function barHeight(){if(bar)root.style.setProperty("--bar-h",bar.offsetHeight+"px")}
barHeight();window.addEventListener("resize",barHeight);

/* models: one view per model (.mview[data-model]) and its table of contents (ol.mtoc[data-model]) at a time */
var MKEY="tsb-model",msel=doc.getElementById("model-switch"),mparts=$$(".mview[data-model], ol.mtoc[data-model]");
function setModel(m,keep){if(!msel)return;var names=$$("option",msel).map(function(o){return o.value});
 if(names.indexOf(m)<0)m=names[0];msel.value=m;
 mparts.forEach(function(n){n.classList.toggle("on",n.dataset.model===m)});
 if(keep){try{localStorage.setItem(MKEY,m)}catch(e){}}}
if(msel){var saved=null;try{saved=localStorage.getItem(MKEY)}catch(e){}setModel(saved,false)}

/* tabs */
var tabs=$$("section.tab"),links=$$("nav.tabs a"),current="";
function show(id){var cur=null;current=id;tabs.forEach(function(s){var on=s.id==="tab-"+id;s.classList.toggle("on",on);if(on)cur=s});
 links.forEach(function(a){if(a.dataset.tab===id)a.setAttribute("aria-current","page");else a.removeAttribute("aria-current")});
 if(cur)observe(cur);return cur}
function openAround(el){var d=el.closest("details");while(d){d.open=true;d=d.parentElement&&d.parentElement.closest("details")}
 if(el.tagName==="DETAILS")el.open=true}
function route(){var h=dec(location.hash.slice(1)),parts=h.split("/"),tab=parts[0],target=null;
 if(parts.length>1){target=doc.getElementById(parts.slice(1).join("/"))}
 else if(h&&!doc.getElementById("tab-"+h)){target=doc.getElementById(h);tab=null}
 if(target&&!tab){var sec=target.closest("section.tab");tab=sec?sec.id.slice(4):null}
 if(!tab||!doc.getElementById("tab-"+tab))tab=tabs.length?tabs[0].id.slice(4):"";
 var mv=target&&target.closest(".mview[data-model]");if(mv)setModel(mv.dataset.model,false);
 show(tab);
 if(target){openAround(target);target.scrollIntoView()}else window.scrollTo(0,0)}
window.addEventListener("hashchange",route);

/* the table of contents: the current section is marked while scrolling */
var io=null;
function observe(sec){if(!("IntersectionObserver" in window))return;if(io)io.disconnect();
 var toc=sec.querySelector("nav.toc");if(!toc)return;var as=$$("a",toc),byId={};
 as.forEach(function(a){byId[dec(a.getAttribute("href").slice(1))]=a});
 io=new IntersectionObserver(function(es){es.forEach(function(e){if(!e.isIntersecting)return;var a=byId[e.target.id];
  if(a&&a.parentElement.classList.contains("l2")){as.forEach(function(x){x.classList.remove("cur")});a.classList.add("cur")}})},
  {rootMargin:"-10% 0px -80% 0px"});
 Object.keys(byId).forEach(function(id){var el=doc.getElementById(id);if(el)io.observe(el)})}
route();
/* a new model keeps the tab; an address into the view of another model gives way to the tab itself */
if(msel)msel.addEventListener("change",function(){setModel(msel.value,true);
 var h=dec(location.hash.slice(1)),id=h.split("/").pop(),t=id&&doc.getElementById(id),
  mv=t&&t.closest(".mview[data-model]");
 if(mv&&mv.dataset.model!==msel.value&&history.replaceState)history.replaceState(null,"","#"+current);
 show(current);window.scrollTo(0,0)});

/* run cards: copies of their images and code (the links inside a clone stand in until then); the Copy button */
$$(".clone").forEach(function(c){(c.dataset.from||"").split(" ").forEach(function(id){var n=id&&doc.getElementById(id);
 if(n){var k=n.cloneNode(true);k.removeAttribute("id");c.appendChild(k)}})});
$$(".copy").forEach(function(b){b.addEventListener("click",function(){
 var t=b.closest(".repro").querySelector("pre").textContent,done=function(){var o=b.textContent;b.textContent="Copied";setTimeout(function(){b.textContent=o},1500)};
 var fb=function(){var a=doc.createElement("textarea");a.value=t;a.style.position="fixed";a.style.opacity="0";doc.body.appendChild(a);a.select();
  try{if(doc.execCommand("copy"))done()}catch(e){}doc.body.removeChild(a)};
 if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(t).then(done,fb);else fb()})});

/* print: every fold-out is opened for the printout and restored afterwards (a closed <details> prints its summary only) */
var reopen=[];
window.addEventListener("beforeprint",function(){reopen=$$("details").filter(function(d){return !d.open});reopen.forEach(function(d){d.open=true})});
window.addEventListener("afterprint",function(){reopen.forEach(function(d){d.open=false});reopen=[]});
})();
