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
H1=np.zeros((n,n))
for J,st in enumerate(basis):
  for i in range(N):
    for j in range(N):
      if so[i][1]!=so[j][1]: continue
      hij=h_cf[so[i][0]+2,so[j][0]+2]
      if abs(hij)<1e-14: continue
      r=apply_1(i,j,st)
      if r and r[1] in bidx: H1[bidx[r[1]],J]+=hij*r[0]
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
ms=np.array([sum(so[i][1] for i in st) for st in basis])
up=np.where(ms==1)[0]
print("built", round(time.time()-t0,1), flush=True)
def H(Dq,B,Cc):
    return Dq*H1+(49*B+7*Cc)*H2+12.6*Cc*H4
def levels(Dq,B,Cc):
    M=H(Dq,B,Cc)
    T=np.linalg.eigvalsh(M[np.ix_(up,up)])
    rest=list(np.linalg.eigvalsh(M))
    for t in T:
        for _ in range(3):
            i=int(np.argmin([abs(x-t) for x in rest])); rest.pop(i)
    return T,np.array(rest)
def classify(Dq,B,Cc):
    T,S=levels(Dq,B,Cc)
    tv=sorted(set(np.round(T,2)))
    trip3=[t for t in tv if np.sum(np.abs(T-t)<1e-2)==3]
    E0=trip3[0]
    sd=sorted(set(np.round(S,2)))
    dbl=[s for s in sd if np.sum(np.abs(S-s)<1e-1)==2]
    return E0,trip3,dbl,T,S
def resid(x):
    Dq,B,Cc=x
    E0,trip3,dbl,T,S=classify(Dq,B,Cc)
    return np.array([trip3[1]-E0-17500, trip3[2]-E0-25000, dbl[0]-E0-9748])
print("start guess check:", classify(1750,700,3000)[1:3])
sol=fsolve(resid,[1750,700,3000],xtol=1e-12)
print("Dq,B,C =",np.round(sol,2))
print("residuals",resid(sol))
E0,trip3,dbl,T,S=classify(*sol)
print("triplets (Ms=1 mult3):",np.round(np.array(trip3)-E0,1)," A2 level:",np.round(sorted(set(np.round(T,2))),1))
print("singlet doublets:",np.round(np.array(dbl)-E0,1))
print("time",round(time.time()-t0,1))
