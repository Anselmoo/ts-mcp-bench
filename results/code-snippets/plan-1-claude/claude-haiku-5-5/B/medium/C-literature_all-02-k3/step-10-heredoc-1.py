import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2
so=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
N=len(so)
def C(k,q,ma,mc):
    if ma-q!=mc: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-ma)*float(wigner_3j(l,k,l,-ma,q,mc))*red
def Vsp(ma,mb,mc,md,F):
    tot=0.0
    for k in (0,2,4):
        for q in range(-k,k+1):
            tot+=F[k]*(-1)**q*C(k,q,ma,mc)*C(k,-q,mb,md)
    return tot
basis=list(itertools.combinations(range(N),2))
def apply_2(a,b,c,d,st):
    lst=list(st)
    if c not in lst: return None
    pos=lst.index(c); sgn=(-1)**pos; lst.pop(pos)
    if d not in lst: return None
    pos=lst.index(d); sgn*=(-1)**pos; lst.pop(pos)
    if b in lst: return None
    pos=sum(1 for x in lst if x<b); sgn*=(-1)**pos; lst.insert(pos,b)
    if a in lst: return None
    pos=sum(1 for x in lst if x<a); sgn*=(-1)**pos; lst.insert(pos,a)
    return sgn,tuple(lst)
def build(F):
    n=len(basis); H=np.zeros((n,n))
    Vt=np.zeros((N,N,N,N))
    for a,(ma,sa) in enumerate(so):
      for b,(mb,sb) in enumerate(so):
        for c,(mc,sc) in enumerate(so):
          for d,(md,sd) in enumerate(so):
            if sa!=sc or sb!=sd: continue
            Vt[a,b,c,d]=Vsp(ma,mb,mc,md,F)
    for J,st in enumerate(basis):
        for I,bra in enumerate(basis):
            val=0.0
            for a in range(N):
              for b in range(N):
                for c in range(N):
                  for d in range(N):
                    v=Vt[a,b,c,d]
                    if abs(v)<1e-14: continue
                    r=apply_2(a,b,c,d,st)
                    if r and r[1]==bra: val+=0.5*v*r[0]
            H[I,J]=val
    return H
for F in [{0:1,2:0,4:0},{0:0,2:1,4:0},{0:0,2:0,4:1}]:
    H=build(F); ev=np.linalg.eigvalsh(H)
    print(F, np.unique(np.round(ev,4),return_counts=True), "trace",round(np.trace(H),4))
