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
    return sum(F[k]*(-1)**q*C(k,q,ma,mc)*C(k,-q,mb,md) for k in (0,2,4) for q in range(-k,k+1))
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
def apply_1(i,j,st):
    if j not in st: return None
    lst=list(st); pos=lst.index(j); sgn=(-1)**pos; lst.pop(pos)
    if i in lst: return None
    pos=sum(1 for x in lst if x<i); sgn*=(-1)**pos; lst.insert(pos,i)
    return sgn,tuple(lst)
E5=np.eye(5)
eg=[E5[2],(E5[4]+E5[0])/np.sqrt(2)]
t2=[(E5[3]+E5[1])/np.sqrt(2),(E5[3]-E5[1])/np.sqrt(2),(E5[4]-E5[0])/np.sqrt(2)]
def ops(F,Dq):
    h=sum(6*Dq*np.outer(v,v) for v in eg)+sum(-4*Dq*np.outer(v,v) for v in t2)
    Vt=np.zeros((N,N,N,N))
    for a,(ma,sa) in enumerate(so):
      for b,(mb,sb) in enumerate(so):
        for c,(mc,sc) in enumerate(so):
          for d,(md,sd) in enumerate(so):
            if sa!=sc or sb!=sd: continue
            Vt[a,b,c,d]=Vsp(ma,mb,mc,md,F)
    n=len(basis); H=np.zeros((n,n))
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
ms=[sum(so[i][1] for i in st) for st in basis]
up=[k for k,m in enumerate(ms) if m==1]
def levels(B,Cc,Dq):
    F={0:0.0,2:49*B+7*Cc,4:12.6*Cc}
    H=ops(F,Dq)
    T=np.linalg.eigvalsh(H[np.ix_(up,up)])
    Hf=np.linalg.eigvalsh(H)
    rest=list(Hf)
    for t in T:
        for _ in range(3):
            i=int(np.argmin([abs(x-t) for x in rest])); rest.pop(i)
    return T, np.array(sorted(rest))
def residual(x):
    Dq,B,Cc=x
    T,S=levels(B,Cc,Dq)
    E0=T.min()
    T3T2=sorted(set(np.round(T,3)))
    # 3T2 = triplet level with multiplicity 3, not ground; 3T1P = highest 3-fold triplet below A2
    tv=[t for t in T3T2]
    # levels: ground 3T1F (lowest), then 3T2, 3T1P (multiplicity 3), 3A2 (mult 1)
    trip3=[t for t in tv if np.sum(np.abs(T-t)<1e-3)==3]
    t3=trip3  # sorted ascending
    E_3T2=t3[1]; E_3T1P=t3[2]
    # 1E = lowest doublet singlet
    S_r=np.round(S,3)
    doub=[s for s in sorted(set(S_r)) if np.sum(np.abs(S-s)<1e-2)==2]
    E_1E=doub[0]
    return np.array([E_3T2-E0-17500, E_3T1P-E0-25000, E_1E-E0-9748]), (E_3T2-E0,E_3T1P-E0,E_1E-E0)
sol=fsolve(lambda x: residual(x)[0], [1750,700,3000], xtol=1e-10)
print("solution Dq,B,C:", np.round(sol,2))
print("check residual & energies:", residual(sol))
print("Dq-only ground check:", levels(700,3000,1750)[0])
