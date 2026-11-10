import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
l=2
ms=list(range(-2,3))
def orb(m,s): return 2*(m+2)+s
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def ck(m,k,q,mp):  # <l m|C^k_q|l mp>
    if m!=mp+q: return 0.0
    return (-1)**(l-m)*w3(l,k,l,-m,q,mp)*(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
def Vint(a,b,c,d,F):  # <ab|1/r12|cd>, a,b,c,d orbital m-values
    tot=0.0
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            s+=(-1)**q*ck(a,k,-q,c)*ck(b,k,q,d)
        tot+=F[k]*s
    return tot
def build(B,C,Dq):
    F4=441*C/35; F2=(441*B+5*F4)/9; F={0:0.0,2:F2,4:F4}
    # one-electron: Dq*(-4I+10 Peg)
    Peg=np.zeros((5,5))
    z=np.zeros(5); z[ms.index(0)]=1
    x=np.zeros(5); x[ms.index(2)]=1/np.sqrt(2); x[ms.index(-2)]=1/np.sqrt(2)
    Peg=np.outer(z,z)+np.outer(x,x)
    M=Dq*(-4*np.eye(5)+10*Peg)
    h=np.zeros((10,10))
    for m1 in ms:
        for m2 in ms:
            for s in (0,1):
                h[orb(m1,s),orb(m2,s)]=M[ms.index(m1),ms.index(m2)]
    # two-electron V[a,b,c,d] = <ab|V|cd>
    V=np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(10),repeat=4):
        ma,sa=divmod(a,2); mb,sb=divmod(b,2); mc,sc=divmod(c,2); md,sd=divmod(d,2)
        ma-=2; mb-=2; mc-=2; md-=2
        if sa!=sc or sb!=sd: continue
        V[a,b,c,d]=Vint(ma,mb,mc,md,F)
    return h,V
def fock_basis(N=6,norb=10):
    return [sum(1<<i for i in c) for c in itertools.combinations(range(norb),N)]
def apply_cdag_c(state,p,q):  # a+_p a_q
    if not (state>>q)&1: return None,0
    sgn=(-1)**bin(state&((1<<q)-1)).count('1')
    st=state^(1<<q)
    if (st>>p)&1: return None,0
    sgn*=(-1)**bin(st&((1<<p)-1)).count('1')
    return st|(1<<p),sgn
def hamiltonian(h,V):
    basis=fock_basis(); idx={s:i for i,s in enumerate(basis)}
    n=len(basis); H=np.zeros((n,n))
    for j,s in enumerate(basis):
        # one-body
        for p in range(10):
            for q in range(10):
                if h[p,q]==0: continue
                t,sg=apply_cdag_c(s,p,q)
                if t is not None: H[idx[t],j]+=sg*h[p,q]
        # two-body: 1/2 sum V[a,b,c,d] a+_a a+_b a_d a_c
        for c in range(10):
            for d in range(10):
                if d==c: continue
                t1,s1=apply_cdag_c(s,c,d) if False else (None,0)
                # a_c then a_d: a_d a_c |s>, apply a_c first
                if not (s>>c)&1: continue
                s_c=s^(1<<c); sg1=(-1)**bin(s&((1<<c)-1)).count('1')
                if not (s_c>>d)&1: continue
                s_cd=s_c^(1<<d); sg2=(-1)**bin(s_c&((1<<d)-1)).count('1')
                tot=sg1*sg2
                for a in range(10):
                    for b in range(10):
                        v=V[a,b,c,d]
                        if v==0 or a==b: continue
                        if (s_cd>>b)&1: continue
                        s_b=s_cd|(1<<b); sg3=(-1)**bin(s_cd&((1<<b)-1)).count('1')
                        if (s_b>>a)&1: continue
                        s_ab=s_b|(1<<a); sg4=(-1)**bin(s_b&((1<<a)-1)).count('1')
                        H[idx[s_ab],j]+=0.5*v*tot*sg3*sg4
    return basis,H
def S2(basis):
    idx={s:i for i,s in enumerate(basis)}; n=len(basis)
    # S^2 = Sz^2 + Sz + S-S+ ; build S+ = sum_m a+_{m up} a_{m down}
    Sp=np.zeros((n,n)); 
    for j,s in enumerate(basis):
        for m in ms:
            t,sg=apply_cdag_c(s,orb(m,0),orb(m,1))
            if t is not None: Sp[idx[t],j]+=sg
    Sz=np.zeros((n,n))
    for j,s in enumerate(basis):
        Sz[j,j]=sum((0.5 if not (s>>orb(m,0))&1 else 0)*0 for m in ms)
        Sz[j,j]=0.5*sum(((s>>orb(m,0))&1)-((s>>orb(m,1))&1) for m in ms)
    return Sz@Sz+Sp.T@Sp*0+ (Sz) - Sp.T@Sp*0 + Sp@Sp.T*0 + Sp.T@Sp - 0  # placeholder replaced below
