import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
def ck(k,m1,m2):
    # c^k(l m1, l m2) for l=2
    return float((-1)**m1*np.sqrt(5*5)*__import__('sympy').physics.wigner.wigner_3j(2,k,2,0,0,0)*__import__('sympy').physics.wigner.wigner_3j(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def V(a,b,c,d,F):  # <ab|1/r|cd>, orbitals indices
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[orbs[i] for i in (a,b,c,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*C[(k,ma,mc)]*C[(k,md,mb)] for k in (0,2,4))
dets=list(itertools.combinations(range(10),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
# one-electron cubic field in m basis: V4 operator; use real-orbital: eg 6Dq, t2g -4Dq
# In m basis: m=0: 6Dq; m=±1: -4Dq; m=±2: diag 1Dq, off-diag(2,-2) 5Dq
def h1(m1,m2,Dq):
    if m1==m2: return {0:6,1:-4,-1:-4,2:1,-2:1}[m1]*Dq
    if abs(m1-m2)==4: return 5*Dq
    return 0
# precompute two-electron matrices with F2,F4 unit
def build(Dq,B,Cc):
    F4=Cc*441/35/441*... if False else None
