import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt

ms=[-2,-1,0,1,2]
def tensors():
    out={}
    for k in (2,4):
        Ck={}
        for q in range(-k,k+1):
            M=np.zeros((5,5))
            for ia,ma in enumerate(ms):
                for ic,mc in enumerate(ms):
                    if ma-mc!=q: continue
                    g=float(gaunt(2,k,2,-ma,q,mc))*(-1)**ma
                    M[ia,ic]=sqrt(4*pi/(2*k+1))*g
            Ck[q]=M
        V=np.zeros((5,5,5,5))
        for a,b,c,d in itertools.product(range(5),repeat=4):
            s=0.0
            for q in range(-k,k+1):
                s+=(-1)**q*Ck[q][a,c]*Ck[-q][b,d]
            V[a,b,c,d]=s
        out[k]=V
    return out

T=tensors()
def cf_one_body(Dq):
    h=np.zeros((5,5),dtype=complex)
    I=np.eye(5)
    v_eg=[I[2], (I[4]+I[0])/sqrt(2)]
    v_t2g=[(I[4]-I[0])/(1j*sqrt(2)), (I[3]-I[1])/sqrt(2), (I[3]+I[1])/(1j*sqrt(2))]
    for v in v_eg: h+=6*Dq*np.outer(v,v.conj())
    for v in v_t2g: h+=-4*Dq*np.outer(v,v.conj())
    return h

def det_basis(nel=6, nso=10):
    return [sum(1<<i for i in c) for c in itertools.combinations(range(nso),nel)]

def apply_ops(state, ops):
    s=state; sign=1
    for typ,i in reversed(ops):
        if typ=='c':
            if (s>>i)&1: return None,0
            sign*=(-1)**bin(s & ((1<<i)-1)).count('1')
            s|=(1<<i)
        else:
            if not (s>>i)&1: return None,0
            sign*=(-1)**bin(s & ((1<<i)-1)).count('1')
            s&=~(1<<i)
    return s,sign

def hamiltonian(F2,F4,Dq,basis):
    h1=cf_one_body(Dq)
    idx={s:i for i,s in enumerate(basis)}
    N=len(basis)
    H=np.zeros((N,N))
    h=np.zeros((10,10))
    for o1 in range(5):
        for o2 in range(5):
            for sp in range(2):
                h[2*o1+sp,2*o2+sp]=h1[o1,o2].real  # real part; imag parts cancel in cubic set
    Vfull=F2*T[2]+F4*T[4]
    for col,s in enumerate(basis):
        for i in range(10):
            for j in range(10):
                if abs(h[i,j])<1e-14: continue
                ns,sg=apply_ops(s,[('c',i),('a',j)])
                if ns is None: continue
                H[idx[ns],col]+=h[i,j]*sg
        for o1,o2,o3,o4 in itertools.product(range(5),repeat=4):
            v=Vfull[o1,o2,o3,o4]
            if abs(v)<1e-12: continue
            for s1 in range(2):
              for s2 in range(2):
                a=2*o1+s1; b=2*o2+s2; c=2*o3+s1; d=2*o4+s2
                ns,sg=apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
                if ns is None: continue
                H[idx[ns],col]+=0.5*v*sg
    return H

def S2_matrix(basis):
    idx={s:i for i,s in enumerate(basis)}
    N=len(basis)
    Sz=np.zeros(N)
    for col,s in enumerate(basis):
        nup=sum((s>>(2*o))&1 for o in range(5)); ndn=sum((s>>(2*o+1))&1 for o in range(5))
        Sz[col]=0.5*(nup-ndn)
    Sp=np.zeros((N,N))
    for col,s in enumerate(basis):
        for o in range(5):
            ns,sg=apply_ops(s,[('c',2*o),('a',2*o+1)])
            if ns is not None: Sp[idx[ns],col]+=sg
    S2=Sp.T@Sp + np.diag(Sz**2) - np.diag(Sz)   # S^2 = S-S+ + Sz^2 + Sz with S-S+ = (S+)^T S+ ; using Sz^2 - Sz? check below
    return S2, Sz, Sp
