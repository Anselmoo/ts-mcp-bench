
python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.linalg import expm
C=3657/821; B=1.0
F4=441*C/35; F2=(441*B+5*F4)/9
ms=[-2,-1,0,1,2]
def so(m,s): return 2*(m+2)+s
nt=40; x,w=np.polynomial.legendre.leggauss(nt)
th=np.arccos(x); nph=60; ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def Y(l,m): return sph_harm_y(l,m,TH,PH)
def Ck(k,q): return np.sqrt(4*np.pi/(2*k+1))*Y(k,q)
cache={}
def A(k,q,m,mp):
    key=(k,q,m,mp)
    if key not in cache:
        cache[key]=np.sum(W*np.conj(Y(2,m))*Ck(k,q)*Y(2,mp))
    return cache[key]
Fk={2:F2,4:F4}
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
dets=list(itertools.combinations(range(10),4))
index={d:i for i,d in enumerate(dets)}
N=len(dets)
def cdag_c(i,j,occ):
    # c_i^dag c_j on sorted tuple occ
    occ=list(occ)
    if j not in occ: return None
    s=(-1)**sum(1 for o in occ if o<j); occ.remove(j)
    if i in occ: return None
    s*=(-1)**sum(1 for o in occ if o<i); occ.append(i); occ.sort()
    return s,tuple(occ)
def ann(k,occ):
    occ=list(occ)
    if k not in occ: return None
    s=(-1)**sum(1 for o in occ if o<k); occ.remove(k); return s,tuple(occ)
def cre(i,occ):
    occ=list(occ)
    if i in occ: return None
    s=(-1)**sum(1 for o in occ if o<i); occ.append(i); occ.sort(); return s,tuple(occ)
def build_2(V):
    H=np.zeros((N,N))
    nz=np.argwhere(np.abs(V)>1e-12)
    for a,d in enumerate(dets):
        for i,j,k,l in nz:
            # c_i^dag c_j^dag c_l c_k |d>
            r=ann(k,d)
            if r is None: continue
            s1,o1=r
            r=ann(l,o1)
            if r is None: continue
            s2,o2=r
            r=cre(j,o2)
            if r is None: continue
            s3,o3=r
            r=cre(i,o3)
            if r is None: continue
            s4,o4=r
            H[index[o4],a]+=0.5*V[i,j,k,l]*s1*s2*s3*s4
    return H
def build_1(h):
    H=np.zeros((N,N),complex)
    nz=np.argwhere(np.abs(h)>1e-14)
    for a,d in enumerate(dets):
        for i,j in nz:
            r=cdag_c(i,j,d)
            if r is None: continue
            s,st=r
            H[index[st],a]+=h[i,j]*s
    return H
Hee=build_2(V)
# check: d2 check not done here; check trace
print("Hee trace",np.trace(Hee).real)
r2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
dxy=vec({2:1/(1j*r2),-2:-1/(1j*r2)})
dyz=vec({1:1/(1j*r2),-1:1/(1j*r2)})
dxz=vec({1:1/r2,-1:-1/r2})
dx2=vec({2:1/r2,-2:1/r2})
dz2=vec({0:1})
Peg=sum(np.outer(v,v.conj()) for v in [dz2,dx2])
Pt2=sum(np.outer(v,v.conj()) for v in [dxy,dyz,dxz])
def h_cf(Dq):
    h=np.zeros((10,10),complex)
    for m1 in ms:
        for m2 in ms:
            for s in (0,1):
                h[so(m1,s),so(m2,s)]=(-4*Dq*Pt2[m1+2,m2+2]+6*Dq*Peg[m1+2,m2+2])
    return h
Sp=np.zeros((10,10)); Sm=np.zeros((10,10)); Sz=np.zeros((10,10))
for m in ms:
    Sp[so(m,0),so(m,1)]=1; Sm[so(m,1),so(m,0)]=1
    Sz[so(m,0),so(m,0)]=0.5; Sz[so(m,1),so(m,1)]=-0.5
Spo=build_1(Sp); Smo=build_1(Sm); Szo=build_1(Sz)
S2=(Szo@Szo+0.5*(Spo@Smo+Smo@Spo)).real
Lz=np.zeros((10,10))
for m in ms:
    for s in (0,1): Lz[so(m,s),so(m,s)]=m
Lzo=build_1(Lz)
R4=expm(-1j*np.pi/2*Lzo)
print("S2 check max eig", np.round(np.linalg.eigvalsh(S2)[[0,-1]],3))
for Dq in [0.90,2.15,3.35]:
    H=Hee+build_1(h_cf(Dq))
    M=H+1000*S2
    ev,evec=np.linalg.eigh(M)
    out=[]; i=0
    while i<N:
        j=i
        while j+1<N and abs(ev[j+1]-ev[i])<1e-5: j+=1
        mult=j-i+1
        vecs=evec[:,i:j+1]
        E=np.real(np.trace(vecs.conj().T@H@vecs))/mult
        S2v=np.real(np.trace(vecs.conj().T@S2@vecs))/mult
        S=(-1+np.sqrt(1+4*S2v))/2
        chi=np.trace(vecs.conj().T@R4@vecs)/mult
        out.append((round(E,4),round(S,2),mult,np.round(chi,3)))
        i=j+1
    print("Dq/B=",Dq)
    for o in out: print(o)
EOF
