import numpy as np, itertools
from sympy.physics.wigner import gaunt
from functools import lru_cache

ms = [-2,-1,0,1,2]
so = [(m,s) for m in ms for s in (1,-1)]
N = len(so)
@lru_cache(None)
def G(l1,l2,l3,m1,m2,m3):
    return float(gaunt(l1,l2,l3,m1,m2,m3))
def gfun(ma,mc,k,q):
    return (-1)**(ma+q)*G(2,2,k,-ma,mc,-q) if (-ma+mc-q)==0 else 0.0
def ffun(mb,md,k,q):
    return (-1)**mb*G(2,2,k,-mb,md,q) if (-mb+md+q)==0 else 0.0
def Vang(k):
    A = np.zeros((5,5,5,5))
    for ia,ma in enumerate(ms):
        for ic,mc in enumerate(ms):
            for ib,mb in enumerate(ms):
                for id_,md in enumerate(ms):
                    s=0.0
                    for q in range(-k,k+1):
                        s += gfun(ma,mc,k,q)*ffun(mb,md,k,q)
                    A[ia,ic,ib,id_] = 4*np.pi/(2*k+1)*s
    return A
AV = {k:Vang(k) for k in (0,2,4)}
def Vmat(F2,F4):
    F={0:0.0,2:F2,4:F4}
    V = np.zeros((N,N,N,N))
    for a,(ma,sa) in enumerate(so):
        for b,(mb,sb) in enumerate(so):
            for c,(mc,sc) in enumerate(so):
                for d,(md,sd) in enumerate(so):
                    if sa!=sc or sb!=sd: continue
                    val=0.0
                    for k in (2,4):
                        val += F[k]*AV[k][ms.index(ma),ms.index(mc),ms.index(mb),ms.index(md)]
                    V[a,b,c,d]=val
    return V
def cf_matrix(Dq):
    idx = {m:i for i,m in enumerate(ms)}
    eg = np.zeros((5,2),complex)
    eg[idx[0],0]=1
    eg[idx[2],1]=1/np.sqrt(2); eg[idx[-2],1]=1/np.sqrt(2)
    t2 = np.zeros((5,3),complex)
    t2[idx[1],0]=1; t2[idx[-1],1]=1
    t2[idx[2],2]=1/np.sqrt(2); t2[idx[-2],2]=-1/np.sqrt(2)
    Peg = eg@eg.conj().T; Pt = t2@t2.conj().T
    return 6*Dq*Peg - 4*Dq*Pt
states = list(itertools.combinations(range(N),3))
sidx = {s:i for i,s in enumerate(states)}
def apply_ops(occ, ops):
    occ=list(occ); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in occ: return None
            p = occ.index(i); sign *= (-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            p = sum(1 for x in occ if x<i); sign *= (-1)**p; occ.insert(p,i)
    return sign, tuple(occ)
def build_H(Dq,B,C):
    F4 = 441*C/35.0
    F2 = 49*B + 7*C
    V = Vmat(F2,F4)
    h = cf_matrix(Dq)
    hs = np.zeros((N,N),complex)
    for a,(ma,sa) in enumerate(so):
        for b,(mb,sb) in enumerate(so):
            if sa==sb: hs[a,b]=h[ms.index(ma),ms.index(mb)]
    H = np.zeros((len(states),len(states)),complex)
    for j,s in enumerate(states):
        for a in range(N):
            for b in range(N):
                if hs[a,b]==0: continue
                r = apply_ops(s,[('c',a),('a',b)])
                if r is None: continue
                sg,ns = r
                H[sidx[ns],j] += sg*hs[a,b]
        for a in range(N):
            for b in range(N):
                for c in range(N):
                    for d in range(N):
                        v = V[a,b,c,d]
                        if v==0: continue
                        r = apply_ops(s,[('c',a),('c',b),('a',d),('a',c)])
                        if r is None: continue
                        sg,ns = r
                        H[sidx[ns],j] += 0.5*sg*v
    return H
