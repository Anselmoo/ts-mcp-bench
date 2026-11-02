/* from a figure or a count to its runs: a bar segment (event tsb:segment from runtime.js), a status tag of the text version or
a count with [data-drill] shows exactly the runs it counts in the run table; "Show all runs" brings the rest back */
(function(){var t=document.getElementById("runtable"),bar=document.getElementById("drill"),f=document.getElementById("run-flt");
if(!t||!bar)return;var tb=t.tBodies[0];
function word(k){var l=document.querySelector('.legend [data-k="'+k+'"]');return l?l.textContent.trim():k}
function reveal(text){bar.firstElementChild.textContent=text;bar.hidden=false;if(history.pushState&&location.hash!=="#run-list")history.pushState(null,"","#run-list");bar.scrollIntoView({block:"start"});bar.focus({preventScroll:true})}
function show(model,cond,label,k){var n=0;f.value="";
Array.prototype.forEach.call(tb.rows,function(r){var on=r.getAttribute("data-model")===model&&r.getAttribute("data-cond")===cond&&r.classList.contains("o-"+k);r.hidden=!on;if(on)n++});
reveal((n?n+" run"+(n===1?"":"s"):"No run in the table")+": "+model+" · "+label+" · "+word(k)+(k==="notrun"?" (planned, never run)":""))}
/* a count of the answer sheet or the class chart: [data-drill] names model, conditions, tasks and outcome of its runs */
function list(s){return s?s.split(","):[]}
function go(a){var d=a.dataset,conds=list(d.cond),tasks=list(d.tasks),n=0;f.value="";
Array.prototype.forEach.call(tb.rows,function(r){
var on=(!d.model||r.getAttribute("data-model")===d.model)&&(!conds.length||conds.indexOf(r.getAttribute("data-cond"))>=0)
&&(!tasks.length||tasks.indexOf(r.cells[2].textContent.trim())>=0)&&(!d.outcome||r.classList.contains("o-"+d.outcome));
r.hidden=!on;if(on)n++});
var tab=document.querySelector('.gallery .tabs button[data-pane="table"]');if(tab&&tab.getAttribute("aria-selected")!=="true")tab.click();
reveal((n?n+" run"+(n===1?"":"s"):"No run in the table")+": "+d.label)}
Array.prototype.forEach.call(document.querySelectorAll("[data-drill]"),function(a){a.addEventListener("click",function(e){e.preventDefault();go(a)})});
bar.querySelector("button").addEventListener("click",function(){bar.hidden=true;Array.prototype.forEach.call(tb.rows,function(r){r.hidden=false})});
f.addEventListener("input",function(){bar.hidden=true});
document.addEventListener("tsb:segment",function(e){var d=e.detail;show(d.model,d.cond,d.label,d.k)});
document.querySelectorAll('.mcard li[data-cond] .st[class*=" st-"]').forEach(function(c){var k=(c.className.match(/st-(\w+)/)||[])[1],li=c.closest("li"),card=c.closest(".mcard");
c.setAttribute("role","button");c.tabIndex=0;function go(){show(card.getAttribute("data-model"),li.getAttribute("data-cond"),li.querySelector("b").textContent,k)}
c.addEventListener("click",go);c.addEventListener("keydown",function(e){if(e.key==="Enter"||e.key===" "){e.preventDefault();go()}})})})();

/* a short id copies its full value (the tooltip) on click */
document.querySelectorAll(".pv code[title]").forEach(function(c){c.addEventListener("click",function(){
if(navigator.clipboard)navigator.clipboard.writeText(c.getAttribute("title")).catch(function(){})})});

(function(){var t=document.getElementById('runtable');if(!t)return;var tb=t.tBodies[0],hs=t.tHead.rows[0].cells;
function val(r,i,n){var c=r.cells[i];if(n){var v=c.getAttribute('data-v');return v===null?-Infinity:parseFloat(v)}return c.textContent.toLowerCase()}
Array.prototype.forEach.call(hs,function(h,i){function go(){var n=h.getAttribute('data-n')==='1',asc=!h.classList.contains('asc');
Array.prototype.forEach.call(hs,function(x){x.classList.remove('asc','desc')});h.classList.add(asc?'asc':'desc');
var rs=Array.prototype.slice.call(tb.rows);rs.sort(function(a,b){var x=val(a,i,n),y=val(b,i,n);return (x<y?-1:x>y?1:0)*(asc?1:-1)});
rs.forEach(function(r){tb.appendChild(r)})}h.addEventListener('click',go);h.addEventListener('keydown',function(e){if(e.key==='Enter')go()})});
var f=document.getElementById('run-flt');f.addEventListener('input',function(){var q=f.value.toLowerCase();
Array.prototype.forEach.call(tb.rows,function(r){r.hidden=q&&r.textContent.toLowerCase().indexOf(q)<0})})})();
