cd /tmp/tsbench-run-l39pr0fd; cat > run2.py <<'E'
from ts import *
import json
B=806.;Cc=3570.
def Hx(x): return H2[2]*(49*B+7*Cc)+H2[4]*12.6*Cc+H1*x*B
irr={(1,1):'A1',(-1,-1):'A2',(0,0):'E',(1,-1):'T1',(-1,1):'T2'}
def lv(x):
    xe=x if x>0 else 1e-3
    w,v=np.linalg.eigh(Hx(xe)); H0=Hx(x)
    res=[];i=0
    while i<n:
        j=i
        while j<n and abs(w[j]-w[i])<1e-6*B: j+=1
        P=v[:,i:j]; deg=j-i
        s2=np.trace(P.T@S2@P).real/deg; S=(-1+np.sqrt(1+4*s2))/2; m=int(round(2*S+1))
        c4=np.trace(P.conj().T@R4@P).real/m; c2=np.trace(P.conj().T@R2@P).real/m
        e=np.trace(P.T@H0@P)/deg
        key=(int(round(c4)),int(round(c2)))
        assert deg%m==0 and abs(c4-round(c4))<1e-4, (deg,m,c4,c2)
        res.append((e,f"{m}{irr[key]}g",deg//m)); i=j
    return res
pts=[]
for k in range(9):
    x=k*0.5; r=lv(x); e0=r[0][0]
    for e,l_,d in r[:8]: pass
    lev=[{"term":l_,"e_over_b":round((e-e0)/B,4)} for e,l_,d in r[:6]]
    print(x,[(a['term'],a['e_over_b']) for a in lev])
    pts.append({"dq_over_b":x,"levels":lev})
json.dump(pts,open('pts.json','w'))
# plot
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
xs=np.linspace(0,4,81); data={}
import collections
for x in xs:
    r=lv(x); e0=r[0][0]
    for e,l_,d in r[:12]: pass
    for e,l_,d in r: data.setdefault(l_,[]).append(((x),(e-e0)/B))
plt.figure(figsize=(7,8))
for l_,p in data.items():
    p=np.array(p)
    if p[:,1].min()<80: pass
plt.close()
E
python3 run2.py