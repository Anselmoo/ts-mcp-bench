mkdir -p /w && cd /w && cat > d5.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5*gaunt(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms if abs(a-b)<=k}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5)); idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply2(det,p,q,r,s):  # a+_p a+_q a_s a_r
    d=list(det); sign=1
    for op,orb in (('a',r),('a',s),('c',q),('c',p)):
        if op=='a':
            if orb not in d: return None,0
            i=d.index(orb); sign*=(-1)**i; d.pop(i)
        else:
            if orb in d: return None,0
            i=sum(1 for x in d if x<orb); sign*=(-1)**i; d.insert(i,orb)
    return tuple(d),sign
def build(F):
    H=np.zeros((N,N))
    for i,det in enumerate(dets):
        for p in range(10):
            for q in range(10):
                for r in range(10):
                    for s in range(10):
                        mp,sp=so[p];mq,sq=so[q];mr,sr=so[r];ms_,ss=so[s]
                        if sp!=sr or sq!=ss or mp+mq!=mr+ms_: continue
                        v=sum(C.get((k,mp,mr),0)*C.get((k,ms_,mq),0)*F[k] for k in (2,4))
                        if v==0: continue
                        nd,sg=apply2(det,p,q,r,s)
                        if nd is None: continue
                        H[idx[nd],i]+=0.5*sg*v
    return H
H2=build({2:1,4:0}); H4=build({2:0,4:1})
V=np.zeros((5,5)); 
for m,v in zip(ms,[1,-4,6,-4,1]): V[ms.index(m),ms.index(m)]=v
V[0,4]=V[4,0]=5
HV=np.zeros((N,N))
for i,det in enumerate(dets):
    for a in det:
        for b in range(10):
            if so[a][1]!=so[b][1]: continue
            v=V[ms.index(so[b][0]),ms.index(so[a][0])]
            if v==0: continue
            d=list(det); ia=d.index(a); sg=(-1)**ia; d.pop(ia)
            if b in d: continue
            ib=sum(1 for x in d if x<b); sg*=(-1)**ib; d.insert(ib,b)
            HV[idx[tuple(d)],i]+=sg*v
# Sz-max=3/2 block selection: count spins
Sz=np.array([sum(0.5 if so[o][1]==0 else -0.5 for o in d) for d in dets])
np.save('m.npy',np.array([H2,H4,HV])); np.save('sz.npy',Sz)
EOF
python3 d5.py && echo done