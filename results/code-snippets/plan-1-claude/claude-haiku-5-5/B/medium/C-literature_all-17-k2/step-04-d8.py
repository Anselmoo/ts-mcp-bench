import numpy as np
from scipy.special import sph_harm
from scipy.sparse import csr_matrix, identity, kron

nt, nph = 12, 16
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nph)*2*np.pi/nph
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.full(nph, 2*np.pi/nph)).ravel()
TH=TH.ravel(); PH=PH.ravel()
ms = [-2,-1,0,1,2]
Y = {m: sph_harm(m, 2, PH, TH) for m in ms}
def Ykq(k,q): return sph_harm(q,k,PH,TH)
Ang={}
for k in [0,2,4]:
    T=np.zeros((5,5,2*k+1),complex); T2=np.zeros((5,5,2*k+1),complex)
    for i,a in enumerate(ms):
        for j,c in enumerate(ms):
            for qi,q in enumerate(range(-k,k+1)):
                T[i,j,qi]=np.sum(W*np.conj(Y[a])*Y[c]*np.conj(Ykq(k,q)))
                T2[i,j,qi]=np.sum(W*np.conj(Y[a])*Y[c]*Ykq(k,q))
    Ang[k]=4*np.pi/(2*k+1)*np.einsum('acq,bdq->abcd',T,T2)

N=10
def cop(i):
    I2=identity(2,format='csr'); Z=csr_matrix(np.diag([1.,-1.])); a=csr_matrix(np.array([[0,1.],[0,0]]))
    ops=[Z]*i+[a]+[I2]*(N-i-1)
    out=csr_matrix(np.array([[1.]]))
    for o in ops: out=kron(out,o,format='csr')
    return out
c=[cop(i) for i in range(N)]
cd=[x.T.conj().tocsr() for x in c]
def spat(i): return i//2
def sp(i): return i%2
s2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,cf in d.items(): v[m+2]=cf
    return v
orbs={'z2':vec({0:1}),'x2y2':vec({2:1/s2,-2:1/s2}),
      'xy':vec({-2:1/(1j*s2),2:-1/(1j*s2)}),'xz':vec({-1:-1/s2,1:-1/s2}),'yz':vec({-1:1/(1j*s2),1:-1/(1j*s2)})}
eg={'z2','x2y2'}
# check orthonormality
M=np.array(list(orbs.values())); print("orth err", np.abs(M.conj()@M.T-np.eye(5)).max())
def build(Dq,B,C):
    F4=12.6*C; F2=49*B+5*F4/9
    Vk={0:0.0,2:F2,4:F4}
    h=np.zeros((5,5),complex)
    for nm,v in orbs.items():
        e = 6*Dq if nm in eg else -4*Dq
        h+= e*np.outer(v,np.conj(v))
    H=csr_matrix((1024,1024),dtype=complex)
    for m in range(5):
        for mp in range(5):
            if abs(h[m,mp])<1e-12: continue
            for s in range(2):
                H = H + h[m,mp]*(cd[2*m+s]@c[2*mp+s])
    Vt=sum(Vk[k]*Ang[k] for k in [0,2,4])
    for a in range(N):
        for b in range(N):
            for cc in range(N):
                for d in range(N):
                    if sp(a)!=sp(cc) or sp(b)!=sp(d): continue
                    v=Vt[spat(a),spat(b),spat(cc),spat(d)]
                    if abs(v)<1e-10: continue
                    H = H + 0.5*v*(cd[a]@cd[b]@c[d]@c[cc])
    return H.toarray()
idx8=[i for i in range(1024) if bin(i).count('1')==8]
def szof(i): return sum((1 if sp(j)==0 else -1) for j in range(N) if (i>>j)&1)
def levels(Dq,B,C):
    H=build(Dq,B,C)
    Hs=H[np.ix_(idx8,idx8)]
    res={}
    for sz in [2,0]:
        sub=[t for t,i in enumerate(idx8) if szof(i)==sz]
        ev=np.linalg.eigvalsh(Hs[np.ix_(sub,sub)])
        res[sz]=np.sort(ev.real)
    return res
