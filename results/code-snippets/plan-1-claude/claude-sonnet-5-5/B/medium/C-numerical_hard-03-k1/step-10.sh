
cd /dev/shm && cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
Ck={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
def sgn(seq):
    return (-1)**sum(1 for x in range(len(seq)) for y in range(x+1,len(seq)) if seq[x]>seq[y])
s=1/np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,x in d.items(): v[m+2]=x
    return v
eg=[vec({0:1}),vec({2:s,-2:s})]
t2=[vec({2:s,-2:-s}),vec({1:1}),vec({-1:1})]
h=sum(6*np.outer(v,v.conj()) for v in eg)+sum(-4*np.outer(v,v.conj()) for v in t2)
def V(a,b,c_,d,k):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c_],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return Ck[(k,mc,ma)]*Ck[(k,mb,md)]
def build(twoMs):
    dets=[d for d in itertools.combinations(range(10),5) if sum(1 if so[i][1] else -1 for i in d)==twoMs]
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets)
    H1=np.zeros((N,N),complex)
    for d in dets:
        for p,a in enumerate(d):
            for b in range(10):
                if so[a][1]!=so[b][1]: continue
                if b!=a and b in d: continue
                hv=h[so[b][0]+2,so[a][0]+2]
                if abs(hv)<1e-12: continue
                l=list(d);l[p]=b
                H1[idx[tuple(sorted(l))],idx[d]]+=hv*sgn(l)
    H2={2:np.zeros((N,N),complex),4:np.zeros((N,N),complex)}
    for d in dets:
        for p in range(5):
         for q in range(p+1,5):
          a,b=d[p],d[q]
          rest=[x for x in d if x not in(a,b)]
          for c_ in range(10):
           for e in range(c_+1,10):
            if c_ in rest or e in rest: continue
            seq=[c_,e]+rest
            for k in (2,4):
                amp=V(c_,e,a,b,k)-V(c_,e,b,a,k)
                if abs(amp)<1e-12: continue
                H2[k][idx[tuple(sorted(seq))],idx[d]]+=amp*sgn(seq)*(-1)**(p+q-1)
    return H1,H2
B1=build(1);B3=build(3)
def spec(Dq,B,Cc):
    F2=49*B+7*Cc;F4=63*Cc/5
    def ev(Bd):
        H=Dq*Bd[0]+F2*Bd[1][2]+F4*Bd[1][4]
        return np.linalg.eigvalsh(H)
    w1=list(ev(B1))
    for x in ev(B3):
        j=int(np.argmin([abs(x-y) for y in w1]));w1.pop(j)
    return np.array(sorted(w1))
E
cat > b.py <<'E'
from a import *
from scipy.optimize import least_squares
obs=np.array([22640,22930,25080])
def lev(Dq,B):
    w=spec(Dq,B,4.6*B);w=w-w[0]
    u=[]
    for x in w:
        if not u or x-u[-1]>1: u.append(x)
    return np.array(u)
for D in [1500,2000,2500,3000]:
    print(D,np.round(lev(D,600)[:8]))
best=[]
for D0 in [1500,2000,2500,3000,3500]:
  for B0 in [300,500,700,900]:
    r=least_squares(lambda p:lev(*p)[1:4]-obs,[D0,B0])
    best.append((r.cost,r.x))
best.sort(key=lambda t:t[0])
for b in best[:6]:print(b, np.round(lev(*b[1])[:6]))
E
python3 b.py
