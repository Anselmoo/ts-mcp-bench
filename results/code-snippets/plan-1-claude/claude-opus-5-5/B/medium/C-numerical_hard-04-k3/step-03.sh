
cat << 'EOF' | python3
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def cgaunt(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*gaunt(2,k,2,-m1,q,m2)*np.sqrt(4*np.pi/(2*k+1)))
CK={k:{(a,b):cgaunt(k,a,b) for a in ms for b in ms} for k in (2,4)}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5)); idx={d:i for i,d in enumerate(dets)}
def eri(a,b,c,d,F2,F4):
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]: return 0.0
    return F2*CK[2][(a[0],c[0])]*CK[2][(d[0],b[0])]+F4*CK[4][(a[0],c[0])]*CK[4][(d[0],b[0])]
def add(lst,x):
    k=sum(1 for y in lst if y<x); l=list(lst); l.insert(k,x); return l,(-1)**k
# precompute matrices for unit Dq, F2, F4
N=len(dets); HV=np.zeros((N,N)); H2=np.zeros((N,N)); H4=np.zeros((N,N))
V=np.zeros((5,5)); V[2,2]=6;V[1,1]=V[3,3]=-4;V[0,0]=V[4,4]=1;V[0,4]=V[4,0]=5
for I,d in enumerate(dets):
    for i,p in enumerate(d):
        rest=[x for x in d if x!=p]
        for q in range(10):
            if so[p][1]!=so[q][1] or (q in rest): continue
            v=V[ms.index(so[q][0]),ms.index(so[p][0])]
            if v==0: continue
            new,s=add(rest,q); HV[idx[tuple(new)],I]+=(-1)**i*s*v
    for i1 in range(5):
        for i2 in range(i1+1,5):
            p,q=d[i1],d[i2]; rest=[x for x in d if x not in (p,q)]
            s0=(-1)**(i1+i2-1)
            for r in range(10):
                for s in range(r+1,10):
                    if r in rest or s in rest: continue
                    a=[eri(so[r],so[s],so[p],so[q],*f)-eri(so[r],so[s],so[q],so[p],*f) for f in ((1,0),(0,1))]
                    if abs(a[0])+abs(a[1])<1e-12: continue
                    n1,g1=add(rest,s); n2,g2=add(n1,r)
                    J=idx[tuple(n2)]; H2[J,I]+=s0*g1*g2*a[0]; H4[J,I]+=s0*g1*g2*a[1]
# S^2 operator
Sz=np.array([sum(0.5 if so[x][1]==0 else -0.5 for x in d) for d in dets])
Sp=np.zeros((N,N))
for I,d in enumerate(dets):
    for i,p in enumerate(d):
        if so[p][1]==1:
            q=p-1
            if q in d: continue
            rest=[x for x in d if x!=p]; new,s=add(rest,q); Sp[idx[tuple(new)],I]+=(-1)**i*s
S2=Sp.T@Sp+np.diag(Sz**2+Sz)  # S-S+ + Sz^2+Sz ... S^2=S-S+ + Sz^2 + Sz
def levels(Dq,B,C):
    F4=C/35; F2=B+5*F4
    H=Dq*HV+49*F2*H2+441*F4*H4
    w,U=np.linalg.eigh(H)
    s2=np.einsum('ij,jk,ki->i',U.T,S2,U)
    out=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<1e-3: j+=1
        S=(-1+np.sqrt(1+4*np.mean(s2[i:j])))/2
        out.append((w[i],j-i,round(S,2))); i=j
    return out
L=levels(2800,500,2200)
E0=L[0][0]
for e,g,S in L[:15]: print(round(e-E0),g,S)
import pickle,sys
np.savez('/dev/shm/m.npz',HV=HV,H2=H2,H4=H4,S2=S2) if False else None
obs=np.array([29360,29620,31640])
def doub(Dq,B):
    L=levels(Dq,B,4.4*B); E0=L[0][0]
    assert L[0][2]==0.5
    return [ (e-E0,g) for e,g,S in L[1:] if S==0.5]
def res(x):
    d=doub(*x); return np.array([d[i][0] for i in range(3)])-obs
for g in [(2500,400),(3000,500),(3500,600),(4000,300)]:
    r=least_squares(res,g,diff_step=1e-4); print(r.x,r.fun,doub(*r.x)[:4])
EOF