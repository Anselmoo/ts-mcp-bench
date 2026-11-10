import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <2m1|C^k|2m2>
    q=m1-m2
    return float((-1)**m1*np.sqrt(5*5)*0+ 0)
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    from sympy import sqrt
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
C={k:np.array([[c(k,a,b) for b in ms] for a in ms]) for k in (0,2,4)}
# real orbital transform: real = U @ complex ; order xy,yz,z2,xz,x2-y2
s=1/np.sqrt(2)
idx={m:i for i,m in enumerate(ms)}
U=np.zeros((5,5),complex)
def setr(r,d):
    for m,v in d.items(): U[r,idx[m]]=v
setr(0,{2:-1j*s,-2:1j*s}) # xy
setr(1,{1:1j*s,-1:1j*s})  # yz
setr(2,{0:1})
setr(3,{1:-s,-1:s})       # xz
setr(4,{2:s,-2:s})
# t2g: 0,1,3 ; eg: 2,4
def build(Dq,B,Cc):
    F={0:0,2:49*B+7*Cc,4:63*Cc/5}
    # V[a,b,c,d]=<ab|1/r|cd> complex, a->c on e1
    V=np.zeros((5,)*4,complex)
    for k in (2,4):
        # <m1 m2|g|m3 m4> = sum_q c^k(m1,m3)c^k(m4,m2) F^k  (Condon-Shortley)
        V+=F[k]*np.einsum('ac,db->abcd',C[k],C[k])
    Ur=U
    # real basis r = sum U[r,m] m ; <r1r2|g|r3r4>
    Vr=np.einsum('ia,jb,kc,ld,abcd->ijkl',Ur.conj(),Ur.conj(),Ur,Ur,V)
    h=np.diag([-4*Dq,-4*Dq,6*Dq,-4*Dq,6*Dq]).astype(complex)
    return h,Vr
def H(Dq,B,Cc):
    h,V=build(Dq,B,Cc)
    n=10 # spin orbitals: 2*i+s
    dets=[d for d in itertools.combinations(range(10),7)]
    di={d:i for i,d in enumerate(dets)}
    N=len(dets); Hm=np.zeros((N,N),complex)
    def so(p):return p//2,p%2
    for I,d in enumerate(dets):
        for p in d:
            Hm[I,I]+=h[p//2,p//2]
    # two-body: 1/2 sum <pq|rs> a+p a+q a_s a_r
    for I,d in enumerate(dets):
        for r,s_ in itertools.permutations(d,2):
            rest=[x for x in d if x not in(r,s_)]
            for p in range(10):
                for q in range(10):
                    if p==q: continue
                    if p%2!=r%2 or q%2!=s_%2: continue
                    if p in rest or q in rest: continue
                    val=V[p//2,q//2,r//2,s_//2]
                    if abs(val)<1e-12: continue
                    # apply a_r then a_s... operator a+p a+q a_s a_r
                    lst=list(d);sign=1
                    def ann(l,x):
                        i=l.index(x);l.pop(i);return (-1)**i
                    def cre(l,x):
                        pos=sum(1 for y in l if y<x);l.insert(pos,x);return (-1)**pos
                    sign*=ann(lst,r);sign*=ann(lst,s_)
                    sign*=cre(lst,q);sign*=cre(lst,p)
                    J=di[tuple(lst)]
                    Hm[J,I]+=0.5*sign*val
    return Hm
def levels(Dq,B,Cc):
    e=np.linalg.eigvalsh(H(Dq,B,Cc))
    e=np.round(e-e.min(),3)
    u=sorted(set(np.round(e,1)))
    return e
import sys
e=levels(900,900,3500)
from collections import Counter
print(sorted(Counter(np.round(e,0)).items())[:14])
