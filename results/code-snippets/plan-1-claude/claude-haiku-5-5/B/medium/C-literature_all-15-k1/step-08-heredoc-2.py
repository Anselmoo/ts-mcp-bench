import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
def sph_harm(m,k,PH,TH): return sph_harm_y(k,m,TH,PH)
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
    return np.einsum('acq,bdq->abcd',G,G)*4*np.pi/(2*k+1)  # A[a,b,c,d]=sum G(a,c)G(b,d)
A={k:ak(k) for k in (0,2,4)}
so=[(o,s) for o in range(5) for s in (0,1)]
N=10
dets=list(itertools.combinations(range(N),7))
idx={d:i for i,d in enumerate(dets)}
M=len(dets)
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
# <ij|1/r|kl> = pairs (i,k),(j,l) -> A[oi,oj,ok,ol] with spin i=k, j=l
ee=[(i,j,k,l) for i,j,k,l in itertools.product(range(N),repeat=4) if so[i][1]==so[k][1] and so[j][1]==so[l][1]]
def op_matrix(terms):
    H=np.zeros((M,M))
    for m,d in enumerate(dets):
        for (i,j,k,l,v) in terms:
            r,s=apply_ops(d,[('c',i),('c',j),('a',l),('a',k)])
            if r is not None: H[idx[r],m]+=0.5*v*s
    return H
def coul(k):
    T=[]
    for (i,j,kk,l) in ee:
        v=A[k][so[i][0],so[j][0],so[kk][0],so[l][0]]
        if abs(v)>1e-12: T.append((i,j,kk,l,v))
    return op_matrix(T)
H2=coul(2); H4=coul(4)
hd=np.array([-4.0 if o<3 else 6.0 for o,s in so])
Hcf=np.zeros((M,M))
for m,d in enumerate(dets):
    for i in d: Hcf[m,m]+=hd[i]
Sz=np.zeros((M,M)); Sp=np.zeros((M,M))
for m,d in enumerate(dets):
    Sz[m,m]=sum(0.5 if so[i][1]==0 else -0.5 for i in d)
    for o in range(5):
        r,s=apply_ops(d,[('c',2*o),('a',2*o+1)])
        if r is not None: Sp[idx[r],m]+=s
S2=Sz@Sz+0.5*(Sp@Sp.T+Sp.T@Sp)
w,U=np.linalg.eigh(S2)
Q={S:U[:,np.abs(w-S*(S+1))<1e-6] for S in (1.5,0.5)}
def terms(Dq,B,C):
    F4=441*C/35.0; F2=441*B+5*F4
    H=Dq*Hcf+F2*H2+F4*H4
    out={}
    for S in (1.5,0.5):
        e=np.linalg.eigvalsh(Q[S].T@H@Q[S])
        # unique
        u=[]
        for x in np.sort(e):
            if not u or abs(x-u[-1][0])>1e-3: u.append([x,1])
            else: u[-1][1]+=1
        out[S]=u
    return out
t=terms(0,1,0)
print("free ion B=1 quartets (E, deg):",[(round(a-t[1.5][0][0],4),b) for a,b in t[1.5]])
print("free ion B=1 doublets:",[(round(a-t[1.5][0][0],4),b) for a,b in t[0.5]])
t=terms(0,0,1)
print("free ion C=1 quartets:",[(round(a-t[1.5][0][0],4),b) for a,b in t[1.5]])
print("free ion C=1 doublets:",[(round(a-t[1.5][0][0],4),b) for a,b in t[0.5]])
