import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache

ms = [-2,-1,0,1,2]
orbs = [(m,s) for m in ms for s in (0,1)]
NSO = 10
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))
def angular(k,ma,mb,mc,md):
    tot=0.0
    for q in range(-k,k+1):
        g1=G(2,k,2,-ma,-q,mc)
        if g1==0: continue
        g2=G(2,k,2,-mb,q,md)
        if g2==0: continue
        tot+= (-1)**(ma+q) * g1 * (-1)**mb * g2
    return 4*np.pi/(2*k+1)*tot
def build(B, C, Dq):
    F4 = 441*C/35.0
    F2 = 49*(B + 5*F4/441.0)
    F = {0:0.0, 2:F2, 4:F4}
    s2=np.sqrt(2)
    vecs_e = [np.array([0,0,1,0,0],complex), np.array([1,0,0,0,1],complex)/s2]
    vecs_t = [np.array([-1j,0,0,0,1j],complex)/s2, np.array([0,1,0,-1,0],complex)/s2, np.array([0,1j,0,1j,0],complex)/s2]
    h = np.zeros((5,5),complex)
    for v in vecs_e: h += -6*Dq*np.outer(v,v.conj())
    for v in vecs_t: h += 4*Dq*np.outer(v,v.conj())
    h1 = np.zeros((NSO,NSO),complex)
    for i,(m,s) in enumerate(orbs):
        for j,(mp,sp) in enumerate(orbs):
            if s==sp: h1[i,j]=h[ms.index(m),ms.index(mp)]
    V = np.zeros((NSO,)*4)
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2_) in enumerate(orbs):
            for k,(m3,s3) in enumerate(orbs):
                for l,(m4,s4) in enumerate(orbs):
                    if s1==s3 and s2_==s4:
                        V[i,j,k,l]=sum(F[kk]*angular(kk,m1,m2,m3,m4) for kk in (0,2,4))
    return h1,V
D = [occ for occ in itertools.combinations(range(NSO),8) if sum(1 for o in occ if orbs[o][1]==0)==5]
def apply_op(occ, ops):
    st=list(occ); sign=1
    for typ,idx in reversed(ops):
        if typ=='c':
            if idx in st: return None,0
            n=sum(1 for o in st if o<idx); sign*=(-1)**n
            st.append(idx); st.sort()
        else:
            if idx not in st: return None,0
            n=sum(1 for o in st if o<idx); sign*=(-1)**n
            st.remove(idx)
    return tuple(st),sign
def Hmat(B,C,Dq):
    h1,V = build(B,C,Dq)
    idx={d:i for i,d in enumerate(D)}
    H=np.zeros((len(D),len(D)),complex)
    for col,d in enumerate(D):
        for i in range(NSO):
            for j in range(NSO):
                if h1[i,j]!=0:
                    r,s=apply_op(d,[('c',i),('a',j)])
                    if r is not None: H[idx[r],col]+=h1[i,j]*s
        for i in range(NSO):
            for j in range(NSO):
                for k in range(NSO):
                    for l in range(NSO):
                        v=V[i,j,k,l]
                        if abs(v)<1e-12: continue
                        r,s=apply_op(d,[('c',i),('c',j),('a',l),('a',k)])
                        if r is not None: H[idx[r],col]+=0.5*v*s
    return H
def levels(B,C,Dq):
    H=Hmat(B,C,Dq)
    assert np.allclose(H,H.conj().T)
    return np.sort(np.linalg.eigvalsh(H).real)
if __name__=="__main__":
    print(len(D))
    print("free ion B=1000,C=4500:", np.round(levels(1000,4500,0),1))
    print("Dq=440:", np.round(levels(1000,4500,440),1))
