cd $TMPDIR && python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=list(range(-2,3))
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
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
    H=Dq*HV+(49*B+7*Cr)*H2+(441*Cr/35)*H4
    w,v=np.linalg.eigh(H); s=np.einsum('ji,jk,ki->i',v,SS,v)
    q=[x-w[0] for x,si in zip(w,s) if abs(si-3.75)<0.1]
    out=[]
    for x in q:
        if not out or x-out[-1][0]>1e-3: out.append([x,1])
        else: out[-1][1]+=1
    return [(round(a,1),n) for a,n in out]
def res(x): q=levels(*x); return [q[0][0]-19720,q[1][0]-23260,q[2][0]-24980]
r=least_squares(res,[800,800,3200],diff_step=1e-4); print(r.x,res(r.x)); print(levels(*r.x)[:6])
EOF