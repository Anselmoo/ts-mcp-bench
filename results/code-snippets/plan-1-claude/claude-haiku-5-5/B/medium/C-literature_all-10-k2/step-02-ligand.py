import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt

def build(nel, F2, F4, Dq, ks=(0,2,4)):
    # complex d orbitals m=-2..2 index m+2
    ms=[-2,-1,0,1,2]
    Fk={0:0.0,2:F2,4:F4}
    V=np.zeros((5,5,5,5))  # <ab|V|cd> spatial
    for k in (2,4):
        C=np.zeros((5,5,5))  # <a|C^k_q|c>, q index q+k
        Ck={}
        for q in range(-k,k+1):
            M=np.zeros((5,5))
            for ia,ma in enumerate(ms):
                for ic,mc in enumerate(ms):
                    if ma-mc!=q: continue  # Gaunt needs ma = mc + q? conj(Y_ma) Y_kq Y_mc -> -ma+q+mc=0
                    g=float(gaunt(2,k,2,-ma,q,mc))*(-1)**ma
                    M[ia,ic]=sqrt(4*pi/(2*k+1))*g
            Ck[q]=M
        for a in range(5):
          for b in range(5):
            for c in range(5):
              for d in range(5):
                s=0.0
                for q in range(-k,k+1):
                    s+=(-1)**q*Ck[q][a,c]*Ck[-q][b,d]
                V[a,b,c,d]+=Fk[k]*s
    # one-body crystal field in complex basis
    h=np.zeros((5,5),dtype=complex)
    eg=[np.array([1,0,0,0,0]), np.array([0,0,0,0,0.])]
    v_eg=[np.eye(5)[2], (np.eye(5)[4]+np.eye(5)[0])/sqrt(2)]
    v_t2g=[(np.eye(5)[4]-np.eye(5)[0])/(1j*sqrt(2)), (np.eye(5)[3]-np.eye(5)[1])/sqrt(2), (np.eye(5)[3]+np.eye(5)[1])/(1j*sqrt(2))]
    for v in v_eg: h+=6*Dq*np.outer(v,v.conj())
    for v in v_t2g: h+=-4*Dq*np.outer(v,v.conj())
    # fermion space: 10 spin orbitals, index 2*orb+spin
    n=10
    dim=2**n
    def cdag_c(i,j):
        # c_i^dag c_j on Fock basis
        M=np.zeros((dim,dim))
        for s in range(dim):
            if not (s>>j)&1: continue
            sign=(-1)**bin(s & ((1<<j)-1)).count('1')
            s1=s ^ (1<<j)
            if (s1>>i)&1: continue
            sign*=(-1)**bin(s1 & ((1<<i)-1)).count('1')
            s2=s1 | (1<<i)
            M[s2,s]+=sign
        return M
    return V,h,cdag_c,dim
