import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
# real d orbitals via complex m basis; build d5 Hamiltonian in complex basis
ms=[-2,-1,0,1,2]
# Slater integrals: F0 irrelevant, F2=49F2', F4=441F4'; B=F2'-5F4', C=35F4'
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(0)) if False else None
from sympy import S
def cgaunt(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * <Y_l m1| Y_k (m1-m2) | Y_l m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    val=(-1)**m1*gaunt(2,k,2,-m1,q,m2)
    return float(val*np.sqrt(4*np.pi/(2*k+1)))
CK={k:{(a,b):cgaunt(k,a,b) for a in ms for b in ms} for k in (0,2,4)}
def Fk(B,C):
    F4p=C/35; F2p=B+5*F4p
    return {0:0.0,2:49*F2p,4:441*F4p}
# two-electron integral <ab|1/r|cd> spin-orbitals (m,s)
def eri(a,b,c,d,F):
    if a[1]!=c[1] or b[1]!=d[1]: return 0.0
    if a[0]+b[0]!=c[0]+d[0]: return 0.0
    return sum(F[k]*CK[k][(a[0],c[0])]*CK[k][(d[0],b[0])] for k in (2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
# crystal field octahedral in m basis: Dq*(6 for m=0, -4 for ±1, m=±2 :1, and <2|V|-2>=5)
def Vcf(Dq):
    V=np.zeros((5,5))
    V[2,2]=6;V[1,1]=V[3,3]=-4;V[0,0]=V[4,4]=1;V[0,4]=V[4,0]=5
    return V*Dq
def build(Dq,B,C):
    F=Fk(B,C);V=Vcf(Dq);N=len(dets);H=np.zeros((N,N))
    for I,d in enumerate(dets):
        # one-body
        for p in d:
            for q in range(10):
                if so[p][1]!=so[q][1]: continue
                v=V[ms.index(so[q][0]),ms.index(so[p][0])]
                if v==0: continue
                if q!=p and q in d: continue
                new=list(d); pos=new.index(p); 
                sgn=(-1)**pos; new.pop(pos)
                # insert q
                k=sum(1 for x in new if x<q); new.insert(k,q); sgn*=(-1)**k
                H[idx[tuple(new)],I]+=sgn*v
        # two-body: sum_{p<q in d} sum_{r<s} <rs||pq> a_r+ a_s+ a_q a_p
        for i1 in range(5):
            for i2 in range(i1+1,5):
                p,q=d[i1],d[i2]
                rest=[x for x in d if x not in (p,q)]
                sgn0=(-1)**(i1+i2-1)
                for r in range(10):
                    for s in range(r+1,10):
                        if (r in rest) or (s in rest): continue
                        v=eri(so[r],so[s],so[p],so[q],F)-eri(so[r],so[s],so[q],so[p],F)
                        if abs(v)<1e-12: continue
                        new=list(rest)
                        k=sum(1 for x in new if x<s); new.insert(k,s); sg=(-1)**k
                        k2=sum(1 for x in new if x<r); new.insert(k2,r); sg*=(-1)**k2
                        H[idx[tuple(new)],I]+=sgn0*sg*v
    return H
# S^2 to label spins
def spins(Dq,B,C):
    H=build(Dq,B,C); w,U=np.linalg.eigh(H)
    # compute Ms=1/2 only? use S^2 via degeneracy count approx: compute S^2 operator
    return w,U
import pickle
