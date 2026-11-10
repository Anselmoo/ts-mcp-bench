
cd <SANDBOX_TMP>/tmp.18wMokKLZh
python3 -c "
from d7 import *
obs={'4T2':(1,6150),'4A2':(1,12400),'4T1':(2,16850),'2T1':(2,19000)}
def pick(t):
    cnt={};d={}
    for e,l in t:
        cnt[l]=cnt.get(l,0)+1; d[(l,cnt[l])]=e
    return d
def resid(p):
    d=pick(table(*p))
    return [d[(k,n)]-v for k,(n,v) in obs.items()]
for g in [(625,800,3200),(640,750,3000),(620,850,3500)]:
    r=least_squares(resid,g,x_scale=[100,100,500])
    print(r.x, resid(r.x), pick(table(*r.x))[('4T1',1)])
t=table(*r.x)
for e,l in t[:14]: print(round(e),l)
"
