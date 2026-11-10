import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import brentq
def sph_harm(m,k,P,T): return sph_harm_y(k,m,T,P)
N=40
x,w=np.polynomial.legendre.leggauss(N)
phi=np.linspace(0,2*np.pi,2*N,endpoint=False)
T,P=np.meshgrid(np.arccos(x),phi,indexing='ij'); W=np.outer(w,np.ones(2*N))*(2*np.pi/(2*N))
X=np.sin(T)*np.cos(P);Y=np.sin(T)*np.sin(P);Z=np.cos(T)
c=np.sqrt(15/(4*np.pi))
d=[np.sqrt(5/(16*np.pi))*(3*Z**2-1), c*X*Z, c*Y*Z, c*X*Y, c/2*(X**2-Y**2)]
def ang(k):
    Yc={m:sph_harm(m,k,P,T) for m in range(-k,k+1)}
    A=np.zeros((2*k+1,5,5),complex); Bm=np.zeros((2*k+1,5,5),complex)
    for i,m in enumerate(range(-k,k+1)):
        for a in range(5):
            for cc in range(5):
                A[i,a,cc]=np.sum(W*d[a]*Yc[m]*d[cc])
                Bm[i,a,cc]=np.sum(W*d[a]*np.conj(Yc[m])*d[cc])
    return np.einsum('iac,ibd->acbd',A,Bm)*4*np.pi/(2*k+1)
G0=ang(0).real; G2=ang(2).real; G4=ang(4).real
def apply_ann(l,p):
    if p not in l: return None
    return (-1)**l.index(p), [q for q in l if q!=p]
def apply_cre(l,p):
    if p in l: return None
    return (-1)**sum(1 for q in l if q<p), sorted(l+[p])
def build(Dq,F2,F4,nel=6):
    h1=np.array([6*Dq,-4*Dq,-4*Dq,-4*Dq,6*Dq])
    Vo=F2*G2+F4*G4
    states=list(itertools.combinations(range(10),nel)); idx={s:i for i,s in enumerate(states)}
    n=len(states); H=np.zeros((n,n)); Sp=np.zeros((n,n)); Sz=np.zeros(n)
    quads=[(a,cc,b,dd) for a,cc,b,dd in itertools.product(range(10),repeat=4) if a%2==cc%2 and b%2==dd%2 and abs(Vo[a//2,cc//2,b//2,dd//2])>1e-12]
    for j,s in enumerate(states):
        l=list(s)
        Sz[j]=0.5*sum(1 if p%2==0 else -1 for p in l)
        for p in l: H[j,j]+=h1[p//2]
        for a,cc,b,dd in quads:
            r=apply_ann(l,cc)
            if r is None: continue
            s1,l1=r; r=apply_ann(l1,dd)
            if r is None: continue
            s2,l2=r; r=apply_cre(l2,b)
            if r is None: continue
            s3,l3=r; r=apply_cre(l3,a)
            if r is None: continue
            s4,l4=r
            H[idx[tuple(l4)],j]+=0.5*s1*s2*s3*s4*Vo[a//2,cc//2,b//2,dd//2]
        for orb in range(5):
            up,dn=2*orb,2*orb+1
            r=apply_ann(l,dn)
            if r is None: continue
            s1,l1=r; r=apply_cre(l1,up)
            if r is None: continue
            s2,l2=r; Sp[idx[tuple(l2)],j]+=s1*s2
    S2=Sp.T@Sp+np.diag(Sz**2+Sz)
    return H,S2
def singlet_levels(Dq,B,C=None):
    C=4*B if C is None else C
    F4=441*C/35; F2=(441*B+5*F4)/9
    H,S2=build(Dq,F2,F4)
    ev,V=np.linalg.eigh(H+1e4*S2)
    out=[e for e,v in zip(ev,V.T) if abs(v@S2@v)<1e-6]
    lv=[]
    for e in out:
        if lv and abs(e-lv[-1][0])<1e-5: lv[-1][1]+=1
        else: lv.append([e,1])
    return lv
def Ts(x):
    lv=singlet_levels(x,1.0); e0=lv[0][0]
    T=[e-e0 for e,m in lv if m==3 and e-e0>1e-6]
    return T
# fit: x such that T2/T1 = 26330/16700 ; then check T3/T1
r12=26330/16700; r13=35020/16700
def f(x):
    T=Ts(x); return T[1]/T[0]-r12
xs=np.linspace(1.5,3.5,21)
vals=[f(v) for v in xs]
print('scan',[(round(a,2),round(b,4)) for a,b in zip(xs,vals)])
