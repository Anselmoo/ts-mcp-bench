import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import sqrt, pi
from scipy.optimize import fsolve
from scipy.linalg import eigh

l=2
ms=list(range(-2,3))
orbs=[(m,s) for m in ms for s in (+1,-1)]   # s=+1/2 -> +1 ; use 2*s
N=len(orbs)
# all 5-electron determinants
basis=[]
for occ in itertools.combinations(range(N),5):
    basis.append(sum(1<<i for i in occ))
idx={b:i for i,b in enumerate(basis)}
D=len(basis)

def gnt(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))
# complex-basis cubic field matrix: W = sum_q a_q <2m|Y4q|2m'> (up to sign), a0=1,a4=a-4=sqrt(5/14)
W=np.zeros((5,5))
for i,m in enumerate(ms):
    for j,mp in enumerate(ms):
        # Y_{2m}^* Y_{4q} Y_{2mp}; Y^* = (-1)^m Y_{-m}
        val=0.0
        for q,a in ((0,1.0),(4,sqrt(5/14)),(-4,sqrt(5/14))):
            if abs(-m+q+mp)>0: continue
            val+= a*((-1)**m)*gnt(2,4,2,-m,q,mp)
        W[i,j]=val
ev,U=np.linalg.eigh(W)
print("W eigen",np.round(ev,4))
# t2g: 3-fold lower, eg: 2-fold upper; normalize to -4 and +6 (Dq units)
ev_sorted=ev
# shape: lowest 3 -> t2g, top 2 -> eg
low=ev[:3]; high=ev[3:]
scale_low=-4.0/np.mean(low); scale_high=6.0/np.mean(high)
assert abs(scale_low-scale_high)<1e-8, (scale_low,scale_high)
Wn=W*scale_low
# one-body crystal field operator as a function of Dq: h = Dq * Wn
# Two-body angular coefficients
def Cmat(k,q):
    M=np.zeros((5,5))
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            # <l m|C^k_q|l m'> = (-1)^m sqrt(4pi/(2k+1)) * int Y*_{lm} Y_{kq} Y_{lm'}
            if -m+q!=mp and False: pass
            if (-m+q)!=mp: continue
            M[i,j]=((-1)**m)*sqrt(4*pi/(2*k+1))*gnt(l,k,l,-m,q,mp)
    return M
Cq={ (k,q):Cmat(k,q) for k in (0,2,4) for q in range(-k,k+1)}
# angular coefficient tensor A_k[a,b,c,d] = sum_q (-1)^q <a|C^k_{-q}|c><b|C^k_q|d>, a..d orbital indices (5)
Ang={}
for k in (0,2,4):
    T=np.zeros((5,5,5,5))
    for q in range(-k,k+1):
        T+= ((-1)**q)*np.einsum('ac,bd->abcd', Cq[(k,-q)], Cq[(k,q)])
    Ang[k]=T
# spin-orbital two-body: V[a,b,c,d] over spin orbitals
def build_ops():
    # one-body h (per unit Dq) on spin orbitals
    H1=np.zeros((N,N))  # Dq coefficient
    Vk={k:np.zeros((N,N,N,N)) for k in (0,2,4)}
    for A,(m1,s1) in enumerate(orbs):
        for B_,(m2,s2) in enumerate(orbs):
            if s1==s2: H1[A,B_]=Wn[ms.index(m1),ms.index(m2)]
    for A,(m1,s1) in enumerate(orbs):
     for B_,(m2,s2) in enumerate(orbs):
      for C_,(m3,s3) in enumerate(orbs):
       for D_,(m4,s4) in enumerate(orbs):
        if s1==s3 and s2==s4:
            i1,i2,i3,i4=ms.index(m1),ms.index(m2),ms.index(m3),ms.index(m4)
            for k in (0,2,4):
                Vk[k][A,B_,C_,D_]=Ang[k][i1,i2,i3,i4]
    return H1,Vk
H1,Vk=build_ops()
# Second-quantized matrices in determinant basis
def apply_cdag_c(p,q,state):
    # c^dag_p c_q |state>, returns (sign,newstate) or None
    if not (state>>q)&1: return None
    s=state
    sign=1
    # annihilate q
    below=bin(s & ((1<<q)-1)).count('1')
    sign*= (-1)**below
    s&=~(1<<q)
    if (s>>p)&1: return None
    below=bin(s & ((1<<p)-1)).count('1')
    sign*= (-1)**below
    s|=(1<<p)
    return sign,s
def one_body_mat(M1):
    H=np.zeros((D,D))
    for j,b in enumerate(basis):
        for p in range(N):
            for q in range(N):
                if M1[p,q]==0: continue
                r=apply_cdag_c(p,q,b)
                if r is None: continue
                sg,nb=r
                H[idx[nb],j]+=sg*M1[p,q]
    return H
def two_body_mat(V):
    H=np.zeros((D,D))
    nz=[(a,b,c,d,V[a,b,c,d]) for a in range(N) for b in range(N) for c in range(N) for d in range(N) if abs(V[a,b,c,d])>1e-12]
    for j,bst in enumerate(basis):
        for (a,b,c,d,v) in nz:
            # c^dag_a c^dag_b c_d c_c  (1/2 sum V_abcd)
            if not (bst>>c)&1: continue
            r1=apply_cdag_c(0,0,0) # placeholder
            # apply c_c then c_d then c^dag_b then c^dag_a
            s=bst; sign=1
            # c_c
            below=bin(s&((1<<c)-1)).count('1'); sign*=(-1)**below; s&=~(1<<c)
            if not (s>>d)&1: continue
            below=bin(s&((1<<d)-1)).count('1'); sign*=(-1)**below; s&=~(1<<d)
            if (s>>b)&1: continue
            below=bin(s&((1<<b)-1)).count('1'); sign*=(-1)**below; s|=(1<<b)
            if (s>>a)&1: continue
            below=bin(s&((1<<a)-1)).count('1'); sign*=(-1)**below; s|=(1<<a)
            H[idx[s],j]+=0.5*sign*v
    return H
H1m=one_body_mat(H1)   # multiply by Dq
Vmats={k:two_body_mat(Vk[k]) for k in (0,2,4)}
np.save('/work/H1.npy',H1m)
for k in Vmats: np.save(f'/work/V{k}.npy',Vmats[k])
# spin operators
def Sz_mat():
    S=np.zeros(D)
    return np.diag([sum(0.5*s for i,(m,s) in enumerate(orbs) if (b>>i)&1) for b in basis])
Sz=Sz_mat()
# S^2 = S- S+ + Sz^2 + Sz ; S+ = sum c^dag_{m,up} c_{m,down}
Splus=np.zeros((D,D)); Sminus=np.zeros((D,D))
for i,(m,s) in enumerate(orbs):
    if s!=1: continue
    j=orbs.index((m,-1))
    Splus+=one_body_mat(np.where(np.arange(N)[:,None]==i,1.0,0)*np.where(np.arange(N)[None,:]==j,1.0,0))
    Sminus+=one_body_mat(np.where(np.arange(N)[:,None]==j,1.0,0)*np.where(np.arange(N)[None,:]==i,1.0,0))
S2=Sminus@Splus+Sz@Sz+Sz
np.save('/work/S2.npy',S2)
np.save('/work/Sz.npy',Sz)
print("done", D)
