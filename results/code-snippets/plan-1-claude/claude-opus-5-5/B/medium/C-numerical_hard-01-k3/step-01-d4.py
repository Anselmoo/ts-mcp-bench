import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    # c^k(l=2 m1, l=2 m2) = (-1)^m1 * 5 * 3j...
    from sympy.physics.wigner import wigner_3j
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def Rk(k,a,b,c,d): # <ab|1/r|cd>, a,c electron1
    if a+b!=c+d: return 0
    return C[(k,a,c)]*C[(k,d,b)]
dets=list(itertools.combinations(range(10),4))
idx={d:i for i,d in enumerate(dets)}
# triplet, Ms=1 subspace: count up spins=3? Ms=1 => 3 alpha? spin index 1=alpha
dets=[d for d in dets if sum(so[i][1] for i in d)==3]
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def Fk(B,Cc):
    A=0; F2=49*B+7*Cc; F4=441*Cc/35
    return {0:0,2:F2,4:F4}
def cf(Dq):
    V=np.zeros((5,5)); d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): V[i,i]=d[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    return V
# precompute two-electron integrals as function
def H(Dq,B,Cc):
    F=Fk(B,Cc); V=cf(Dq)
    def g(p,q,r,s): # <pq|rs> spin orbitals
        (a,sa),(b,sb),(c,sc),(d,sd)=so[p],so[q],so[r],so[s]
        if sa!=sc or sb!=sd: return 0
        return sum(F[k]*Rk(k,a,b,c,d) for k in (2,4))
    def h(p,q):
        (a,sa),(b,sb)=so[p],so[q]
        return V[a+2,b+2] if sa==sb else 0
    Hm=np.zeros((N,N))
    for I,D in enumerate(dets):
        for J,E in enumerate(dets):
            diff1=[x for x in D if x not in E]; diff2=[x for x in E if x not in D]
            if len(diff1)>2: continue
            def sign(D,rem,add):
                L=list(D); s=1
                for r,a in zip(rem,add):
                    i=L.index(r); L[i]=a
                # sort with sign
                perm=sorted(range(len(L)),key=lambda k:L[k])
                # parity
                p=list(perm); par=1
                vis=[False]*len(p)
                for i in range(len(p)):
                    if not vis[i]:
                        j=i;c=0
                        while not vis[j]: vis[j]=True;j=p[j];c+=1
                        if c%2==0: par=-par
                return par
            if len(diff1)==0:
                v=sum(h(p,p) for p in D)
                for i in range(4):
                    for j in range(i+1,4):
                        p,q=D[i],D[j]; v+=g(p,q,p,q)-g(p,q,q,p)
            elif len(diff1)==1:
                p=diff1[0]; r=diff2[0]; sg=sign(D,[p],[r])
                v=h(p,r)+sum(g(p,q,r,q)-g(p,q,q,r) for q in D if q!=p)
                v*=sg
            else:
                p,q=diff1; r,s=diff2; sg=sign(D,[p,q],[r,s])
                v=sg*(g(p,q,r,s)-g(p,q,s,r))
            Hm[J,I]=v
    return Hm
import pickle
