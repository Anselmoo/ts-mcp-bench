cd /; python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
th=np.arccos(xg); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=(np.outer(wg,np.ones(nphi))*2*np.pi/nphi)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
orbs={'xy':x*y,'xz':x*z,'yz':y*z,'z2':(3*z**2-1)/2,'x2y2':(x**2-y**2)*np.sqrt(3)/2}
names=list(orbs)
for n in names:
    f=orbs[n]; orbs[n]=f/np.sqrt(np.sum(W*f*f))
def Rkq(k):
    out=[]
    for m in range(-k,k+1):
        if m==0: out.append(sph_harm(0,k,PH,TH).real)
        elif m>0: out.append(np.sqrt(2)*(-1)**m*sph_harm(m,k,PH,TH).real)
        else: out.append(np.sqrt(2)*(-1)**m*sph_harm(-m,k,PH,TH).imag)
    return out
def ak(k):
    R=Rkq(k); n=5
    G=np.zeros((n,n,len(R)))
    for i,a in enumerate(names):
        for j,c in enumerate(names):
            for q,Rq in enumerate(R):
                G[i,j,q]=np.sum(W*orbs[a]*orbs[c]*Rq)
    return np.einsum('acq,bdq->abcd',G,G)*4*np.pi/(2*k+1)
A={k:ak(k) for k in (0,2,4)}
# check: a0 should be 1 for (aa,bb)
print("a0 xy,xy,xy,xy", A[0][0,0,0,0], "a2 check t2g", A[2][0,0,0,0])
so=[(o,s) for o in range(5) for s in (0,1)]
N=10
def build(Dq,B,C):
    F4=441*C/35.0; F2=441*B+5*F4
    F={0:0.0,2:F2,4:F4}
    V=np.zeros((N,N,N,N))
    for i,(oi,si) in enumerate(so):
        for j,(oj,sj) in enumerate(so):
            for k_,(ok,sk) in enumerate(so):
                for l,(ol,sl) in enumerate(so):
                    if si!=sk or sj!=sl: continue
                    V[i,j,k_,l]=sum(F[kk]*A[kk][oi,ok,oj,ol] for kk in (0,2,4))
    h=np.zeros((N,N))
    for i,(o,s) in enumerate(so):
        h[i,i]= -4*Dq if o<3 else 6*Dq
    return h,V
dets=list(itertools.combinations(range(N),7))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det,ops):
    occ=list(det); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
# precompute operator structure
ee=[]
for i,j,k,l in itertools.product(range(N),repeat=4):
    if so[i][1]==so[k][1] and so[j][1]==so[l][1]:
        ee.append((i,j,k,l))
def hamiltonian(Dq,B,C):
    h,V=build(Dq,B,C)
    M=len(dets); H=np.zeros((M,M))
    for m,d in enumerate(dets):
        for i in range(N):
            for j in range(N):
                if abs(h[i,j])>1e-12:
                    r,s=apply_ops(d,[('c',i),('a',j)])
                    if r is not None: H[idx[r],m]+=h[i,j]*s
        for (i,j,k,l) in ee:
            v=V[i,j,k,l]
            if abs(v)<1e-12: continue
            r,s=apply_ops(d,[('c',i),('c',j),('a',l),('a',k)])
            if r is not None: H[idx[r],m]+=0.5*v*s
    return H
M=len(dets)
Sz=np.zeros((M,M)); Sp=np.zeros((M,M))
for m,d in enumerate(dets):
    Sz[m,m]=sum(0.5 if so[i][1]==0 else -0.5 for i in d)
    for o in range(5):
        r,s=apply_ops(d,[('c',2*o),('a',2*o+1)])
        if r is not None: Sp[idx[r],m]+=s
S2=Sz@Sz+0.5*(Sp@Sp.T+Sp.T@Sp)
np.save('/dev/null',np.zeros(1)) if False else None
def levels(Dq,B,C):
    H=hamiltonian(Dq,B,C)
    w,v=np.linalg.eigh(H+1e5*S2)
    res={1:[],3:[],5:[]}
    for e,vec in zip(w,v.T):
        s2=vec@S2@vec; S=(-1+np.sqrt(1+4*s2))/2
        res.setdefault(round(2*S),[]).append(e)
    return res
r=levels(1000,1000,4000)
print({k:[round(x,1) for x in v[:6]] for k,v in r.items()})
# check free-ion limit: Dq=0 quartet energies should be 4F(0) and 4P at 15B-... 
r=levels(0,1000,4000)
print("free ion Dq=0 quartets",[round(x-r[3][0],1) for x in r[3]][:6])
print("doublets",[round(x-r[3][0],1) for x in r[1]][:12])
import pickle
EOF