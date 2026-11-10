import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2; ms=list(range(-l,l+1))
def red(k): return float((-1)**l*(2*l+1)*wigner_3j(l,k,l,0,0,0))
def Cmat(k,q):
    M=np.zeros((5,5))
    for i,m in enumerate(ms):
        for j,mp in enumerate(ms):
            if -m+q+mp!=0 or abs(q)>k: continue
            M[i,j]=float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp))*red(k)
    return M
M4={q:Cmat(4,q) for q in range(-4,5)}
Mcub=M4[0]+np.sqrt(5/14)*(M4[4]+M4[-4])
Hcub=21.0*Mcub  # times Dq
# spin-orbital index: s*5+mi, s=0 up, 1 down
def so(s,mi): return s*5+mi
# Fock basis: 5-electron determinants
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(10),5)]
didx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply_cdag_c(a,c,state):
    # returns (sign, newstate) for a^dag_a a_c
    out={}
    for d,amp in state.items():
        if not (d>>c)&1: continue
        s1=(-1)**bin(d&((1<<c)-1)).count('1')
        d2=d^(1<<c)
        if (d2>>a)&1: continue
        s2=(-1)**bin(d2&((1<<a)-1)).count('1')
        d3=d2|(1<<a)
        out[d3]=out.get(d3,0)+amp*s1*s2
    return out
def apply_2(a,b,c,d,vec_state):
    # a^dag_a a^dag_b a_d a_c  acting on determinant: do a_c, then a_d, then a^dag_b, then a^dag_a
    st=vec_state
    st=apply_cdag_c(0,0,{}) if False else st
    # generic: sequence of ops
    def op(kind,i,s):
        out={}
        for dd,amp in s.items():
            if kind=='a':
                if not (dd>>i)&1: continue
                sg=(-1)**bin(dd&((1<<i)-1)).count('1'); nd=dd^(1<<i)
            else:
                if (dd>>i)&1: continue
                sg=(-1)**bin(dd&((1<<i)-1)).count('1'); nd=dd|(1<<i)
            out[nd]=out.get(nd,0)+amp*sg
        return out
    s=op('a',c,st); s=op('a',d,s); s=op('c',b,s); s=op('c',a,s)
    return s
# build Coulomb operator pieces: need two-body ops for each k with coefficient matrices
# V = 1/2 sum_k F^k sum_{abcd} <ab|C^k.C^k|cd> a^+_a a^+_b a_d a_c
# <ab|..|cd> = sum_q (-1)^q C^k_q[a,c] C^k_{-q}[b,d] (spin: s_a=s_c, s_b=s_d)
def twobody_matrices(k):
    # returns dict of matrix elements over all (a,b,c,d) as list
    terms=[]
    for a,b,c,d in itertools.product(range(10),repeat=4):
        sa,ma=divmod(a,5); sb,mb=divmod(b,5); sc,mc=divmod(c,5); sd,md=divmod(d,5)
        if sa!=sc or sb!=sd: continue
        val=0.0
        for q in range(-k,k+1):
            val+=(-1)**q*Cmat(k,q)[ma,mc]*Cmat(k,-q)[mb,md]
        if abs(val)>1e-12: terms.append((a,b,c,d,val))
    return terms
def build_op_matrix(terms):
    Mx=np.zeros((N,N))
    for a,b,c,d,val in terms:
        for j,dd in enumerate(dets):
            out=apply_2(a,b,c,d,{dd:1.0})
            for nd,amp in out.items():
                if nd in didx: Mx[didx[nd],j]+=val*amp
    return Mx
def one_body(Mat):
    Mx=np.zeros((N,N))
    for a in range(10):
        for c in range(10):
            sa,ma=divmod(a,5); sc,mc=divmod(c,5)
            if sa!=sc: continue
            v=Mat[ma,mc]
            if abs(v)<1e-12: continue
            for j,dd in enumerate(dets):
                out=apply_cdag_c(a,c,{dd:1.0})
                for nd,amp in out.items():
                    Mx[didx[nd],j]+=v*amp
    return Mx
import time
t=time.time()
Vk={k:0.5*build_op_matrix(twobody_matrices(k)) for k in (0,2,4)}
print('built',time.time()-t)
Hcf=one_body(Hcub)   # times Dq
# S^2
Sp=np.zeros((N,N)); Sz=np.zeros((N,N))
for m in range(5):
    Sp+=one_body(np.eye(5)*0)  # placeholder
Sp=np.zeros((N,N))
for m in range(5):
    # a^dag_up,m a_down,m
    for j,dd in enumerate(dets):
        out=apply_cdag_c(so(0,m),so(1,m),{dd:1.0})
        for nd,amp in out.items(): Sp[didx[nd],j]+=amp
Sm=Sp.T
Szd=np.diag([ (sum(1 for i in range(5) if (dd>>i)&1)-sum(1 for i in range(5,10) if (dd>>i)&1))/2 for dd in dets])
S2=Sm@Sp+Szd@Szd+Szd
np.savez('/tmp/ops.npz',Hcf=Hcf,V0=Vk[0],V2=Vk[2],V4=Vk[4],S2=S2)
print('saved')
