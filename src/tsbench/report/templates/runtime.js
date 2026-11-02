
(function(){"use strict";
var d3=window.d3,J=window.JFS;
function fail(el,e){var p=document.createElement("p");p.className="err";p.textContent="Figure could not be drawn: "+e;el.appendChild(p);if(window.console)console.error(e)}
if(!d3||!J){document.querySelectorAll("figure.jfs").forEach(function(el){fail(el,"d3/Figura missing")});return}
/* Colours: the Figura theme `neutral`, and on a dark screen its dark twin with the page's dark tokens (base.html.j2), so a figure
   sits on the page instead of a white plate. A saved SVG and a printed page are always drawn in the light theme. */
J.THEMES.neutral["on-series"]="#ffffff";
J.THEMES["neutral-dark"]={"ink":"#e6e8ea","ink-muted":"#a7b0b9","paper":"#161a20","rule":"#6b737c","grid":"#2c323a","fill-soft":"#1d2533",
 "series-1":"#7ab0ff","series-2":"#e0b04a","series-3":"#f07fae","series-4":"#6cc0f0","series-5":"#5ccf86","series-6":"#ff8a80",
 "house-primary":"#7ab0ff","house-deep":"#dce6f8","house-tint":"#1d2533","house-signal":"#8ab8ff","on-series":"#0e1116"};
var DARKQ=window.matchMedia?window.matchMedia("(prefers-color-scheme: dark)"):null,PRINT=false;
function darkPage(){var m=document.querySelector('meta[name="color-scheme"]');return !PRINT&&!!(DARKQ&&DARKQ.matches&&m&&/dark/.test(m.content))}
function theme(){J.useTheme(darkPage()?"neutral-dark":"neutral")}
theme();
var K=J.STROKE,SH=[d3.symbolCircle,d3.symbolSquare,d3.symbolTriangle,d3.symbolDiamond],uid=0;
var CC={A:"series-1",B:"series-2",C:"series-3","B fixed":"series-4"},XC=["series-4","series-5","series-6"];
function ccol(k,i){return J.tok(CC[k]||XC[(i||0)%3])}
function shapeOf(k,i){var ix={A:0,B:1,C:2,"B fixed":3}[k];return SH[ix==null?(i||0)%4:ix]}
var DEC=".",MV=null,PX=96/25.4;
/* The figures fill the width of their column: the width in mm follows the drawing area (`root`), so a figure is never
   scaled down and its text keeps its size (12 px at scale 1.5). A narrow column (a phone) draws at scale 1.3 and
   stacks the panels; without a measurable column (hidden, printing) the spec's width stands. */
function narrow(root){var px=root.clientWidth;return px>0&&px<600}
function scaleOf(root,s){return narrow(root)?1.3:(s.scale||1.5)}
function widthOf(root,s,dflt){var px=root.clientWidth;if(s.fixed||!px)return s.width||dflt;return Math.max(px/PX/scaleOf(root,s),50)}
/* motion (templates/motion.js): the stage of the figure being drawn; no-ops without it */
function mvA(n,from,d,t){if(MV)MV.attr(n,from,d,t)}
function mvF(n,d,t){if(MV)MV.fade(n,d,t)}
function mark(n,k){if(window.TSMOTION)window.TSMOTION.mark(n,k)}
function de(v,nd){if(v==null||isNaN(v))return "–";var a=Math.abs(v);if(nd==null)nd=a>=100?0:a>=10?1:a>=1?2:3;
 return d3.format(".%df".replace("%d",nd))(v).replace(".",DEC)}
function tickFmt(v){var s;if(v>=10000)return d3.format("~g")(v/1000).replace(".",DEC)+" k";s=d3.format("~g")(v);return s.replace(".",DEC)}
function intFmt(v){return Math.abs(v-Math.round(v))<1e-9?String(Math.round(v)):""}
function hatch(svg,col,dir,w){var id="h"+(++uid),d=svg.select("defs");if(d.empty())d=svg.insert("defs",":first-child");
 var p=d.append("pattern").attr("id",id).attr("width",3).attr("height",3).attr("patternUnits","userSpaceOnUse").attr("patternTransform","rotate("+(dir||45)+")");
 p.append("rect").attr("width",3).attr("height",3).attr("fill",J.tok("paper"));
 p.append("line").attr("x1",0).attr("x2",0).attr("y1",0).attr("y2",3).attr("stroke",col).attr("stroke-width",w||0.9);return "url(#"+id+")"}
/* band labels wider than w are cut with an ellipsis before the last " · " part (the condition stays readable);
   the full label stays as a <title> */
function fitLabels(ax,w){ax.g.selectAll(".jfs-yaxis text").each(function(){var el=this,full=el.textContent;
 if(!el.getComputedTextLength||el.getComputedTextLength()<=w)return;
 var k=full.lastIndexOf(" \u00b7 "),s=k>0?full.slice(0,k):full,tail=k>0?full.slice(k):"";
 while(s.length>3&&el.getComputedTextLength()>w){s=s.slice(0,-1);el.textContent=s+"\u2026"+tail}
 d3.select(el).append("title").text(full)})}
function legend(ax,items,y){var lx=0;items.forEach(function(it){var g=ax.g.append("g").attr("transform","translate("+lx+","+(y==null?-12:y)+")");
 g.append("path").attr("d",d3.symbol(it.shape,12)).attr("fill",it.color);
 g.append("text").attr("x",4.5).attr("dominant-baseline","middle").attr("font-size",J.SIZE.legend).attr("fill",it.color).text(it.name);
 lx+=14+it.name.length*3.1})}
function glyph(g,kind,cx,cy,col){var s=2.2;
 if(kind==="correct")g.append("path").attr("d","M"+(cx-s)+","+cy+"l"+s*0.8+","+s*0.9+"l"+s*1.5+","+(-s*1.8)).attr("fill","none").attr("stroke",col).attr("stroke-width",0.9).attr("stroke-linecap","round");
 if(kind==="wrong")g.append("path").attr("d","M"+(cx-s)+","+(cy-s)+"l"+2*s+","+2*s+"M"+(cx+s)+","+(cy-s)+"l"+(-2*s)+","+2*s).attr("stroke",col).attr("stroke-width",0.9).attr("stroke-linecap","round");
 if(kind==="harness"){g.append("path").attr("d","M"+cx+","+(cy-s)+"v"+s*1.5).attr("stroke",col).attr("stroke-width",1).attr("stroke-linecap","round");g.append("circle").attr("cx",cx).attr("cy",cy+s*0.9).attr("r",0.6).attr("fill",col)}}

var KINDS={
/* a: share correct with 95 % interval (no caps), counts only below five evaluable runs (r.few); b: runs stacked by
   outcome (count); one row per condition.
   s.stack puts b under a in one column (small multiples side by side); s.nmax gives every card the same run axis. */
rate:function(root,s){
 var st=!!s.stack||narrow(root),rows=s.rows,n=rows.length,T=16,B=26,L=s.left||88,R1=54,GAP=14,RB=6,rh=18,ph=n*rh+8,hpt=st?2*(T+B+ph):T+B+ph;
 var f=J.figure(root,{width:widthOf(root,s,st?"single":125),height:hpt/J.MM,displayScale:scaleOf(root,s)});
 if(st)L=Math.min(L,f.W*0.36);
 var inner=st?f.W-L-R1-RB:f.W-L-R1-GAP-RB,pa=st?inner:inner*0.5,pb=st?inner+R1:inner-pa,labels=rows.map(function(r){return r.label});
 var a=J.axes(f.svg,{rect:{x:L,y:T,w:pa,h:ph},xDomain:[0,100],yBand:labels,grid:"major",xLabel:(s.labels&&s.labels.xa)||"Share correct (%), line: 95 % interval",xFormat:intFmt,xTicks:5});
 var nmax=s.nmax||d3.max(rows,function(r){return r.total})||1,bx=st?L:L+pa+R1+GAP,by=st?2*T+ph+B:T;
 var ob={rect:{x:bx,y:by,w:pb,h:ph},xDomain:[0,nmax],yBand:labels,grid:"major",xLabel:(s.labels&&s.labels.xb)||"Runs (count)",xFormat:intFmt,xTicks:Math.min(nmax,5)};
 if(!st)ob.yTicks=false;
 var b=J.axes(f.svg,ob);
 fitLabels(a,L-8);fitLabels(b,L-8);
 J.panelLabel(f.svg,"a",2,2);J.panelLabel(f.svg,"b",st?2:L+pa+R1+GAP-8,st?by-T+2:2);
 var PAT={harness:hatch(f.svg,J.tok("rule"),45)};
 var FILL={correct:J.tok("series-5"),wrong:J.tok("series-6"),harness:PAT.harness,na429:J.tok("grid"),notrun:J.tok("paper")};
 rows.forEach(function(r,i){var yc=a.y(r.label),col=ccol(r.cond,i),ev=r.n_eval>0;
  if(ev&&!r.few){var ci=a.plot.append("line").attr("x1",a.x(r.lo)).attr("x2",a.x(r.hi)).attr("y1",yc).attr("y2",yc).attr("stroke",col).attr("stroke-width",K.axis);
   var pt=a.plot.append("path").attr("transform","translate("+a.x(r.p)+","+yc+")").attr("d",d3.symbol(shapeOf(r.cond,i),14)).attr("fill",col);
   pt.append("title").text(r.tip||(r.label+": "+de(r.p,0)+" % ("+r.correct+"/"+r.n_eval+")"));
   mvF(pt.node(),i*90);mvA(ci.node(),{x1:a.x(r.p),x2:a.x(r.p)},160+i*90,420)}
  mvF(a.g.append("text").attr("x",pa+RB).attr("y",yc).attr("dominant-baseline","middle").attr("font-size",J.SIZE.legend).attr("fill",J.tok("ink"))
   .text(ev&&!r.few?de(r.p,0)+" % ("+r.correct+"/"+r.n_eval+")":ev?r.correct+"/"+r.n_eval:(s.labels&&s.labels.none)||"no runs").node(),320+i*90);
  /* fewer than five evaluable runs: the interval would span most of the axis, so the row says why it has no share */
  if(r.few){var ft=a.g.append("text").attr("x",3).attr("y",yc).attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick)
   .attr("fill",J.tok("ink-muted")).text("n = "+r.n_eval+": too few runs for a share");
   if(ft.node().getComputedTextLength&&ft.node().getComputedTextLength()>pa-6)ft.text("n = "+r.n_eval+", no share");
   ft.append("title").text(r.tip);mvF(ft.node(),i*90)}
  var x0=0,seg=b.plot.append("g");
  (r.seg||[]).forEach(function(sg,j){var k=sg[0],c=sg[1];if(!c)return;var x1=b.x(x0),x2=b.x(x0+c),w=x2-x1;
   var rc=seg.append("rect").attr("x",x1).attr("y",yc-4.5).attr("width",Math.max(w-0.6,0.3)).attr("height",9).attr("fill",FILL[k])
    .attr("stroke",k==="notrun"?J.tok("rule"):J.tok("ink")).attr("stroke-width",K.axis).attr("stroke-dasharray",k==="notrun"?"1.5 1":null);
   rc.append("title").text(sg[2]+": "+c);mvA(rc.node(),{width:0},140+i*90+j*70,320);mark(rc.node(),k);
   /* a page with the runs of this figure (s.model) shows the runs a segment counts: event tsb:segment */
   if(s.model)rc.attr("data-k",k).on("click",function(){root.dispatchEvent(new CustomEvent("tsb:segment",
    {bubbles:true,detail:{model:s.model,cond:r.cond,label:r.label,k:k}}))});
   if(w>=15){glyph(seg,k,x1+5,yc,(k==="correct"||k==="wrong")?J.tok("on-series"):J.tok("ink"));
    seg.append("text").attr("x",x1+9.5).attr("y",yc).attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick).attr("fill",(k==="correct"||k==="wrong")?J.tok("on-series"):J.tok("ink")).text(c)}
   else if(w>=5)seg.append("text").attr("x",(x1+x2)/2).attr("y",yc).attr("text-anchor","middle").attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick)
    .attr("fill",(k==="correct"||k==="wrong")?J.tok("on-series"):J.tok("ink")).text(c);
   x0+=c});
  seg.selectAll(":scope>:not(rect)").each(function(){mvF(this,520+i*90)})});
 return f},
