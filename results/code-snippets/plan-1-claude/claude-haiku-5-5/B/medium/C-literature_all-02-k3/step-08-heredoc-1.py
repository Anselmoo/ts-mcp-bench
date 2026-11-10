import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve
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
def apply_1(i,j,st):
    if j not in st: return None
    lst=list(st); pos=lst.index(j); sgn=(-1)**pos; lst.pop(pos)
    if i in lst: return None
    pos=sum(1 for x in lst if x<i); sgn*=(-1)**pos; lst.insert(pos,i)
    return sgn,tuple(lst)
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
def build(F,Dq):
    n=len(basis); H=np.zeros((n,n))
    h=np.zeros((5,5)); E=np.eye(5)
    eg=[E[2],(E[4]+E[0])/np.sqrt(2)]
    t2=[(E[3]+E[1])/np.sqrt(2),(E[3]-E[1])/np.sqrt(2),(E[4]-E[0])/np.sqrt(2)]
    for v in eg: h+=6*Dq*np.outer(v,v)
    for v in t2: h+=-4*Dq*np.outer(v,v)
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
            for i in range(N):
                for j in range(N):
                    if so[i][1]!=so[j][1]: continue
                    hij=h[so[i][0]+2,so[j][0]+2]
                    if abs(hij)<1e-14: continue
                    r=apply_1(i,j,st)
                    if r and r[1]==bra: val+=hij*r[0]
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
def FF(B,C): return {0:0.0,2:49*B+7*C,4:12.6*C}
def levels(Dq,B,C): return np.linalg.eigvalsh(build(FF(B,C),Dq))
ev=levels(0.0,1.0,4.0); print("free ion B=1,C=4:", np.unique(np.round(ev,4),return_counts=True))
