(function(){"use strict";
var d3=window.d3,J=window.JFS,AF=window.TSFIG;
if(!d3||!J||!AF)return;
var S=J.STROKE,CS={A:"series-1",B:"series-2",C:"series-3"},SH={A:d3.symbolCircle,B:d3.symbolSquare,C:d3.symbolTriangle};
function col(c){return J.tok(CS[c]||"series-4")}
function shp(c){return SH[c]||d3.symbolDiamond}
function fmt(v){var s=String(Math.round(v*100)/100);return s.replace("-","−")}
function mark(g,p,cx,cy,col0,sz){
 if(p.kind==="paper"){g.append("path").attr("transform","translate("+cx+","+cy+") rotate(45)").attr("d",d3.symbol(d3.symbolCross,sz*1.2))
   .attr("fill","none").attr("stroke",J.tok("ink")).attr("stroke-width",0.9).append("title").text(p.tip);return}
 var m=g.append("path").attr("transform","translate("+cx+","+cy+")").attr("d",d3.symbol(shp(p.cond),sz));
 if(p.out)m.attr("fill",J.tok("paper")).attr("stroke",col0).attr("stroke-width",0.9);
 else m.attr("fill",col0).attr("fill-opacity",0.7).attr("stroke",J.tok("paper")).attr("stroke-width",0.3);
 m.append("title").text(p.tip)}
function legend(g,conds,x0,y,paper){var lx=x0;conds.forEach(function(c){
  g.append("path").attr("transform","translate("+lx+","+y+")").attr("d",d3.symbol(shp(c),12)).attr("fill",col(c));
  g.append("text").attr("x",lx+5).attr("y",y).attr("dominant-baseline","middle").attr("font-size",J.SIZE.legend).attr("fill",col(c)).text(c);lx+=22});
 if(paper){g.append("path").attr("transform","translate("+lx+","+y+") rotate(45)").attr("d",d3.symbol(d3.symbolCross,14)).attr("fill","none").attr("stroke",J.tok("ink")).attr("stroke-width",0.9);
  g.append("text").attr("x",lx+6).attr("y",y).attr("dominant-baseline","middle").attr("font-size",J.SIZE.legend).text("Paper")}}
AF.kinds.parity=function(root,s){
 var W=Math.min(AF.widthOf(root,s,88),110),L=38,R=8,T=16,B=26,Wp=W*J.MM,side=Wp-L-R,hpt=T+B+side,d0=s.dom[0],d1=s.dom[1],t=s.tol;
 var f=J.figure(root,{width:W,height:hpt/J.MM,displayScale:AF.scaleOf(root,s)});
 var ax=J.axes(f.svg,{rect:{x:L,y:T,w:side,h:side},xDomain:s.dom,yDomain:s.dom,nice:false,grid:"major",xLabel:s.xLabel,yLabel:s.yLabel,
  xFormat:fmt,yFormat:fmt,xTicks:4,yTicksN:4,yLabelOffset:30});
 var x=ax.x,y=ax.y;
 ax.plot.append("path").attr("d","M"+x(d0)+","+y(d0*(1-t))+"L"+x(d1)+","+y(d1*(1-t))+"L"+x(d1)+","+y(d1*(1+t))+"L"+x(d0)+","+y(d0*(1+t))+"Z")
  .attr("fill",J.tok("house-tint")).attr("stroke","none");
 ax.plot.append("line").attr("x1",x(d0)).attr("y1",y(d0)).attr("x2",x(d1)).attr("y2",y(d1)).attr("stroke",J.tok("rule")).attr("stroke-width",S.axis).attr("stroke-dasharray","2 2");
 s.pts.forEach(function(p){var yy=Math.min(Math.max(p.y,d0),d1);mark(ax.plot,p,x(p.x),y(yy),col(p.cond),14)});
 legend(f.svg,s.conds,L,T-8,s.pts.some(function(p){return p.kind==="paper"}));
 return f};
AF.kinds.relerr=function(root,s){
 var rows=s.rows,n=rows.length,L=s.left||110,R=10,T=16,B=26,rh=21,W=AF.widthOf(root,s,120),Wp=W*J.MM,hpt=T+B+n*rh+8,d0=s.dom[0],d1=s.dom[1],t=s.tol;
 var f=J.figure(root,{width:W,height:hpt/J.MM,displayScale:AF.scaleOf(root,s)});
 var ax=J.axes(f.svg,{rect:{x:L,y:T,w:Wp-L-R,h:hpt-T-B},xDomain:s.dom,yBand:rows,grid:"major",xLabel:s.xLabel,xFormat:fmt,xTicks:6});
 ax.plot.append("rect").attr("x",ax.x(-t)).attr("width",ax.x(t)-ax.x(-t)).attr("y",0).attr("height",ax.rect.h).attr("fill",J.tok("house-tint"));
 ax.plot.append("line").attr("x1",ax.x(0)).attr("x2",ax.x(0)).attr("y1",0).attr("y2",ax.rect.h).attr("stroke",J.tok("rule")).attr("stroke-width",S.axis).attr("stroke-dasharray","2 2");
 var LANE={A:-6.5,B:-2.2,C:2.2};
 s.pts.forEach(function(p){var yc=ax.y(p.row),off=p.kind==="paper"?7:(LANE[p.cond]||0)+(((p.j||0)%5)-2)*0.45;
  mark(ax.plot,p,ax.x(p.x),yc+off,col(p.cond),12)});
 legend(f.svg,s.conds,L,T-8,s.pts.some(function(p){return p.kind==="paper"}));
 return f};
document.querySelectorAll("figure.litfig").forEach(AF.render);
})();