/* one dot per row (model) and condition; the value as a direct label */
dots:function(root,s){
 var rows=s.rows,cs=s.conds,T=s.legend===false?8:20,B=26,L=s.left||56,R=s.right!=null?s.right:40,per=cs.length*7.4+8,hpt=T+B+rows.length*per+4;
 var vals=[];rows.forEach(function(r){cs.forEach(function(c){var v=r.v[c];if(v!=null)vals.push(v)})});var hi=s.domain?s.domain[1]:(d3.max(vals)||1)*1.18;
 var f=J.figure(root,{width:widthOf(root,s,"single"),height:hpt/J.MM,displayScale:scaleOf(root,s)});
 var ax=J.axes(f.svg,{rect:{x:L,y:T,w:f.W-L-R,h:hpt-T-B},xDomain:[0,hi],yBand:rows.map(function(r){return r.label}),grid:"major",xLabel:s.xLabel,xFormat:s.int?intFmt:tickFmt,xTicks:4});
 f.ax=ax;var dod=function(k){return (k-(cs.length-1)/2)*7.4};
 rows.forEach(function(r,ri){var yc=ax.y(r.label);cs.forEach(function(c,k){var v=r.v[c],yy=yc+dod(k),col=ccol(c,k),dl=ri*60+k*80;
  if(v==null){ax.g.append("text").attr("x",3).attr("y",yy).attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick).attr("fill",J.tok("ink-muted")).text(r.na&&r.na[c]||"–");return}
  var ci=r.ci&&r.ci[c];
  var ln=ci?ax.plot.append("line").attr("x1",ax.x(ci[0])).attr("x2",ax.x(ci[1])).attr("y1",yy).attr("y2",yy).attr("stroke",col).attr("stroke-width",K.axis)
   :ax.plot.append("line").attr("x1",ax.x(0)).attr("x2",ax.x(v)).attr("y1",yy).attr("y2",yy).attr("stroke",col).attr("stroke-width",K.axis);
  var pt=ax.plot.append("path").attr("transform","translate("+ax.x(v)+","+yy+")").attr("d",d3.symbol(shapeOf(c,k),14)).attr("fill",col);
  pt.append("title").text((r.tips&&r.tips[c])||(r.label+" · "+c+": "+de(v)));
  mvA(ln.node(),ci?{x1:ax.x(v),x2:ax.x(v)}:{x2:ax.x(0)},120+dl,420);mvF(pt.node(),ci?dl:380+dl);
  var lb=ax.g.append("text").attr("x",Math.min(Math.max(ax.x(ci?ci[1]:v),ax.x(v))+4,ax.rect.w-2)).attr("y",yy).attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick).attr("fill",J.tok("ink")).text((r.t&&r.t[c]!=null)?r.t[c]:de(v));mvF(lb.node(),480+dl)})});
 if(s.legend!==false)legend(ax,cs.map(function(c,k){return {name:s.names[c]||c,color:ccol(c,k),shape:shapeOf(c,k)}}),-14);
 return f},
