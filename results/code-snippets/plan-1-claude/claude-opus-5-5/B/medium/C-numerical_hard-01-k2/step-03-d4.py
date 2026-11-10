import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
# ck(l=2,m1,l=2,m2) = sqrt(4pi/(2k+1)) * gaunt
import math
def ck(k,m1,m2):
    # <2 m1|C^k_{m1-m2}|2 m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*math.sqrt(4*math.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def R(a,b,c,d,F):
    # <ab|1/r|cd>, a,c electron1
    if a+b!=c+d: return 0.0
    return sum(F[k]*CK[(k,a,c)]*CK[(k,d,b)] for k in (0,2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),4))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5; F={0:0,2:F2,4:F4}
    V=np.zeros((5,5)); 
    dm={-2:Dq,-1:-4*Dq,0:6*Dq,1:-4*Dq,2:Dq}
    for m in ms: V[m+2,m+2]=dm[m]
    V[0,4]=V[4,0]=5*Dq
    N=len(dets); H=np.zeros((N,N))
    for i,d in enumerate(dets):
        occ=list(d)
        # one-body
        for p_i,p in enumerate(occ):
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[so[q][0]+2,so[p][0]+2]
                if v==0: continue
                if q!=p and q in occ: continue
                new=occ.copy(); new[p_i]=q
                sign=1
                # sort with sign
                arr=new[:]
                for a in range(len(arr)):
                    for b in range(len(arr)-1-a):
                        if arr[b]>arr[b+1]: arr[b],arr[b+1]=arr[b+1],arr[b]; sign=-sign
                H[idx[tuple(arr)],i]+=sign*v
        # two-body
        for (ia,a),(ib,b) in itertools.combinations(enumerate(occ),2):
            for c in range(10):
                for e in range(10):
                    if c==e: continue
                    if so[c][1]!=so[a][1] or so[e][1]!=so[b][1]: continue
                    val=R(so[c][0],so[e][0],so[a][0],so[b][0],F)
                    if abs(val)<1e-12: continue
                    new=occ.copy()
                    rest=[x for x in occ if x not in (a,b)]
                    if c in rest or e in rest: continue
                    new[ia]=c; new[ib]=e
                    arr=new[:]; sign=1
                    for x in range(len(arr)):
                        for y in range(len(arr)-1-x):
                            if arr[y]>arr[y+1]: arr[y],arr[y+1]=arr[y+1],arr[y]; sign=-sign
                    H[idx[tuple(arr)],i]+=sign*val
    return H
# Sz=1 sector: count spin up(0) minus down
def sz(d): return sum(1 if so[x][1]==0 else -1 for x in d)/2
def levels(Dq,B,C):
    H=build(Dq,B,C); H=(H+H.T)/2
    e=np.linalg.eigvalsh(H)
    # spin: get triplets by Sz sectors: triplet energies = in Sz=1 but not Sz=2
    sel1=[i for i,d in enumerate(dets) if sz(d)==1]
    sel2=[i for i,d in enumerate(dets) if sz(d)==2]
    e1=np.linalg.eigvalsh(H[np.ix_(sel1,sel1)]); e2=np.linalg.eigvalsh(H[np.ix_(sel2,sel2)])
    e0=np.linalg.eigvalsh(H[np.ix_([i for i,d in enumerate(dets) if sz(d)==0],)*2])
    return e0,e1,e2
