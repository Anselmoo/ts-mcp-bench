import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (+1,-1) for m in ms]
N=len(so)
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.linspace(0,2*np.pi,nph,endpoint=False)
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
def Y(l,m,t,p): return sph_harm_y(l,m,t,p)
def ang(k,conj1):
    A=np.zeros((5,5,2*k+1),complex)
    for i,a in enumerate(ms):
        for j,c in enumerate(ms):
            for qi,q in enumerate(range(-k,k+1)):
                if conj1: A[i,j,qi]=np.sum(W*np.conj(Y(2,a,TH,PH))*np.conj(Y(k,q,TH,PH))*Y(2,c,TH,PH))
                else:     A[i,j,qi]=np.sum(W*np.conj(Y(2,a,TH,PH))*Y(k,q,TH,PH)*Y(2,c,TH,PH))
    return A
A={k:ang(k,True) for k in (2,4)}; B={k:ang(k,False) for k in (2,4)}
def Vk(k):
    return 4*np.pi/(2*k+1)*np.einsum('acq,bdq->abcd',A[k],B[k])
V2,V4=Vk(2),Vk(4)
def apply(ops,state):
    st=set(state); s=1
    for typ,i in reversed(ops):
        lst=sorted(st); pos=sum(1 for j in lst if j<i)
        if typ=='a':
            if i not in st: return None,0
            s*=(-1)**pos; st.remove(i)
        else:
            if i in st: return None,0
            s*=(-1)**pos; st.add(i)
    return frozenset(st),s
dets=[frozenset(c) for c in itertools.combinations(range(N),3)]
idx={d:i for i,d in enumerate(dets)}; D=len(dets)
def two_body(V):
    H=np.zeros((D,D),complex)
    for J,d in enumerate(dets):
        for a,b,c,e in itertools.product(range(N),repeat=4):
            if so[a][1]!=so[c][1] or so[b][1]!=so[e][1]: continue
            val=V[ms.index(so[a][0]),ms.index(so[b][0]),ms.index(so[c][0]),ms.index(so[e][0])]
            if abs(val)<1e-13: continue
            ns,s=apply([('c',a),('c',b),('a',e),('a',c)],d)
            if ns is None: continue
            H[idx[ns],J]+=0.5*val*s
    return H
s2=np.sqrt(2)
def vec(d): return np.array([d.get(m,0) for m in ms],complex)
dz2=vec({0:1}); dxz=vec({1:-1/s2,-1:1/s2}); dyz=vec({1:-1j/s2,-1:-1j/s2})
dx2=vec({2:1/s2,-2:1/s2}); dxy=vec({2:-1j/s2,-2:1j/s2})
P=np.zeros((5,5),complex)
for v in [dz2,dx2]: P+=6*np.outer(v,np.conj(v))
for v in [dxz,dyz,dxy]: P+=-4*np.outer(v,np.conj(v))
def one_body(h):
    H=np.zeros((D,D),complex)
    for J,d in enumerate(dets):
        for a in range(N):
            for b in range(N):
                if so[a][1]!=so[b][1]: continue
                val=h[ms.index(so[a][0]),ms.index(so[b][0])]
                if abs(val)<1e-13: continue
                ns,s=apply([('c',a),('a',b)],d)
                if ns is None: continue
                H[idx[ns],J]+=val*s
    return H
H2=two_body(V2); H4=two_body(V4); HCF=one_body(P)  # Dq=1 scale: P has eg +6, t2g -4
# Sanity: H2,H4 Hermitian
print("herm", np.allclose(H2,H2.conj().T), np.allclose(H4,H4.conj().T), np.allclose(HCF,HCF.conj().T))
def levels(F2,F4,Dq):
    H=F2*H2+F4*H4+Dq*HCF
    H=H.real
    # Sz=3/2 sector: all spin up
    up=[i for i,d in enumerate(dets) if all(so[k][1]==+1 for k in d)]
    q=np.linalg.eigvalsh(H[np.ix_(up,up)])
    # Sz=1/2 sector: two up one down
    mid=[i for i,d in enumerate(dets) if sum(so[k][1] for k in d)==1]
    dd=np.linalg.eigvalsh(H[np.ix_(mid,mid)])
    # remove quartet eigenvalues (M_S=1/2 components of quartets) from mid list
    rem=list(dd)
    for e in q:
        j=int(np.argmin([abs(r-e) for r in rem])); rem.pop(j)
    return np.sort(q), np.sort(np.array(rem))
if __name__=="__main__":
    q,dbl=levels(1.0,0.0,0.0)
    print("quartets at Dq=0,F2=1,F4=0:",np.round(q,4))
    print("doublets:",np.round(dbl,4))
