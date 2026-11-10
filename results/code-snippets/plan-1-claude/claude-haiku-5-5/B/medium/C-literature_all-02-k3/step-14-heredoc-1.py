import numpy as np, itertools, time
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve
t0=time.time()
l=2
so=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
N=len(so)
def C(k,q,ma,mc):
    if ma-q!=mc: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-ma)*float(wigner_3j(l,k,l,-ma,q,mc))*red
def Vsp(ma,mb,mc,md,F):
    return sum(F[k]*(-1)**q*C(k,q,ma,mc)*C(k,-q,mb,md) for k in (0,2,4) for q in range(-k,k+1))
basis=list(itertools.combinations(range(N),2))
bidx={b:i for i,b in enumerate(basis)}
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
def apply_1(i,j,st):
    if j not in st: return None
    lst=list(st); pos=lst.index(j); sgn=(-1)**pos; lst.pop(pos)
    if i in lst: return None
    pos=sum(1 for x in lst if x<i); sgn*=(-1)**pos; lst.insert(pos,i)
    return sgn,tuple(lst)
E5=np.eye(5)
eg=[E5[2],(E5[4]+E5[0])/np.sqrt(2)]
t2=[(E5[3]+E5[1])/np.sqrt(2),(E5[3]-E5[1])/np.sqrt(2),(E5[4]-E5[0])/np.sqrt(2)]
h_cf=sum(6*np.outer(v,v) for v in eg)+sum(-4*np.outer(v,v) for v in t2)
n=len(basis)
# one-body matrix
H1=np.zeros((n,n))
for J,st in enumerate(basis):
  for i in range(N):
    for j in range(N):
      if so[i][1]!=so[j][1]: continue
      hij=h_cf[so[i][0]+2,so[j][0]+2]
      if abs(hij)<1e-14: continue
      r=apply_1(i,j,st)
      if r and r[1] in bidx: H1[bidx[r[1]],J]+=hij*r[0]
# two-body for k=2 and k=4 separately
def H2body(F):
    Vt=np.zeros((N,N,N,N))
    for a,(ma,sa) in enumerate(so):
      for b,(mb,sb) in enumerate(so):
        for c,(mc,sc) in enumerate(so):
          for d,(md,sd) in enumerate(so):
            if sa!=sc or sb!=sd: continue
            Vt[a,b,c,d]=Vsp(ma,mb,mc,md,F)
    H=np.zeros((n,n))
    for J,st in enumerate(basis):
      for a,b,c,d in itertools.product(range(N),repeat=4):
        v=Vt[a,b,c,d]
        if abs(v)<1e-14: continue
        r=apply_2(a,b,c,d,st)
        if r and r[1] in bidx: H[bidx[r[1]],J]+=0.5*v*r[0]
    return H
H2=H2body({0:0,2:1,4:0}); H4=H2body({0:0,2:0,4:1})
np.savez('/tmp/mats.npz',H1=H1,H2=H2,H4=H4,ms=np.array([sum(so[i][1] for i in st) for st in basis]))
print("built", time.time()-t0)
