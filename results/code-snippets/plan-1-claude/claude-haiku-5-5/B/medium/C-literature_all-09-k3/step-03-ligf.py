import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
from functools import lru_cache

# spin-orbitals: (m, s), m=-2..2, s=+1/2,-1/2 ; index 0..9
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
n=len(orbs)
@lru_cache(None)
def G(k,q,m,mp):
    # <2 m| C^k_q |2 mp>  with C^k_q = sqrt(4pi/(2k+1)) Y_kq
    if abs(q)>k or abs(m)>2 or abs(mp)>2: return 0.0
    val=gaunt(2,k,2,-m,q,mp)
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m*val)
def Vsp(m1,m2,m3,m4,F):
    tot=0.0
    for k,Fk in zip((0,2,4),F):
        if Fk==0: continue
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*G(k,-q,m1,m3)*G(k,q,m2,m4)
        tot+=Fk*s
    return tot
# Build Fock-space operators (Jordan-Wigner), restrict to N=5
dim=2**n
def cdag_c(i,j):
    # c_i^dag c_j
    pass
ann=[]
for i in range(n):
    M=np.zeros((dim,dim))
    for st in range(dim):
        if (st>>i)&1:
            sign=(-1)**bin(st & ((1<<i)-1)).count('1')
            M[st ^ (1<<i), st]=sign
    ann.append(M)
cre=[a.T for a in ann]
Nop=sum(cre[i]@ann[i] for i in range(n))
idx=[st for st in range(dim) if bin(st).count('1')==5]
def build(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5.0; F0=0.0
    F=(F0,F2,F4)
    h=np.zeros((n,n))
    # one-electron: V = -4Dq I + 10Dq P_eg ; P_eg = |0><0| + |2'><2'|, |2'>=(|2>+|-2>)/sqrt2
    Peg=np.zeros((5,5))  # index m+2
    Peg[2,2]=1
    v=np.zeros(5); v[0]=1/np.sqrt(2); v[4]=1/np.sqrt(2)
    Peg+=np.outer(v,v)
    Vmat=-4*Dq*np.eye(5)+10*Dq*Peg
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            if s1==s2: h[i,j]=Vmat[m1+2,m2+2]
    H1=sum(h[i,j]*cre[i]@ann[j] for i in range(n) for j in range(n) if abs(h[i,j])>1e-14)
    H2=np.zeros((dim,dim))
    # H2 = 1/2 sum <ij|V|kl> c_i^+ c_j^+ c_l c_k
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            for k,(m3,s3) in enumerate(orbs):
                for l,(m4,s4) in enumerate(orbs):
                    if s1!=s3 or s2!=s4: continue
                    val=Vsp(m1,m2,m3,m4,F)
                    if abs(val)<1e-12 or i==j or k==l: continue
                    H2+=0.5*val*(cre[i]@cre[j]@ann[l]@ann[k])
    H=H1+H2
    Hs=H[np.ix_(idx,idx)]
    # total spin S^2 in N=5 subspace
    Sz=np.zeros((dim,dim))
    for i,(m,s) in enumerate(orbs):
        Sz+=s*cre[i]@ann[i]
    # S+ S- for S^2
    Sp=np.zeros((dim,dim)); Sm=np.zeros((dim,dim))
    for a in range(5):
        # spin-up index 2*(m+2), down 2*(m+2)+1
        up=2*a; dn=2*a+1
        Sp+=cre[up]@ann[dn]; Sm+=cre[dn]@ann[up]
    S2=Sm@Sp+Sz@Sz+Sz
    S2s=S2[np.ix_(idx,idx)]
    w,U=np.linalg.eigh(Hs)
    # spin of each eigenvector
    ss=np.real(np.einsum('ia,ij,ja->a',U,S2s,U))
    return w,ss