/* horizontal box plot: whiskers without caps, filled = correct, hatched = wrong */
box:function(root,s){
 var rows=s.rows,T=8,B=26,L=s.left||60,R=34,rh=11,hpt=T+B+rows.length*rh+8;
 var f=J.figure(root,{width:widthOf(root,s,"single"),height:hpt/J.MM,displayScale:scaleOf(root,s)});
 var ax=J.axes(f.svg,{rect:{x:L,y:T,w:f.W-L-R,h:hpt-T-B},xLog:!!s.log,xDomain:s.domain,yBand:rows.map(function(r){return r.label}),grid:"major",xLabel:s.xLabel,xFormat:tickFmt,xTicks:4});
 f.ax=ax;
 rows.forEach(function(r,i){var yc=ax.y(r.label),st=r.st,col=ccol(r.cond,i);
  if(!st){ax.g.append("text").attr("x",3).attr("y",yc).attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick).attr("fill",J.tok("ink-muted")).text(s.none||"no values");
   ax.g.append("text").attr("x",ax.rect.w+4).attr("y",yc).attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick).text("n=0");return}
  var g=ax.plot.append("g");g.append("title").text(r.tip);mvF(g.node(),100+i*70,320);
  g.append("line").attr("x1",ax.x(st.lo)).attr("x2",ax.x(st.q1)).attr("y1",yc).attr("y2",yc).attr("stroke",col).attr("stroke-width",K.axis);
  g.append("line").attr("x1",ax.x(st.q3)).attr("x2",ax.x(st.hi)).attr("y1",yc).attr("y2",yc).attr("stroke",col).attr("stroke-width",K.axis);
  g.append("rect").attr("x",ax.x(st.q1)).attr("y",yc-3.2).attr("width",Math.max(ax.x(st.q3)-ax.x(st.q1),0.8)).attr("height",6.4)
   .attr("fill",r.ok?col:hatch(f.svg,col,45)).attr("stroke",col).attr("stroke-width",K.data);
  g.append("line").attr("x1",ax.x(st.median)).attr("x2",ax.x(st.median)).attr("y1",yc-3.2).attr("y2",yc+3.2).attr("stroke",r.ok?J.tok("paper"):J.tok("ink")).attr("stroke-width",1.2);
  (st.out||[]).forEach(function(o){g.append("circle").attr("cx",ax.x(o)).attr("cy",yc).attr("r",1.3).attr("fill","none").attr("stroke",col).attr("stroke-width",K.axis)});
  ax.g.append("text").attr("x",ax.rect.w+4).attr("y",yc).attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick).text("n="+st.n)});
 return f},
