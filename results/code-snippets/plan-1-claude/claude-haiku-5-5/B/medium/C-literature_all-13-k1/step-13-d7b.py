import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N as sN
from functools import lru_cache
from math import pi
from d7 import ang, gnt
NSO=10
def mats():
    idx=lambda m: m+2
    h=np.zeros((5,5))
    h[idx(0),idx(0)]+=1
    for a in (2,-2):
        for b in (2,-2):
            h[idx(a),idx(b)]+=0.5
    h*=10.0   # per unit Dq
    H1=np.zeros((NSO,NSO))
    for m1 in range(-2,3):
        for m2 in range(-2,3):
            for s in (0,1):
                H1[2*(m1+2)+s,2*(m2+2)+s]=h[idx(m1),idx(m2)]
    Vk={2:np.zeros((NSO,)*4),4:np.zeros((NSO,)*4)}
    for i in range(NSO):
        for j in range(NSO):
            for k in range(NSO):
                for l in range(NSO):
                    if i%2!=k%2 or j%2!=l%2: continue
                    mi,mj,mk,ml=i//2-2,j//2-2,k//2-2,l//2-2
                    for kk in (2,4): Vk[kk][i,j,k,l]=ang(kk,mi,mj,mk,ml)
    basis=[sum(1<<i for i in c) for c in itertools.combinations(range(NSO),7)]
    index={b:n for n,b in enumerate(basis)}
    D=len(basis)
    def ann(x,st):
        if not (st>>x)&1: return None,0
        return st^(1<<x), (-1)**bin(st&((1<<x)-1)).count('1')
    def cre(x,st):
        if (st>>x)&1: return None,0
        return st|(1<<x), (-1)**bin(st&((1<<x)-1)).count('1')
    Hc=np.zeros((D,D)); H2=np.zeros((D,D)); H4=np.zeros((D,D))
    Hs={2:H2,4:H4}
    for n,b in enumerate(basis):
        for a in range(NSO):
            for c in range(NSO):
                if H1[a,c]==0: continue
                st,s1=ann(c,b)
                if st is None: continue
                st,s2=cre(a,st)
                if st is None: continue
                Hc[index[st],n]+=H1[a,c]*s1*s2
        for kk in (2,4):
            V=Vk[kk]
            for i in range(NSO):
                for j in range(NSO):
                    for k in range(NSO):
                        for l in range(NSO):
                            v=V[i,j,k,l]
                            if v==0 or i==j or k==l: continue
                            st,s1=ann(k,b)
                            if st is None: continue
                            st,s2=ann(l,st)
                            if st is None: continue
                            st,s3=cre(j,st)
                            if st is None: continue
                            st,s4=cre(i,st)
                            if st is None: continue
                            Hs[kk][index[st],n]+=0.5*v*s1*s2*s3*s4
    Sz=np.zeros((D,D)); Sp=np.zeros((D,D)); ML=np.zeros(D)
    for n,b in enumerate(basis):
        nu=sum((b>>(2*m))&1 for m in range(5)); nd=sum((b>>(2*m+1))&1 for m in range(5))
        Sz[n,n]=0.5*(nu-nd)
        ML[n]=sum((m-2)*(((b>>(2*m))&1)+((b>>(2*m+1))&1)) for m in range(5))
        for m in range(5):
            st,s1=ann(2*m+1,b)
            if st is None: continue
            st,s2=cre(2*m,st)
            if st is None: continue
            Sp[index[st],n]+=s1*s2
    S2=Sp.T@Sp+Sz@Sz+Sz
    return Hc,H2,H4,S2,ML
