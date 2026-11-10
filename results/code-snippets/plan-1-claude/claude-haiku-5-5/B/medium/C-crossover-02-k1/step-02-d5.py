import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from math import sqrt
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]  # 10 spin-orbitals
N=len(orbs)
def ang(k,m1,q,m2):  # <l m1|C^k_q|l m2>
    if m1!=m2+q: return 0.0
    # reduced <l||C^k||l> = (-1)^l (2l+1) (l k l;0 0)
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-m1)*float(wigner_3j(l,k,l,-m1,q,m2))*red
def Vsp(a,b,c,d):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=a,b,c,d
    if sa!=sc or sb!=sd: return 0.0
    tot={}
    val=0.0
    # returns dict k->angular factor (multiply by F^k)
    out=[]
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*ang(k,ma,q,mc)*ang(k,mb,-q,md)
        out.append(s)
    return out
# Slater integrals (cm-1)
def run(Dq,F0,F2,F4):
    F=[F0,F2,F4]
    # build two-electron integrals <ab|V|cd>
    V=np.zeros((N,N,N,N))
    for a in range(N):
        for b in range(N):
            for c in range(N):
                for d in range(N):
                    r=Vsp(orbs[a],orbs[b],orbs[c],orbs[d])
                    if r==0.0: continue
                    V[a,b,c,d]=sum(F[i]*r[i] for i in range(3))
    # one-electron cubic field: W = C4_0 + sqrt(5/14)(C4_4+C4_-4); eigen on l=2
    W=np.zeros((5,5))
    ms=list(range(-2,3))
    for i,m1 in enumerate(ms):
        for j,m2 in enumerate(ms):
            W[i,j]=ang(4,m1,0,m2)+sqrt(5/14)*(ang(4,m1,4,m2)+ang(4,m1,-4,m2))
    ev=np.linalg.eigvalsh(W)
    return W,ev
if __name__=="__main__":
    W,ev=run(0,1,0,0)
    print(np.round(ev,4))
