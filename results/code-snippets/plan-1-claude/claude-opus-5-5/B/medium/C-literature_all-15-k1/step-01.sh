
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
# c^k(m1,m2)
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5*gaunt(2,k,2,-m1,m1-m2,m2)) if abs(m1-m2)<=k else 0.
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def g(a,b,c,d,F): # <ab|1/r|cd>
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]: return 0
    return sum(F[k]*C[(k,a[0],c[0])]*C[(k,d[0],b[0])] for k in (0,2,4))
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def build(F):
    H=np.zeros((N,N))
    for i,D in enumerate(dets):
        # two-body: apply a+_p a+_q a_s a_r
        for r,s in itertools.combinations(D,2):
            for p in range(10):
                for q in range(10):
                    if p==q: continue
                    val=g(so[p],so[q],so[r],so[s],F)-g(so[p],so[q],so[s],so[r],F)
                    if val==0: continue
                    # annihilate s then r, create q then p
                    L=list(D); sign=1
                    for o in (s,r):
                        k=L.index(o); sign*=(-1)**k; L.pop(k)
                    ok=True
                    for o in (q,p):
                        if o in L: ok=False;break
                        k=sum(1 for x in L if x<o); sign*=(-1)**k; L.insert(k,o)
                    if not ok: continue
                    # p<q double counting: sum over ordered p,q gives factor 1/2 * 2 with antisym pairs-> use 0.5
                    H[idx[tuple(L)],i]+=0.5*sign*val
    return H
def cf():
    v=np.zeros((5,5))
    for i,m in enumerate(ms): v[i,i]={0:6,1:-4,2:1}[abs(m)]
    v[0,4]=v[4,0]=5
    V=np.zeros((N,N))
    for i,D in enumerate(dets):
        for r in D:
            for p in range(10):
                if so[p][1]!=so[r][1]: continue
                val=v[ms.index(so[p][0]),ms.index(so[r][0])]
                if val==0: continue
                L=list(D);k=L.index(r);sign=(-1)**k;L.pop(k)
                if p in L: continue
                k=sum(1 for x in L if x<p);sign*=(-1)**k;L.insert(k,p)
                V[idx[tuple(L)],i]+=sign*val
    return V
V=cf()
# F2=49B+... with C: F4=441C/35 ; F2 = 49(B+5F4/441)=49B+7C
H2=build({0:0,2:49.,4:0}); H4=build({0:0,2:0,4:1.})
HB=49*H2; HC=7*H2+(441/35)*H4
Sz=np.diag([sum(1 if so[o][1] else -1 for o in D)/2 for D in dets])
S2off=None
# S^2 via S-S+ + Sz^2+Sz
Sp=np.zeros((N,N))
for i,D in enumerate(dets):
    for o in D:
        if so[o][1]==0:
            p=o+1
            if p in D: continue
            L=list(D);k=L.index(o);sign=(-1)**k;L.pop(k)
            k=sum(1 for x in L if x<p);sign*=(-1)**k;L.insert(k,p)
            Sp[idx[tuple(L)],i]+=sign
S2=Sp.T@Sp+Sz@Sz+Sz
C4=np.diag([np.prod([np.exp(-1j*so[o][0]*np.pi/2) for o in D]) for D in dets])
np.save('/tmp/m.npy',np.array([HB,HC,V,S2]));np.save('/tmp/c4.npy',C4)
EOF
python3 /tmp/d7.py && echo ok
