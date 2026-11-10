import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
from sympy import N as sN
l=2
ms=[-2,-1,0,1,2]
# spatial orbital index: 0..4 -> m=-2..2 ; spin-orbital = 2*sp + s (s=0 up,1 down)
G={}
def gnt(m1,k,m2,m3,q):
    key=(m1,k,m2,m3,q)
    if key not in G: G[key]=float(sN(gaunt(l,k,l,m1,q,m2)))
    return G[key]
def Cmat(k,q):
    # <m_a|C^k_q|m_c> matrix (5x5)
    M=np.zeros((5,5))
    for i,ma in enumerate(ms):
        for j,mc in enumerate(ms):
            if ma-mc==q:  # need -ma + q + mc = 0 -> q = ma-mc
                M[i,j]=np.sqrt(4*np.pi/(2*k+1))*(-1)**(ma%2)*gnt(-ma,k,mc,0,q) if False else 0
    return M
# direct computation: <a|C^k_q|c> = int Y_a^* C^k_q Y_c = sqrt(4pi/(2k+1)) (-1)^{ma} gaunt(l,k,l,-ma,q,mc), requires -ma+q+mc=0
def Cel(k,q,ma,mc):
    if -ma+q+mc!=0: return 0.0
    return np.sqrt(4*np.pi/(2*k+1))*(-1)**(ma%2 if ma>=0 else (-ma)%2)*float(sN(gaunt(l,k,l,-ma,q,mc)))
def Vel(a,b,c,d,F):
    # <ab|1/r12|cd> spatial, a,b,c,d are m values
    tot=0.0
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            s+= (-1)**(q%2)*Cel(k,q,a,c)*Cel(k,-q,b,d)
        tot+=F[k]*s
    return tot
def build(Dq,B,C):
    F4=441*C/35.0; F2=441*B+5*F4; F={0:0.0,2:F2,4:F4}
    # F0 set to 0 (constant shift)
    # one-electron CF in complex basis
    s2=np.sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[ms.index(m)]=c
        return v
    xy=vec({2:1/(1j*s2),-2:-1/(1j*s2)})
    yz=vec({1:1j/s2,-1:1j/s2})
    zx=vec({1:-1/s2,-1:1/s2})
    z2=vec({0:1})
    x2y2=vec({2:1/s2,-2:1/s2})
    t2=[xy,yz,zx]; eg=[z2,x2y2]
    Pt=sum(np.outer(v,v.conj()) for v in t2)
    Pe=sum(np.outer(v,v.conj()) for v in eg)
    h=-4*Dq*Pt+6*Dq*Pe
    # two-electron integrals in spin-orbital indices
    n=10
    V=np.zeros((n,n,n,n))
    for so_a in range(n):
        for so_b in range(n):
            for so_c in range(n):
                for so_d in range(n):
                    sa,ma_=so_a%2,so_a//2
                    sb,mb_=so_b%2,so_b//2
                    sc,mc_=so_c%2,so_c//2
                    sd,md_=so_d%2,so_d//2
                    if sa!=sc or sb!=sd: continue
                    V[so_a,so_b,so_c,so_d]=Vel(ms[ma_],ms[mb_],ms[mc_],ms[md_],F)
    # spin-orbital one-electron
    H1=np.zeros((n,n),complex)
    for i in range(n):
        for j in range(n):
            if i%2==j%2: H1[i,j]=h[i//2,j//2]
    return H1,V
def apply_ops(state,terms):
    pass
def fermi(det,ops):
    # ops: list of ('c',i) or ('a',i) applied right to left; det: tuple sorted occupied
    occ=list(det); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in occ: return None,0
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
def basis(Ms2):
    # Ms2 = 2*Ms: 3 for quartet max, 1 for Ms=1/2
    dets=[]
    for c in itertools.combinations(range(10),3):
        nup=sum(1 for i in c if i%2==0); ndn=3-nup
        if nup-ndn==Ms2: dets.append(c)
    return dets
def Hmat(dets,H1,V):
    idx={d:i for i,d in enumerate(dets)}
    M=np.zeros((len(dets),len(dets)),complex)
    n=10
    for j,d in enumerate(dets):
        # one-electron
        for a in range(20):
            for b in range(20):
                pass
        # one-electron part: sum_ij H1[i,j] a_i^dag a_j
        for i in range(n):
            for jj in range(n):
                if H1[i,jj]==0: continue
                nd,s=fermi(d,[('c',i),('a',jj)])
                if nd is not None and nd in idx: M[idx[nd],j]+=H1[i,jj]*s
        # two-electron: 1/2 sum V_abcd a+a a+b a_d a_c
        for a in range(n):
          for b in range(n):
            for c in range(n):
              for dd in range(n):
                v=V[a,b,c,dd]
                if abs(v)<1e-12: continue
                nd,s=fermi(d,[('c',a),('c',b),('a',dd),('a',c)])
                if nd is not None and nd in idx: M[idx[nd],j]+=0.5*v*s
    return M
