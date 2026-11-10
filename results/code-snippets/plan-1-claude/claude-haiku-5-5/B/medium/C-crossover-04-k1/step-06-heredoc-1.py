import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=922.0; C=4156.0
F4=441*C/35; F2=49*B+7*C
print("F2,F4",F2,F4)
F={2:F2,4:F4}
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (0,1) for m in ms]
n=10
G={}
for ma in ms:
  for mc in ms:
    for k in (2,4):
      for q in range(-k,k+1):
        G[(ma,k,q,mc)]=float((-1)**ma*gaunt(2,k,2,-ma,q,mc))
def V2(a,b,c,d):
    ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
    if sa!=sc or sb!=sd: return 0.0
    tot=0.0
    for k in (2,4):
        s=0.0
        for q in range(-k,k+1):
            if (mc+q)!=ma or (md-q)!=mb: continue
            s+=(-1)**q*G[(ma,k,q,mc)]*G[(mb,k,-q,md)]
        tot+=F[k]*4*np.pi/(2*k+1)*s
    return tot
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
r2=np.sqrt(2)
orbs=[(6,vec({0:1})),(6,vec({2:1/r2,-2:1/r2})),
      (-4,vec({2:1/(1j*r2),-2:-1/(1j*r2)})),
      (-4,vec({1:-1/r2,-1:1/r2})),
      (-4,vec({1:1j/r2,-1:1j/r2}))]
M=np.array([o[1] for o in orbs])
assert np.allclose(M.conj()@M.T,np.eye(5))
def hmat(Dq):
    h=np.zeros((5,5),complex)
    for e,v in orbs: h+=Dq*e*np.outer(v,v.conj())
    return h
def dets(nup,ndn):
    out=[]
    for A in itertools.combinations(range(5),nup):
        for Bb in itertools.combinations(range(5,10),ndn):
            out.append(tuple(sorted(A+Bb)))
    return out
def annih(st,j):
    if j not in st: return None
    p=st.index(j)
    return ((-1)**p,[x for x in st if x!=j])
def create(st,j):
    if j in st: return None
    p=sum(1 for x in st if x<j)
    return ((-1)**p,sorted(st+[j]))
Vt={}
for a,b,c,d in itertools.product(range(n),repeat=4):
    v=V2(a,b,c,d)
    if abs(v)>1e-12: Vt[(a,b,c,d)]=v
def opmat(bra,ket,H1):
    tot=0j
    kl=list(ket)
    for i in range(n):
        for j in range(n):
            if abs(H1[i,j])<1e-14: continue
            r=annih(kl,j)
            if r is None: continue
            s1,st=r
            r=create(st,i)
            if r is None: continue
            s2,st2=r
            if tuple(st2)==bra: tot+=H1[i,j]*s1*s2
    for (a,b,c,d),v in Vt.items():
        r=annih(kl,c)
        if r is None: continue
        s1,st=r
        r=annih(st,d)
        if r is None: continue
        s2,st=r
        r=create(st,b)
        if r is None: continue
        s3,st=r
        r=create(st,a)
        if r is None: continue
        s4,st=r
        if tuple(st)==bra: tot+=0.5*v*s1*s2*s3*s4
    return tot
def energies(Dq,nup,ndn):
    occ=dets(nup,ndn)
    h=hmat(Dq)
    H1=np.zeros((n,n),complex)
    for s in (0,1):
        for i in range(5):
            for j in range(5):
                H1[i+5*s,j+5*s]=h[i,j]
    N=len(occ)
    Hm=np.array([[opmat(occ[I],occ[J],H1) for J in range(N)] for I in range(N)])
    Hm=(Hm+Hm.conj().T)/2
    return np.sort(np.linalg.eigvalsh(Hm))
e0=energies(0.0,5,2); print("quartet free:",np.round(e0-e0[0],1))
d0=energies(0.0,4,3); print("M=1/2 free:",np.round(d0-e0[0],1))
def gap(Dq):
    q=energies(Dq,5,2)[0]; d=energies(Dq,4,3)
    # lowest doublet: remove quartet eigenvalues (those in M_S=3/2 spectrum)
    qall=energies(Dq,5,2)
    return None
