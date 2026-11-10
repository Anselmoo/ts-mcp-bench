import numpy as np, itertools
from scipy.optimize import least_squares
A = np.load('A.npy')  # A[k][a,c,b,d]
def build(nel, Dq, F0, F2, F4, dq_sign=1):
    # spin-orbital index s=2*o+sp
    basis = [sum(1<<s for s in c) for c in itertools.combinations(range(10), nel)]
    idx = {b:i for i,b in enumerate(basis)}
    D = len(basis)
    # one-electron h: t2g (xy,yz,zx = orb 0,1,2) -4Dq ; eg (orb 3,4) +6Dq
    h1 = np.array([-4*Dq]*3+[6*Dq]*2)
    # two-electron V[o1,o2,o3,o4] for orbital indices with <o1 o2|g|o3 o4> (electron1: o3->o1, electron2: o4->o2)
    Vo = F0*A[0] + F2*A[1] + F4*A[2]
    H = np.zeros((D,D))
    def apply_ann(state, s):
        if not (state>>s)&1: return None,0
        sign = (-1)**bin(state & ((1<<s)-1)).count('1')
        return state ^ (1<<s), sign
    def apply_cre(state, s):
        if (state>>s)&1: return None,0
        sign = (-1)**bin(state & ((1<<s)-1)).count('1')
        return state | (1<<s), sign
    for j,st in enumerate(basis):
        # one-electron
        for s in range(10):
            o, sp = divmod(s,2)
            if (st>>s)&1:
                H[j,j] += h1[o]
        # two-electron: 1/2 sum V a+_a a+_b a_d a_c
        for a in range(10):
          for c in range(10):
            oa,sa=divmod(a,2); oc,sc=divmod(c,2)
            if sa!=sc: continue
            for b in range(10):
              for d in range(10):
                ob,sb=divmod(b,2); od,sd=divmod(d,2)
                if sb!=sd: continue
                v = Vo[oa,oc,ob,od]
                if abs(v)<1e-14: continue
                s1, g1 = apply_ann(st, c)
                if g1==0: continue
                s2, g2 = apply_ann(s1, d)
                if g2==0: continue
                s3, g3 = apply_cre(s2, b)
                if g3==0: continue
                s4, g4 = apply_cre(s3, a)
                if g4==0: continue
                i = idx[s4]
                H[i,j] += 0.5*v*g1*g2*g3*g4
    return basis, H
def spin2(basis):
    # total S^2 expectation via S+S-: compute Sz and S^2 numerically
    D=len(basis); idx={b:i for i,b in enumerate(basis)}
    Sz = np.zeros(D)
    for j,st in enumerate(basis):
        n_up=sum(1 for o in range(5) if (st>>(2*o))&1)
        n_dn=sum(1 for o in range(5) if (st>>(2*o+1))&1)
        Sz[j]=0.5*(n_up-n_dn)
    return Sz
