import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre
from scipy.optimize import brentq
nt, nphi = 60, 120
xg, wg = leggauss(nt)
th = np.arccos(xg); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = (np.repeat(wg[:,None],nphi,1)*(2*np.pi/nphi)).ravel()
x = (np.sin(TH)*np.cos(PH)).ravel(); y=(np.sin(TH)*np.sin(PH)).ravel(); z=np.cos(TH).ravel()
raw = [x*y, x*z, y*z, x*x-y*y, (3*z*z-1)/2]
orb = np.array([f/np.sqrt(np.sum(W*f*f)) for f in raw])
cg = np.outer(x,x)+np.outer(y,y)+np.outer(z,z)
Pk = {k: eval_legendre(k, np.clip(cg,-1,1)) for k in (2,4)}
pairs = [(a,c) for a in range(5) for c in range(5)]
rho = np.array([orb[a]*orb[c] for a,c in pairs])
A = {k: (rho*W) @ Pk[k] @ (rho*W).T for k in (2,4)}
idx = {p:i for i,p in enumerate(pairs)}
def Vmat(F):
    V = np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        val = sum(F[k]*A[k][idx[(a,c)], idx[(b,d)]] for k in F)
        for s1 in (0,1):
            for s2 in (0,1):
                V[2*a+s1,2*b+s2,2*c+s1,2*d+s2] = val
    return V
dets = [tuple(sorted(c)) for c in itertools.combinations(range(10),6)]
didx = {d:i for i,d in enumerate(dets)}
def annih(k, st):
    if k not in st: return None
    p = st.index(k); return ((-1)**p, tuple(m for m in st if m!=k))
def create(i, st):
    if i in st: return None
    p = sum(1 for m in st if m<i); return ((-1)**p, tuple(sorted(st+(i,))))
N=len(dets)
def build_H(F, Dq):
    V = Vmat(F)
    H=np.zeros((N,N))
    h = np.array([-4,-4,-4,6,6])*Dq
    nz = [(i,j,k,l,V[i,j,k,l]) for i,j,k,l in itertools.product(range(10),repeat=4) if abs(V[i,j,k,l])>1e-12]
    for n,st in enumerate(dets):
        for m in st: H[n,n]+=h[m//2]
        for (i,j,k,l,v) in nz:
            r1=annih(k,st)
            if r1 is None: continue
            s1,c1=r1
            r2=annih(l,c1)
            if r2 is None: continue
            s2,c2=r2
            r3=create(j,c2)
            if r3 is None: continue
            s3,c3=r3
            r4=create(i,c3)
            if r4 is None: continue
            s4,c4=r4
            H[didx[c4],n]+=0.5*v*s1*s2*s3*s4
    return H
Sp=np.zeros((N,N)); Sz=np.zeros(N)
for n,st in enumerate(dets):
    Sz[n]=sum(0.5 if m%2==0 else -0.5 for m in st)
    for o in range(5):
        r1=annih(2*o+1,st)
        if r1 is None: continue
        s1,c1=r1
        r2=create(2*o,c1)
        if r2 is None: continue
        s2,c2=r2
        Sp[didx[c2],n]+=s1*s2
S2 = Sp.T@Sp + np.diag(Sz**2+Sz)
perm = {0:(0,-1),1:(2,1),2:(1,-1),3:(3,-1),4:(4,1)}
U=np.zeros((N,N))
for n,st in enumerate(dets):
    sign=1; cur=(); ok=True
    for m in st:
        o,s=divmod(m,2); no,sg=perm[o]; sign*=sg
        r=create(2*no+s,cur)
        if r is None: ok=False;break
        ss,cur=r; sign*=ss
    if ok: U[didx[cur],n]=sign
U=-U
w,v=np.linalg.eigh(S2); Q=v[:,np.abs(w)<1e-8]
Us=Q.T@U@Q
Hfix={}
def levels(Dq,B=1.0,C=4.5):
    F4=441*C*B/35; F2=(441*B+5*F4)/9
    H=build_H({2:F2,4:F4},Dq*B)
    Hs=Q.T@H@Q
    E,Vv=np.linalg.eigh(Hs)
    out=[];i=0
    while i<len(E):
        j=i
        while j+1<len(E) and abs(E[j+1]-E[i])<1e-7*max(1,abs(E[i])): j+=1
        blk=Vv[:,i:j+1]; tr=np.trace(blk.T@Us@blk)
        out.append((E[i], j-i+1, round(tr,3)))
        i=j+1
    return out
def ET(Dq):
    lv=levels(Dq); E0=lv[0][0]
    assert lv[0][1]==1 and lv[0][2]==1.0
    t1=[E-E0 for E,d,t in lv if d==3 and t==1.0]
    t2=[E-E0 for E,d,t in lv if d==3 and t==-1.0]
    return t1[0], t2[0]
for D in [3.0,3.5,4.0,4.5]:
    a,b=ET(D); print(D, round(a,4), round(b,4), round(b/a,5))
f=lambda D: ET(D)[1]/ET(D)[0]-23529/16611
xs=brentq(f,3.0,4.5,xtol=1e-10)
t1,t2=ET(xs)
B=16611/t1
print("x=Dq/B",xs,"B=",B,"Dq=",xs*B,"check T2=",t2*B, "C=",4.5*B)
# verify T1/T2 degeneracy classification at solution
print(levels(xs)[:6])
