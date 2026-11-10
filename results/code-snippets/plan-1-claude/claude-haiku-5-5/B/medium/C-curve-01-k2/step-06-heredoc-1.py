import numpy as np, itertools
from scipy.special import sph_harm_y
C=3657/821; B=1.0
F4=441*C/35; F2=(441*B+5*F4)/9
ms=[-2,-1,0,1,2]
def so(m,s): return 2*(m+2)+s
nt=40; x,w=np.polynomial.legendre.leggauss(nt)
th=np.arccos(x); nph=60; ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def Y(l,m): return sph_harm_y(l,m,TH,PH)
def A(k,q,m,mp): return np.sum(W*np.conj(Y(2,m))*np.sqrt(4*np.pi/(2*k+1))*Y(k,q)*Y(2,mp))
Fk={2:F2,4:F4}
V=np.zeros((10,10,10,10))
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    val=sum(Fk[k]*sum((-1)**q*A(k,q,m1,m3)*A(k,-q,m2,m4) for q in range(-k,k+1)) for k in (2,4))
    val=val.real
    if abs(val)<1e-12: continue
    for s1 in (0,1):
        for s2 in (0,1):
            V[so(m1,s1),so(m2,s2),so(m3,s1),so(m4,s2)]=val
def run(n):
    dets=list(itertools.combinations(range(10),n)); index={d:i for i,d in enumerate(dets)}; N=len(dets)
    H=np.zeros((N,N)); nz=np.argwhere(np.abs(V)>1e-12)
    def cre(i,occ):
        if i in occ: return None
        s=(-1)**sum(1 for o in occ if o<i); return s,tuple(sorted(occ+[i]))
    def ann(k,occ):
        if k not in occ: return None
        s=(-1)**sum(1 for o in occ if o<k); return s,tuple(o for o in occ if o!=k)
    for a,d in enumerate(dets):
        for i,j,k,l in nz:
            r=ann(k,list(d)); 
            if r is None: continue
            s1,o1=r; r=ann(l,list(o1))
            if r is None: continue
            s2,o2=r; r=cre(j,list(o2))
            if r is None: continue
            s3,o3=r; r=cre(i,list(o3))
            if r is None: continue
            s4,o4=r
            H[index[o4],a]+=0.5*V[i,j,k,l]*s1*s2*s3*s4
    Sp=np.zeros((10,10))
    for m in ms: Sp[so(m,0),so(m,1)]=1
    Sz=np.zeros((10,10))
    for m in ms: Sz[so(m,0),so(m,0)]=0.5; Sz[so(m,1),so(m,1)]=-0.5
    return dets,H
dets,H=run(2)
# S2 for d2 via Sz and S+ S-
ev,evec=np.linalg.eigh(H)
print("d2 eigen grouped:")
i=0
while i<len(ev):
    j=i
    while j+1<len(ev) and abs(ev[j+1]-ev[i])<1e-6: j+=1
    print(round(ev[i],4), j-i+1); i=j+1
