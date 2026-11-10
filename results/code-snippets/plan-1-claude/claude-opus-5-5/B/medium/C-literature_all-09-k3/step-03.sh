cd <SANDBOX_TMP>/tmp.wzseEn6RP2; cat << 'EOF' > d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
l=2
C={}
for k in (0,2,4):
  for a in range(-2,3):
    for b in range(-2,3):
      C[(k,a,b)]=float((-1)**a*np.sqrt(4*np.pi/(2*k+1))*5*gaunt(2,k,2,-a,a-b,b))
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(orbs[i][1] for i in d)==4]
idx={d:i for i,d in enumerate(dets)}
def g(i,j,k,l_,Fk):
    (mi,si),(mj,sj),(mk,sk),(ml,sl)=orbs[i],orbs[j],orbs[k],orbs[l_]
    if si!=sk or sj!=sl or mi+mj!=mk+ml: return 0.0
    return sum(C[(k_,mi,mk)]*C[(k_,ml,mj)]*Fk[k_] for k_ in (2,4))
def apply(d,ann,cre):
    lst=list(d); sg=1
    for a in ann:
        if a not in lst: return None,0
        i=lst.index(a); sg*=(-1)**i; lst.pop(i)
    for c in cre:
        if c in lst: return None,0
        pos=sum(1 for x in lst if x<c); sg*=(-1)**pos; lst.insert(pos,c)
    return tuple(lst),sg
def build(Dq,B,Cc):
    Fk={2:49*(B+Cc/7),4:441*Cc/35}
    V=np.zeros((5,5))
    for m in range(-2,3): V[m+2,m+2]={0:6,1:-4,2:1}[abs(m)]*Dq
    V[4,0]=V[0,4]=5*Dq
    n=len(dets);H=np.zeros((n,n))
    for d in dets:
        I=idx[d]
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[orbs[q][0]+2,orbs[p][0]+2]
                if v==0: continue
                nd,sg=apply(d,[p],[q])
                if nd: H[idx[nd],I]+=v*sg
        for p,q in itertools.combinations(d,2):
            for r,s in itertools.combinations(range(10),2):
                v=g(r,s,p,q,Fk)-g(r,s,q,p,Fk)
                if abs(v)<1e-12: continue
                nd,sg=apply(d,[q,p],[s,r])
                if nd: H[idx[nd],I]+=v*sg
    return H
def lv(Dq,B,Cc):
    w=np.linalg.eigvalsh(build(Dq,B,Cc)); return w-w[0]
w=lv(0,1,0); print(np.round(w,3))
w=lv(0,0,1); print(np.round(w,3))
def f(x):
    w=lv(*x)
    return [w[1]-19720,w[4]-23260,w[7]-24980]
for g0 in ([800,800,3000],[700,900,3200],[900,700,3300]):
    s=fsolve(f,g0); print(s, np.round(lv(*s)[:12],1))
EOF
python3 d5.py