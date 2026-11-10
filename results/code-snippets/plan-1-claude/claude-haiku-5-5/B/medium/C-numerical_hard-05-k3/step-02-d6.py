import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
from scipy.sparse import csr_matrix, kron, identity, diags
from scipy.sparse.linalg import eigsh
ms=[-2,-1,0,1,2]
# spin-orbitals: index = 2*orb + s (s=0 up,1 down)
so=[(m,s) for m in ms for s in (0,1)]
n=len(so)
gcache={}
def G(a,b,c,d,e,f):
    key=(a,b,c,d,e,f)
    if key not in gcache: gcache[key]=float(gaunt(a,b,c,d,e,f))
    return gcache[key]
def angular(mi,mj,mk,ml,K):
    tot=0.0
    for q in range(-K,K+1):
        A1=(-1)**(mi+q)*G(2,2,K,-mi,mk,-q) if abs(-mi)<=2 and abs(mk)<=2 else 0
        A2=(-1)**mj*G(2,2,K,-mj,ml,q) if abs(-mj)<=2 and abs(ml)<=2 else 0
        tot+=A1*A2
    return tot*4*np.pi/(2*K+1)
def Vint(F):  # F dict K->value
    V=np.zeros((n,n,n,n))
    for i,(mi,si) in enumerate(so):
        for j,(mj,sj) in enumerate(so):
            for k,(mk,sk) in enumerate(so):
                for l,(ml,sl) in enumerate(so):
                    if si!=sk or sj!=sl: continue
                    v=0
                    for K in (0,2,4):
                        v+=F[K]*angular(mi,mj,mk,ml,K)
                    V[i,j,k,l]=v
    return V
# Fock operators via Jordan-Wigner
I2=identity(2,format='csr'); Z=diags([1,-1]).tocsr(); a=csr_matrix(np.array([[0,1],[0,0]]))
def cop(p):
    ops=[Z]*p+[a]+[I2]*(n-p-1)
    M=ops[0]
    for o in ops[1:]: M=kron(M,o,format='csr')
    return M
c=[cop(p) for p in range(n)]
cd=[x.T.conj().tocsr() for x in c]
def build(Dq,B,C):
    F4=C*441/35.0; F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    V=Vint(F)
    dim=2**n
    H=csr_matrix((dim,dim))
    # one-electron: 10Dq P_eg  (eg = z2 (m=0) and (Y22+Y2-2)/sqrt2 )
    # projector: P = |z><z| + |x><x| with |x>=(|2>+|-2>)/sqrt2 in orbital space
    h=np.zeros((5,5))
    iz=2  # m=0
    h[iz,iz]=1
    ix=[0,4]  # m=-2 index 0, m=+2 index 4
    for p in ix:
        for q in ix:
            h[p,q]+=0.5
    h=10*Dq*h  # 10Dq P_eg
    for p,(mp,sp) in enumerate(so):
        for q,(mq,sq) in enumerate(so):
            if sp!=sq: continue
            op=mp+2; oq=mq+2
            if h[op,oq]!=0:
                H=H+h[op,oq]*(cd[p]@c[q])
    for i in range(n):
        for j in range(n):
            for k in range(n):
                for l in range(n):
                    if abs(V[i,j,k,l])>1e-12:
                        H=H+0.5*V[i,j,k,l]*(cd[i]@cd[j]@c[l]@c[k])
    # select N=6
    Nop=sum(cd[p]@c[p] for p in range(n))
    S2z=0.5*sum((cd[p]@c[p])*(1 if so[p][1]==0 else -1) for p in range(n))
    return H.toarray(), Nop.toarray().diagonal(), S2z.toarray().diagonal()
