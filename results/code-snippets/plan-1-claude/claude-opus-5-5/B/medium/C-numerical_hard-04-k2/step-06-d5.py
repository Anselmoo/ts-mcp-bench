import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float((-1)**m*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m,q,mp))
C={k:{(a,b):ck(k,a,b) for a in ms for b in ms} for k in (2,4)}
so=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(1 if so[i][1]==0 else -1 for i in d)==1]
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def V2(i,j,k,l,F):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[i],so[j],so[k],so[l]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.0
    return sum(C[k_][(m1,m3)]*C[k_][(m4,m2)]*F[k_] for k_ in (2,4))
def sgn(lst,x): return (-1)**sum(1 for y in lst if y<x)
cf=np.zeros((5,5))
for a in ms: cf[a+2,a+2]={0:6,1:-4,-1:-4,2:1,-2:1}[a]
cf[4,0]=cf[0,4]=5
def build(F):
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        occ=list(d)
        for a,b in itertools.combinations(occ,2):
            rest=[x for x in occ if x not in (a,b)]
            for c,e in itertools.combinations(range(10),2):
                if c in rest or e in rest: continue
                val=V2(c,e,a,b,F)-V2(c,e,b,a,F)
                if abs(val)<1e-12: continue
                l1=occ[:]; s=sgn(l1,a); l1.remove(a); s*=sgn(l1,b); l1.remove(b)
                s*=sgn(l1,e); l1.append(e); l1.sort(); s*=sgn(l1,c); l1.append(c); l1.sort()
                H[idx[tuple(l1)],I]+=s*val
    return H
def build1(M):
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        occ=list(d)
        for a in occ:
            for c in range(10):
                if so[c][1]!=so[a][1]: continue
                v=M[so[c][0]+2,so[a][0]+2]
                if abs(v)<1e-12: continue
                if c!=a and c in occ: continue
                l1=occ[:]; s=sgn(l1,a); l1.remove(a)
                s*=sgn(l1,c); l1.append(c); l1.sort()
                H[idx[tuple(l1)],I]+=s*v
    return H
H2=build({2:1.0,4:0.0}); H4=build({2:0.0,4:1.0}); HD=build1(cf)
dets3=[d for d in itertools.combinations(range(10),5) if sum(1 if so[i][1]==0 else -1 for i in d)==3]
idx3={d:i for i,d in enumerate(dets3)}
Sp=np.zeros((len(dets3),N))
for I,d in enumerate(dets):
    occ=list(d)
    for a in occ:
        if so[a][1]==1:
            c=a-1
            if c in occ: continue
            l1=occ[:]; s=sgn(l1,a); l1.remove(a); s*=sgn(l1,c); l1.append(c); l1.sort()
            Sp[idx3[tuple(l1)],I]+=s
S2=Sp.T@Sp+0.75
np.save('m.npy',np.array([H2,H4,HD,S2]))
