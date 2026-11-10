cd $TMPDIR && python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=list(range(-2,3))
def c(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
C={(k,a,b):c(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5)); idx={d:i for i,d in enumerate(dets)}
def apply(occ,ann,cre):
    occ=list(occ);sg=1
    for x in ann:
        if x not in occ: return None,0
        p=occ.index(x);sg*=(-1)**p;occ.pop(p)
    for x in cre:
        if x in occ: return None,0
        p=sum(1 for y in occ if y<x);sg*=(-1)**p;occ.insert(p,x)
    return tuple(occ),sg
N=len(dets)
# precompute matrices for Dq, F2, F4
HV=np.zeros((N,N));H2=np.zeros((N,N));H4=np.zeros((N,N));SS=np.zeros((N,N))
V=np.zeros((5,5))
for i,m in enumerate(ms): V[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
V[0,4]=V[4,0]=5
for d in dets:
    i=idx[d]
    for p in d:
        for q in range(10):
            if so[q][1]!=so[p][1]: continue
            v=V[ms.index(so[q][0]),ms.index(so[p][0])]
            if v==0: continue
            o,sg=apply(d,[p],[q])
            if o: HV[idx[o],i]+=sg*v
    for a,b in itertools.permutations(d,2):
        for cc in range(10):
            for dd in range(10):
                (m1,s1),(m2,s2)=so[a],so[b];(m3,s3),(m4,s4)=so[cc],so[dd]
                if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
                o,sg=apply(d,[a,b],[dd,cc])
                if not o: continue
                for k,Hk in ((2,H2),(4,H4)):
                    Hk[idx[o],i]+=0.5*sg*C[(k,m3,m1)]*C[(k,m2,m4)]
    sz=sum(0.5 if so[p][1]==0 else -0.5 for p in d)
    SS[i,i]+=sz*sz+sz
    for p in d:
        if so[p][1]==1:
            o,sg=apply(d,[p],[p-1])
            if not o: continue
            for p2 in o:
                if so[p2][1]==0:
                    o2,s2=apply(o,[p2],[p2+1])
                    if o2: SS[idx[o2],i]+=sg*s2
def levels(Dq,B,Cr):
    F2=49*B+7*Cr;F4=441*Cr/35
    H=Dq*HV+F2*H2+F4*H4
    w,v=np.linalg.eigh(H); s=np.einsum('ji,jk,ki->i',v,SS,v)
    gs=w[0]
    q=sorted(set(round(x-gs,2) for x,si in zip(w,s) if abs(si-3.75)<0.1))
    return q, round(s[0],2)
print(levels(0,800,3200), 10*800+5*3200)
print(levels(800,800,3200))
def res(x): q,_=levels(*x); return [q[0]-19720,q[1]-23260,q[2]-24980]
r=least_squares(res,[800,800,3200]); print(r.x,res(r.x)); print(levels(*r.x))
EOF