/* task by task: per row (C against another condition) the tasks where C's share correct is higher, the same or lower, stacked on
   one count axis; every segment names its count and its meaning, never colour alone */
pairs:function(root,s){
 var rows=s.rows,T=6,B=26,L=s.left||70,R=8,rh=20,ph=rows.length*rh+6,hpt=T+B+ph;
 var f=J.figure(root,{width:widthOf(root,s,"double"),height:hpt/J.MM,displayScale:scaleOf(root,s)});
 var nmax=d3.max(rows,function(r){return r.n})||1;
 var ax=J.axes(f.svg,{rect:{x:L,y:T,w:f.W-L-R,h:ph},xDomain:[0,nmax],yBand:rows.map(function(r){return r.label}),grid:"major",
  xLabel:s.xLabel||"Tasks (count)",xFormat:intFmt,xTicks:Math.min(nmax,5)});
 var FILL={higher:J.tok("series-5"),same:J.tok("grid"),lower:J.tok("series-6")},INK={higher:J.tok("on-series"),same:J.tok("ink"),lower:J.tok("on-series")};
 rows.forEach(function(r,i){var yc=ax.y(r.label),x0=0,g=ax.plot.append("g");
  r.seg.forEach(function(sg,j){var k=sg[0],c=sg[1];if(!c)return;var x1=ax.x(x0),x2=ax.x(x0+c),w=x2-x1;
   var rc=g.append("rect").attr("x",x1).attr("y",yc-6).attr("width",Math.max(w-0.6,0.3)).attr("height",12).attr("fill",FILL[k])
    .attr("stroke",J.tok("ink")).attr("stroke-width",K.axis);
   rc.append("title").text(r.label+": "+sg[2]);mvA(rc.node(),{width:0},140+i*90+j*70,320);
   var t=c+" "+sg[3],full=t.length*3.1+6<w;
   if(w>=7)g.append("text").attr("x",full?x1+3:(x1+x2)/2).attr("y",yc).attr("text-anchor",full?"start":"middle").attr("dominant-baseline","middle")
    .attr("font-size",J.SIZE.tick).attr("fill",INK[k]).text(full?t:c);
   x0+=c});
  g.selectAll(":scope>text").each(function(){mvF(this,520+i*90)})});
 return f},
