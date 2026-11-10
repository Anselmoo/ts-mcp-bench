
python3 - <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j as w
from scipy.optimize import fsolve
ms=[2,1,0,-1,-2]
def ck(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*5*w(2,k,2,-m1,q,m2)*w(2,k,2,0,0,0))
Ck={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),6) if sum(1 if so[i][1]==0 else -1 for i in d)==0]
idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def ann(p,d):
    if p not in d: return 0,None
    pos=d.index(p); return (-1)**pos, tuple(x for x in d if x!=p)
def cre(p,d):
    if p in d: return 0,None
    pos=sum(1 for x in d if x<p); return (-1)**pos, tuple(sorted(d+(p,)))
def V2(p,q,r,s,F):
    (a,sa),(b,sb),(c,sc),(d,sd)=so[p],so[q],so[r],so[s]
    if sa!=sc or sb!=sd or a+b!=c+d: return 0
    return sum(Ck[(k,a,c)]*Ck[(k,d,b)]*F[k] for k in (2,4))
twoall=[(p,q,r,s) for p in range(10) for q in range(10) for r in range(10) for s in range(10) if p!=q and r!=s and so[p][1]==so[r][1] and so[q][1]==so[s][1] and so[p][0]+so[q][0]==so[r][0]+so[s][0]]
def H(B,C,Dq):
    F={2:49*(B+C/7),4:441*C/35}
    h=np.zeros((N,N))
    Vm=np.zeros((5,5))
    for i,m in enumerate(ms): Vm[i,i]={2:1,1:-4,0:6,-1:-4,-2:1}[m]*Dq
    Vm[0,4]=Vm[4,0]=5*Dq
    one=[(p,q,Vm[ms.index(so[p][0]),ms.index(so[q][0])]) for p in range(10) for q in range(10) if so[p][1]==so[q][1] and Vm[ms.index(so[p][0]),ms.index(so[q][0])]!=0]
    two=[(p,q,r,s,V2(p,q,r,s,F)) for p,q,r,s in twoall]; two=[t for t in two if abs(t[4])>1e-12]
    for j,d in enumerate(dets):
        for p,q,v in one:
            s1,d1=ann(q,d)
            if not s1: continue
            s2,d2=cre(p,d1)
            if s2: h[idx[d2],j]+=v*s1*s2
        for p,q,r,s,v in two:
            s1,d1=ann(r,d)
            if not s1: continue
            s2,d2=ann(s,d1)
            if not s2: continue
            s3,d3=cre(q,d2)
            if not s3: continue
            s4,d4=cre(p,d3)
            if s4: h[idx[d4],j]+=0.5*v*s1*s2*s3*s4
    return h
S2=np.zeros((N,N))
for j,d in enumerate(dets):
    st={}
    for m in range(5):
        s1,d1=ann(2*m+1,d)
        if not s1: continue
        s2,d2=cre(2*m,d1)
        if s2: st[d2]=st.get(d2,0)+s1*s2
    out={}
    for d2,c in st.items():
        for m in range(5):
            s1,d3=ann(2*m,d2)
            if not s1: continue
            s2,d4=cre(2*m+1,d3)
            if s2: out[d4]=out.get(d4,0)+c*s1*s2
    for d4,c in out.items(): S2[idx[d4],j]+=c
def tr(x):
    Dq,B=x
    e=np.linalg.eigvalsh(H(B,4.5*B,Dq)+1e5*S2); return e-e[0]
def f(x):
    e=tr(x); return [e[1]-16474,e[4]-25381]
s=fsolve(f,[2000,600]); print(s,f(s)); print(np.round(tr(s)[:8]))
E