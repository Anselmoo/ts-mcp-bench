import numpy as np, itertools
from scipy.special import sph_harm
from scipy.linalg import eigh
B=1.0; C=3657/821
F4=441*C/35; F2=(441*B+5*F4)/9
# spin-orbital index: idx = 2*(m+2)+s  (s=0 up,1 down)
ms=[-2,-1,0,1,2]
def so(m,s): return 2*(m+2)+s
# angular integrals via quadrature
nt=40; x,w=np.polynomial.legendre.leggauss(nt)
th=np.arccos(x); nph=60; ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def Y(l,m): return sph_harm(m,l,PH,TH)
def Ck(k,q): return np.sqrt(4*np.pi/(2*k+1))*Y(k,q)
def A(k,q,m,mp):
    return np.sum(W*np.conj(Y(2,m))*Ck(k,q)*Y(2,mp))
Fk={0:0.0,2:F2,4:F4}
# two-electron integrals
V=np.zeros((10,10,10,10))
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    val=0
    for k in (2,4):
        s=0
        for q in range(-k,k+1):
            s+=(-1)**q*A(k,q,m1,m3)*A(k,-q,m2,m4)
        val+=Fk[k]*s
    val=val.real
    if abs(val)<1e-12: continue
    for s1 in (0,1):
        for s2 in (0,1):
            V[so(m1,s1),so(m2,s2),so(m3,s1),so(m4,s2)]=val
# determinants
dets=[d for d in itertools.combinations(range(10),4)]
index={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply_cdag_c(i,j,state):
    # state: sorted tuple; returns (sign, newstate) or None for c_i^dag c_j
    occ=list(state)
    if j not in occ: return None
    sgn=(-1)**sum(1 for o in occ if o<j)
    occ.remove(j)
    if i in occ: return None
    sgn*=(-1)**sum(1 for o in occ if o<i)
    occ.append(i); occ.sort()
    return sgn,tuple(occ)
def apply_2(i,j,k,l,state):
    # c_i^dag c_j^dag c_l c_k  (k applied first)
    r=apply_cdag_c_gen(l,k,state)
    if r is None: return None
    s1,st1=r
    r=apply_cdag_c_gen(j,None,st1) if False else None
    # c_j^dag c_i^dag? careful: c_i^dag c_j^dag = -c_j^dag c_i^dag ; do c_j^dag then c_i^dag
    occ=list(st1)
    if j in occ: return None
    s2=(-1)**sum(1 for o in occ if o<j); occ.append(j); occ.sort()
    if i in occ: return None
    s3=(-1)**sum(1 for o in occ if o<i); occ.append(i); occ.sort()
    return s1*s2*s3,tuple(occ)
def apply_cdag_c_gen(l,k,state):
    # c_l c_k : annihilate k then l
    occ=list(state)
    if k not in occ: return None
    s=(-1)**sum(1 for o in occ if o<k); occ.remove(k)
    if l not in occ: return None
    s*=(-1)**sum(1 for o in occ if o<l); occ.remove(l)
    return s,tuple(occ)
def build_op2(V):
    H=np.zeros((N,N))
    nz=np.argwhere(np.abs(V)>1e-12)
    for a,d in enumerate(dets):
        for i,j,k,l in nz:
            r=apply_2(i,j,k,l,d)
            if r is None: continue
            s,st=r
            H[index[st],a]+=0.5*V[i,j,k,l]*s
    return H
def build_1(h):  # h[i,j] c_i^dag c_j
    H=np.zeros((N,N))
    for a,d in enumerate(dets):
        for i,j in np.argwhere(np.abs(h)>1e-14):
            r=apply_cdag_c(i,j,d)
            if r is None: continue
            s,st=r
            H[index[st],a]+=h[i,j]*s
    return H
Hee=build_2=build_op2(V)
# crystal field one-electron matrix in m basis
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=np.sqrt(2)
eg=[vec({0:1}), vec({2:1/r2,-2:1/r2}), ]
t2g=[vec({2:1/r2,-2:-1/r2}*0+{2:1/r2,-2:-1/r2}) ]
# build proper orthonormal real orbitals
dxy=vec({2:1/(1j*r2),-2:-1/(1j*r2)})
dyz=vec({1:1/(1j*r2),-1:1/(1j*r2)})
dxz=vec({1:1/r2,-1:-1/r2})
dx2=vec({2:1/r2,-2:1/r2})
dz2=vec({0:1})
Peg=sum(np.outer(v,v.conj()) for v in [dz2,dx2])
Pt2=sum(np.outer(v,v.conj()) for v in [dxy,dyz,dxz])
# one-electron spin-orbital matrix
def h_cf(Dq):
    h=np.zeros((10,10),complex)
    for m1 in ms:
        for m2 in ms:
            for s in (0,1):
                h[so(m1,s),so(m2,s)]=(-4*Dq*Pt2[m1+2,m2+2]+6*Dq*Peg[m1+2,m2+2])
    return h
# spin operators
Sp=np.zeros((10,10)); Sm=np.zeros((10,10))
Sz=np.zeros((10,10))
for m in ms:
    Sp[so(m,0),so(m,1)]=1; Sm[so(m,1),so(m,0)]=1
    Sz[so(m,0),so(m,0)]=0.5; Sz[so(m,1),so(m,1)]=-0.5
Spo=build_1(Sp); Smo=build_1(Sm); Szo=build_1(Sz)
S2=Szo@Szo+0.5*(Spo@Smo+Smo@Spo)
# Lz rotation (C4 about z)
Lz=np.zeros((10,10))
for m in ms:
    for s in (0,1): Lz[so(m,s),so(m,s)]=m
Lzo=build_1(Lz)
from scipy.linalg import expm
R4=expm(-1j*np.pi/2*Lzo)
np.save('/tmp/Hee.npy',Hee); np.save('/tmp/S2.npy',S2); np.save('/tmp/R4.npy',R4)
import pickle
pickle.dump(dict(Hee=Hee,S2=S2,R4=R4,Lzo=Lzo),open('/tmp/ops.pkl','wb'))
# check 3P-3F for d2 check: build d2 sector quickly separately is skipped
def one_body(h): return build_1(h)
results={}
for Dq in [0.90,2.15,3.35]:
    Hcf=build_1(h_cf(Dq))
    H=Hee+Hcf
    M=H+1000*S2
    ev,evec=np.linalg.eigh(M)
    # group
    out=[]
    i=0
    while i<N:
        j=i
        while j+1<N and abs(ev[j+1]-ev[i])<1e-6: j+=1
        mult=j-i+1
        vecs=evec[:,i:j+1]
        Eall=np.real(np.mean(np.diag(vecs.conj().T@H@vecs)))
        S2v=np.real(np.trace(vecs.conj().T@S2@vecs))/mult
        S=(-1+np.sqrt(1+4*S2v))/2
        # character of C4
        chi=np.trace(vecs.conj().T@R4@vecs)
        out.append((round(Eall,6),round(S,3),mult,np.round(chi,3)))
        i=j+1
    results[Dq]=out
    print("Dq/B=",Dq)
    for o in out: print(o)