/* before and after per row (quality page): hollow square = before, filled circle = after, a thin line between;
   the values as direct labels, a drop named in words */
dumbbell:function(root,s){
 var rows=s.rows,T=24,B=26,L=s.left||64,R=96,rh=12,hpt=T+B+rows.length*rh+4;
 var f=J.figure(root,{width:widthOf(root,s,"double"),height:hpt/J.MM,displayScale:scaleOf(root,s)});
 var ax=J.axes(f.svg,{rect:{x:L,y:T,w:f.W-L-R,h:hpt-T-B},xDomain:s.domain,yBand:rows.map(function(r){return r.label}),grid:"major",xLabel:s.xLabel,xTicks:5});
 var CB=J.tok("series-2"),CA=J.tok("series-1"),SB=d3.symbolSquare,SA=d3.symbolCircle,one=d3.format(".1f");
 function v1(v){return v==null?"–":one(v)}
 function mk(g,v,yc,before){var p=g.append("path").attr("transform","translate("+ax.x(v)+","+yc+")");
  if(before)p.attr("d",d3.symbol(SB,12)).attr("fill",J.tok("paper")).attr("stroke",CB).attr("stroke-width",K.data);
  else p.attr("d",d3.symbol(SA,14)).attr("fill",CA);return p.node()}
 rows.forEach(function(r,i){var yc=ax.y(r.label),g=ax.g.append("g"),d=150+i*45,both=r.before!=null&&r.after!=null;g.append("title").text(r.tip);
  if(both){var ln=g.append("line").attr("x1",ax.x(r.before)).attr("x2",ax.x(r.after)).attr("y1",yc).attr("y2",yc).attr("stroke",J.tok("rule")).attr("stroke-width",K.component);
   mvA(ln.node(),{x2:ax.x(r.before)},d,520)}
  if(r.before!=null)mk(g,r.before,yc,true);
  if(r.after!=null){var am=mk(g,r.after,yc,false);if(both)mvA(am,{transform:"translate("+ax.x(r.before)+","+yc+")"},d,520);else mvF(am,d)}
  mvF(ax.g.append("text").attr("x",ax.rect.w+5).attr("y",yc).attr("dominant-baseline","middle").attr("font-size",J.SIZE.tick)
   .attr("fill",r.drop?J.tok("series-6"):J.tok("ink")).text(v1(r.before)+" → "+v1(r.after)+(r.drop?"  dropped":"")).node(),d+520)});
 var lx=0;[[s.names.before,true],[s.names.after,false]].forEach(function(it){var g=ax.g.append("g").attr("transform","translate("+lx+",-14)");
  if(it[1])g.append("path").attr("d",d3.symbol(SB,12)).attr("fill",J.tok("paper")).attr("stroke",CB).attr("stroke-width",K.data);
  else g.append("path").attr("d",d3.symbol(SA,14)).attr("fill",CA);
  g.append("text").attr("x",5).attr("dominant-baseline","middle").attr("font-size",J.SIZE.legend).attr("fill",J.tok("ink")).text(it[0]);
  lx+=18+it[0].length*3.2});
 return f}
};
function render(el){try{var s=JSON.parse(el.querySelector("script.spec").textContent);DEC=s.dec||".";var host=el.querySelector(".plot");host.innerHTML="";
 MV=window.TSMOTION&&!el._f?window.TSMOTION.stage():null;
 var f=KINDS[el.getAttribute("data-kind")](host,s),svg=f.svg.node();if(MV)MV.run(el);MV=null;svg.setAttribute("role","img");svg.setAttribute("aria-label",el.getAttribute("data-alt")||"");
 el._f=f;el._w=host.clientWidth;if(!el.querySelector(".dl")){var b=document.createElement("button");b.type="button";b.className="dl";b.textContent="Save SVG";
  b.addEventListener("click",function(){if(window.TSMOTION)window.TSMOTION.finish();var name=(el.getAttribute("data-kind")||"figure")+".svg";
   if(!darkPage()){J.download(el._f,name);return}
   /* on a dark screen: draw a light copy at the same size off screen and save that */
   var tmp=document.createElement("div"),host=el.querySelector(".plot");tmp.style.cssText="position:absolute;left:-99999px;top:0;width:"+host.clientWidth+"px";
   document.body.appendChild(tmp);PRINT=true;theme();try{var sp=JSON.parse(el.querySelector("script.spec").textContent);J.download(KINDS[el.getAttribute("data-kind")](tmp,sp),name)}
   finally{PRINT=false;theme();tmp.remove()}});el.appendChild(b)}
}catch(e){MV=null;fail(el,e)}}
document.querySelectorAll("figure.jfs").forEach(render);
/* a column that changes its width (a turned phone, a resized window) draws its figures again, without motion */
var rt=null;window.addEventListener("resize",function(){clearTimeout(rt);rt=setTimeout(function(){
 if(window.TSMOTION)window.TSMOTION.finish();
 document.querySelectorAll("figure[data-kind]").forEach(function(el){var h=el.querySelector(".plot");
  if(el._f&&h&&KINDS[el.getAttribute("data-kind")]&&Math.abs(h.clientWidth-(el._w||0))>24)render(el)})},200)});
/* the colour scheme changes, or the page is printed: draw every figure again in the matching theme, without motion */
function redrawAll(){theme();document.querySelectorAll("figure[data-kind]").forEach(function(el){if(el._f&&KINDS[el.getAttribute("data-kind")])render(el)})}
if(DARKQ&&DARKQ.addEventListener)DARKQ.addEventListener("change",redrawAll);
window.addEventListener("beforeprint",function(){if(darkPage()){PRINT=true;redrawAll()}});
window.addEventListener("afterprint",function(){if(PRINT){PRINT=false;redrawAll()}});
window.TSFIG={render:render,kinds:KINDS,mvA:mvA,mvF:mvF,widthOf:widthOf,scaleOf:scaleOf,narrow:narrow};
})();
