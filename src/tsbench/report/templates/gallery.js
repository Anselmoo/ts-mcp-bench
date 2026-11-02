(function(){
var $=function(s,r){return (r||document).querySelector(s)},$$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))};
document.documentElement.classList.add('js');
$$('.clone').forEach(function(c){(c.dataset.from||'').split(' ').forEach(function(id){var n=id&&document.getElementById(id);if(n){var k=n.cloneNode(true);k.removeAttribute('id');c.appendChild(k)}})});
$$('.copy').forEach(function(b){b.addEventListener('click',function(){
 var t=$('pre',b.closest('.repro')).textContent,done=function(){var o=b.textContent;b.textContent='Copied';setTimeout(function(){b.textContent=o},1500)};
 var fb=function(){var a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();try{document.execCommand('copy');done()}catch(e){}document.body.removeChild(a)};
 if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,fb)}else{fb()}})});
var tabs=$$('.gallery .tabs button'),panes=$$('.gallery .pane'),bar=$('.gallery .filters');
var f={model:$('#f-model'),cond:$('#f-cond'),cls:$('#f-cls'),ok:$('#f-ok'),q:$('#f-q')};
var cache=new WeakMap();
function text(el){var t=cache.get(el);if(t===undefined){t=(el.dataset.s||'')+' '+el.textContent.toLowerCase();cache.set(el,t)}return t}
function apply(){
 var q=f.q.value.trim().toLowerCase();
 panes.forEach(function(p){
  var shown=0,total=0;
  $$('.item[data-model]',p).forEach(function(it){
   var d=it.dataset;total++;
   var ok=(!f.model.value||d.model===f.model.value)&&(!f.cond.value||d.cond===f.cond.value)&&(!f.cls.value||d.cls===f.cls.value)&&(!f.ok.value||d.ok===f.ok.value)&&(!q||text(it).indexOf(q)>=0);
   it.hidden=!ok;if(ok)shown++;
  });
  $$('.task',p).forEach(function(g){g.hidden=!$('.item[data-model]:not([hidden])',g)});
  p.dataset.shown=shown;p.dataset.total=total;
 });
 var cur=$('.gallery .pane:not([hidden])'),c=$('#count');if(c&&cur)c.textContent=cur.dataset.shown+' of '+cur.dataset.total;
 chart();
}
function show(id){panes.forEach(function(p){p.hidden=p.id!==id});if(bar)bar.hidden=id==='table';tabs.forEach(function(b){b.setAttribute('aria-selected',b.dataset.pane===id)});apply();}
tabs.forEach(function(b){b.addEventListener('click',function(){show(b.dataset.pane);try{history.replaceState(null,'','#'+b.dataset.pane)}catch(e){}})});
function wilson(k,n){if(!n)return[0,1];var z=1.96,p=k/n,d=1+z*z/n,c=p+z*z/(2*n),h=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n));return[Math.max(0,(c-h)/d),Math.min(1,(c+h)/d)]}
var CONDS=[['A','A no tools'],['B','B code'],['C','C TS-MCP']];
var last='';
function chart(){
 var box=$('#overview'),note=$('#overview-note');if(!box)return;
 var data={},n=0;
 $$('#runs .run[data-model]:not([hidden])').forEach(function(it){
  var ok=it.dataset.ok;if(ok!=='correct'&&ok!=='wrong'&&ok!=='harness')return;
  var m=data[it.dataset.model]=data[it.dataset.model]||{};var c=m[it.dataset.cond]=m[it.dataset.cond]||[0,0];
  c[1]++;n++;if(ok==='correct')c[0]++;
 });
 var sig=JSON.stringify(data);if(sig===last)return;last=sig;
 var models=Object.keys(data).sort();box.textContent='';
 if(!models.length){box.textContent='No evaluable runs in the selection.';return}
 if(!(window.JFS&&window.d3)){box.textContent='Chart not available (JFS missing).';return}
 try{
  var f=JFS.figure(box,{width:'double',height:24+10*models.length});
  var L=130,R=64,T=26,B=28;
  var ax=JFS.axes(f.svg,{rect:{x:L,y:T,w:f.W-L-R,h:f.H-T-B},xDomain:[0,1],yBand:models,grid:'major',xLabel:'Accuracy (fraction of runs, 95 % Wilson CI)'});
  var shapes=[d3.symbolCircle,d3.symbolSquare,d3.symbolDiamond];
  models.forEach(function(m){
   var yc=ax.y(m),ns=[];
   CONDS.forEach(function(cd,i){
    var v=data[m][cd[0]];if(!v){ns.push('–');return}
    var ci=wilson(v[0],v[1]),col=JFS.tok('series-'+(i+1)),yy=yc+(i-1)*3.4,p=v[0]/v[1];
    ax.plot.append('line').attr('x1',ax.x(ci[0])).attr('x2',ax.x(ci[1])).attr('y1',yy).attr('y2',yy).attr('stroke',col).attr('stroke-width',0.5);
    ax.plot.append('path').attr('transform','translate('+ax.x(p)+','+yy+')').attr('d',d3.symbol(shapes[i],10)).attr('fill',col);
    ns.push(String(v[1]));
   });
   ax.g.append('text').attr('x',ax.rect.w+5).attr('y',yc).attr('dominant-baseline','middle').attr('font-size',6).attr('fill',JFS.tok('ink-muted')).text(ns.join(' / '));
  });
  ax.g.append('text').attr('x',ax.rect.w+5).attr('y',-6).attr('font-size',6).attr('fill',JFS.tok('ink-muted')).text('n (A / B / C)');
  var lx=0;CONDS.forEach(function(cd,i){
   var g=ax.g.append('g').attr('transform','translate('+lx+',-14)'),col=JFS.tok('series-'+(i+1));
   g.append('path').attr('d',d3.symbol(shapes[i],10)).attr('fill',col).attr('transform','translate(3,0)');
   g.append('text').attr('x',9).attr('dominant-baseline','middle').attr('font-size',6.5).attr('fill',JFS.tok('ink')).text(cd[1]);
   lx+=22+cd[1].length*3.6;
  });
  if(note)note.textContent=n+' scored runs (correct, wrong, harness limit; without rate-limited and unscored runs) in the current selection.';
 }catch(e){box.textContent='Chart not available ('+e.message+').'}
}
['change','input'].forEach(function(ev){Object.keys(f).forEach(function(k){f[k].addEventListener(ev,apply)})});
var h=(location.hash||'').slice(1);show(panes.some(function(p){return p.id===h})?h:tabs[0].dataset.pane);
})();
