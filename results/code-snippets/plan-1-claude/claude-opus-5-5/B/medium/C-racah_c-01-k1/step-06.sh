cd $TMPDIR && cat << 'EOF' > d3.py
import numpy as np, itertools
from collections import Counter
from sympy.physics.wigner import wigner_3j
l=2
def ck(k,m,mp):
    return float((-1)**m*5*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m,m-mp,mp))
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
n=len(orbs)
CK={(k,m,mp):ck(k,m,mp) for k in (2,4) for m in range(-2,3) for mp in range(-2,3)}
dets=list(itertools.combinations(range(n),3))
idx={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    st=list(det);sign=1
    for o,cr in reversed(ops):
        if cr:
            if o in st: return None,0
            pos=sum(1 for x in st if x<o);sign*=(-1)**pos;st.insert(pos,o)
        else:
            if o not in st: return None,0
            pos=st.index(o);sign*=(-1)**pos;st.pop(pos)
    return tuple(st),sign
N=len(dets)
HD=np.zeros((N,N));H2=np.zeros((N,N));H4=np.zeros((N,N))
h=np.zeros((n,n))
for i,(m,s) in enumerate(orbs):
    for j,(mp,sp) in enumerate(orbs):
        if s!=sp: continue
        if m==mp: h[i,j]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
        elif abs(m-mp)==4: h[i,j]=5
for J,d in enumerate(dets):
    for p in range(n):
        for q in range(n):
            if h[p,q]==0: continue
            r,s=apply([(p,1),(q,0)],d)
            if r: HD[idx[r],J]+=s*h[p,q]
    for p in range(n):
     for q in range(n):
      for r_ in range(n):
       for s_ in range(n):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[p],orbs[q],orbs[r_],orbs[s_]
        if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
        r,s=apply([(p,1),(q,1),(s_,0),(r_,0)],d)
        if r:
            H2[idx[r],J]+=0.5*s*CK[(2,ma,mc)]*CK[(2,md,mb)]
            H4[idx[r],J]+=0.5*s*CK[(4,ma,mc)]*CK[(4,md,mb)]
ms=np.array([sum(orbs[i][1] for i in d) for d in dets])
b32=np.where(ms==3)[0];b12=np.where(ms==1)[0]
def spec(Dq,B,C):
    H=Dq*HD+49*(B+C/7)*H2+441*C/35*H4
    e32=np.linalg.eigvalsh(H[np.ix_(b32,b32)]);e12=np.linalg.eigvalsh(H[np.ix_(b12,b12)])
    e0=e32.min()
    c12=Counter(np.round(e12-e0,4));c32=Counter(np.round(e32-e0,4))
    q=sorted(c32);d=sorted(k for k in c12 if c12[k]>c32.get(k,0))
    return q,d
EOF
python3 -c "
from d3 import *
q,d=spec(1417,878,3500);print(q[:5],d[:4])
from scipy.optimize import least_squares
def res(x):
    q,d=spec(*x);return [q[1]-14170,q[2]-21710,q[3]-33970,d[0]-18540]
r=least_squares(res,[1417,878,3500]);print(r.x,res(r.x))
x=r.x;print(spec(x[0],x[1],x[2])[0][:4],spec(*x)[1][:4])
"