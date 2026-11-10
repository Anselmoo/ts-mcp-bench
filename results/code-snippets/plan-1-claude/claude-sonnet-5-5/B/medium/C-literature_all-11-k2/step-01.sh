
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[2,1,0,-1,-2]
def ck(k,m1,m2): # <2m1|C^k_q|2m2>, q=m1-m2
    q=m1-m2
    return float((-1)**m1*np.sqrt(5*5)*__import__('sympy').physics.wigner.wigner_3j(2,k,2,-m1,q,m2)*__import__('sympy').physics.wigner.wigner_3j(2,k,2,0,0,0))
so=[(m,s) for m in ms for s in (0,1)]
n=10
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def g(k,a,b,c,d): # <ab|1/r12|cd> angular: sum_q c^k(a,c)c^k(b,d) with (-1)^q
    return C[(k,a,c)]*C[(k,d,b)] if a-c==d-b else 0
# <ab|g|cd> = sum_k c^k(a,c) c^k(d,b) F^k
import sympy
dets=list(itertools.combinations(range(10),6))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def build(F2,F4,Dq):
    H=np.zeros((N,N))
    F={0:0,2:F2,4:F4}
    V=np.zeros((5,5)); 
    for i,m in enumerate(ms): V[i,i]={2:1,1:-4,0:6,-1:-4,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    # two-electron antisym matrix elements
    def v2(p,q,r,s_): # <pq|r s> direct - exchange
        (a,sa),(b,sb),(c,sc),(d,sd)=so[p],so[q],so[r],so[s_]
        val=0
        if sa==sc and sb==sd: val+=sum(g(k,a,b,c,d)*F[k] for k in (2,4))
        if sa==sd and sb==sc: val-=sum(g(k,a,b,d,c)*F[k] for k in (2,4))
        return val
    for I,d in enumerate(dets):
        for J,e in enumerate(dets):
            diff1=set(d)-set(e)
            if len(diff1)>2: continue
            # build via second quantization
            pass
    return V,v2
E
echo