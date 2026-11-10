import numpy as np, itertools, scipy.sparse as sp
from sympy.physics.wigner import gaunt
from scipy.special import sph_harm_y
from scipy.optimize import fsolve
ms=list(range(-2,3))
def a(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        s+= float(gaunt(2,k,2,-m1,-q,m3)*gaunt(2,k,2,-m2,q,m4))*(-1)**(m1+q+m2)
    return 4*np.pi/(2*k+1)*s
Acoef={}
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    Acoef[(m1,m2,m3,m4)]=np.array([a(k,m1,m2,m3,m4) for k in (0,2,4)])
th,wt=np.polynomial.legendre.leggauss(40)
phis=np.linspace(0,2*np.pi,80,endpoint=False)
T,P=np.meshgrid(np.arccos(th),phis,indexing='ij')
W=np.outer(wt,np.ones(len(phis)))*(2*np.pi/len(phis))
x=np.sin(T)*np.cos(P); y=np.sin(T)*np.sin(P); z=np.cos(T)
V=np.zeros_like(T)
for L in [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]:
    c=x*L[0]+y*L[1]+z*L[2]; V+=35*c**4/8-30*c**2/8+3/8
M1=np.zeros((5,5))
for i,m1 in enumerate(ms):
    for j,m2 in enumerate(ms):
        M1[i,j]=np.real(np.sum(np.conj(sph_harm_y(2,m1,T,P))*V*sph_harm_y(2,m2,T,P)*W))
nso=10; N=1<<nso
def ann(p):
    rows=[];cols=[];vals=[]
    for st in range(N):
        if (st>>p)&1:
            sign=(-1)**bin(st & ((1<<p)-1)).count('1')
            rows.append(st^(1<<p)); cols.append(st); vals.append(sign)
    return sp.csr_matrix((vals,(rows,cols)),shape=(N,N))
ANN=[ann(p) for p in range(nso)]
CRE=[X.T.tocsr() for X in ANN]
def so(mi,s): return 2*mi+s
# N=5 subspace
pop=np.array([bin(s).count('1') for s in range(N)])
idx5=np.where(pop==5)[0]
# Sz operator
szd=np.array([sum((0.5 if (s>>(2*i))&1 else 0)-(0.5 if (s>>(2*i+1))&1 else 0) for i in range(5)) for s in range(N)])
# S+ = sum_i c_up^dag c_down
Splus=sp.csr_matrix((N,N))
for i in range(5): Splus=Splus+CRE[so(i,0)]@ANN[so(i,1)]
Sminus=Splus.T.tocsr()
Sz=sp.diags(szd)
S2=Sminus@Splus+Sz@Sz+Sz
def build(Dq,B,C):
    F=np.array([0.0,49*B+7*C,12.6*C])
    H=sp.csr_matrix((N,N))
    for i in range(5):
        for j in range(5):
            if M1[i,j]!=0:
                for s in (0,1):
                    H=H+6*Dq*M1[i,j]*(CRE[so(i,s)]@ANN[so(j,s)])
    Hd=sp.csr_matrix((N,N))
    for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
        coef=Acoef[(m1,m2,m3,m4)]@F
        if abs(coef)<1e-12: continue
        for s1 in (0,1):
            for s2 in (0,1):
                Hd=Hd+0.5*coef*(CRE[so(m1+2,s1)]@CRE[so(m2+2,s2)]@ANN[so(m4+2,s2)]@ANN[so(m3+2,s1)])
    return (H+Hd)
def spectrum(Dq,B,C):
    H=build(Dq,B,C)
    H5=H[idx5][:,idx5].toarray(); S25=S2[idx5][:,idx5].toarray()
    # diagonalize H in full N=5 space; classify by S^2 via projection
    w,v=np.linalg.eigh(H5)
    S2e=np.einsum('ia,ij,ja->a',v,S25,v)
    return w,S2e
w,S2e=spectrum(0,1000,4000)
for e,s in zip(w,S2e):
    pass
import collections
print("lowest levels (E, S(S+1)):")
for e,s in zip(w[:20],S2e[:20]): print(round(e,3), round(s,3))
np.save if False else None
import pickle
pickle.dump(None,open('<SANDBOX_TMP>/null.pkl','wb')) if False else None
globals().update(dict(build=build,spectrum=spectrum))
