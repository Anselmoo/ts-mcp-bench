cat << 'EOF' > d6.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.sparse import csr_matrix, kron, identity, diags
ms=[-2,-1,0,1,2]
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
        A1=(-1)**((mi+q)%2)*G(2,2,K,-mi,mk,-q)
        A2=(-1)**(mj%2)*G(2,2,K,-mj,ml,q)
        tot+=A1*A2
    return tot*4*np.pi/(2*K+1)
Vang={}
for K in (0,2,4):
    Vang[K]=np.zeros((n,n,n,n))
for i,(mi,si) in enumerate(so):
  for j,(mj,sj) in enumerate(so):
    for k,(mk,sk) in enumerate(so):
      for l,(ml,sl) in enumerate(so):
        if si!=sk or sj!=sl: continue
        for K in (0,2,4):
            Vang[K][i,j,k,l]=angular(mi,mj,mk,ml,K)
I2=identity(2,format='csr'); Z=diags([1.0,-1.0]).tocsr(); a=csr_matrix(np.array([[0.0,1.0],[0.0,0.0]]))
def cop(p):
    ops=[Z]*p+[a]+[I2]*(n-p-1)
    M=ops[0]
    for o in ops[1:]: M=kron(M,o,format='csr')
    return M
c=[cop(p) for p in range(n)]
cd=[x.T.conj().tocsr() for x in c]
Nop=sum(cd[p]@c[p] for p in range(n))
Sz2=sum((cd[p]@c[p])*(0.5 if so[p][1]==0 else -0.5) for p in range(n))
def build(Dq,B,C):
    F4=C*441/35.0; F2=(441*B+5*F4)/9.0
    V=F2*Vang[2]+F4*Vang[4]
    h=np.zeros((5,5))
    h[2,2]=1
    for p in (0,4):
        for q in (0,4):
            h[p,q]+=0.5
    h=10*Dq*h
    dim=2**n
    H=csr_matrix((dim,dim))
    for p,(mp,sp) in enumerate(so):
        for q,(mq,sq) in enumerate(so):
            if sp!=sq: continue
            if h[mp+2,mq+2]!=0: H=H+h[mp+2,mq+2]*(cd[p]@c[q])
    for i,j,k,l in zip(*np.nonzero(np.abs(V)>1e-12)):
        H=H+0.5*V[i,j,k,l]*(cd[i]@cd[j]@c[l]@c[k])
    return H
def spectrum(Dq,B,C):
    H=build(Dq,B,C)
    Nd=Nop.diagonal(); Sd=Sz2.diagonal()
    idx=np.where((np.abs(Nd-6)<1e-9)&(np.abs(Sd)<1e-9))[0]
    Hs=H.toarray()[np.ix_(idx,idx)] if False else (H[idx][:,idx]).toarray()
    w=np.linalg.eigvalsh(Hs)
    return w
EOF
python3 -c "
import d6,numpy as np
w=d6.spectrum(0.0,1.0,4.5)
print(len(w)); print(np.round(w-w[0],4)[:40])
"