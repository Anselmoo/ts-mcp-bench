cd <SANDBOX_TMP>
cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=706.,2734.
F={2:B+C/7,4:C/35}
cc_={}
def c(k,m,mp):
    if abs(m-mp)>k: return 0.
    key=(k,m,mp)
    if key not in cc_: cc_[key]=float((-1)**m*5*gaunt(2,k,2,-m,m-mp,mp))
    return cc_[key]
orb=[(m,s) for m in range(-2,3) for s in (0,1)]
def Vv(a,b,cd,d):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=a,b,cd,d
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.
    return sum(F[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
Vt={}
for p in range(10):
  for q in range(10):
    for r in range(10):
      for s in range(10):
        v=Vv(orb[p],orb[q],orb[r],orb[s])
        if abs(v)>1e-12: Vt[(p,q,r,s)]=v
def hmat(Dq):
    h=np.zeros((10,10))
    for i,(m,s) in enumerate(orb):
        for j,(mp,sp) in enumerate(orb):
            if s!=sp: continue
            if m==mp: h[i,j]=6*Dq if m==0 else (-4*Dq if abs(m)==1 else Dq)
            elif abs(m)==2 and mp==-m: h[i,j]=5*Dq
    return h
def sgn(l):
    return (-1)**sum(1 for a in range(len(l)) for b in range(a+1,len(l)) if l[a]>l[b])
def ann(l,x):
    return [y for y in l if y!=x],(-1)**l.index(x)
def cre(l,x):
    if x in l: return None,0
    nl=[x]+l
    return sorted(nl),sgn(nl)
def gs(Dq,Ms2,ret=False):
    dets=[d for d in itertools.combinations(range(10),4) if sum(1 if orb[i][1]==0 else -1 for i in d)==Ms2]
    idx={d:i for i,d in enumerate(dets)};N=len(dets);H=np.zeros((N,N));h=hmat(Dq)
    for d in dets:
        i=idx[d]
        for q in d:
            for p in range(10):
                if h[p,q]==0: continue
                l,s1=ann(list(d),q);l2,s2=cre(l,p)
                if l2 is None: continue
                H[idx[tuple(l2)],i]+=h[p,q]*s1*s2
        for (p,q,r,s),v in Vt.items():
            if r not in d or s not in d or r==s: continue
            l,s1=ann(list(d),r)
            l,s2=ann(l,s)
            l,s3=cre(l,q)
            if l is None: continue
            l,s4=cre(l,p)
            if l is None: continue
            H[idx[tuple(l)],i]+=0.5*v*s1*s2*s3*s4
    assert np.allclose(H,H.T,atol=1e-6)
    return np.linalg.eigvalsh(H)[0]
f=lambda Dq:gs(Dq,4)-gs(Dq,2)
for D in (1000,2000,3000):print(D,f(D))
print(brentq(f,500,4000,xtol=0.01))
E
python3 a.py