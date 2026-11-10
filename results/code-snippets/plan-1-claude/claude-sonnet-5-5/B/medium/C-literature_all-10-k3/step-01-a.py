import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,l,m1,l2,m2):
    # <l m1|C^k_q|l m2>, q=m1-m2
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt((2*l+1)*(2*l2+1))*__import__('sympy.physics.wigner',fromlist=['x']).wigner_3j(l,k,l2,0,0,0)*__import__('sympy.physics.wigner',fromlist=['x']).wigner_3j(l,k,l2,-m1,q,m2))
from sympy.physics.wigner import wigner_3j
def ckk(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
# orbitals idx: (m,s)
so=[(m,s) for m in ms for s in (0,1)]
n=10
C={k:np.array([[ckk(k,a,b) for b in ms] for a in ms]) for k in (0,2,4)}
def build():
    # V[a,b,c,d]=sum_k ck(a,c)ck(d,b) F^k  : <ab|1/r|cd> = sum_k c^k(a,c)c^k(b,d)... use standard: <ab|g|cd>=sum_k c^k(la ma,lc mc) c^k(ld md, lb mb) F^k
    pass
dets=[d for d in itertools.combinations(range(10),6)]
idx={d:i for i,d in enumerate(dets)}
def ham(Dq,B,Cc):
    F={2:49*B+7*Cc,4:1.4*Cc}
    ca={k:C[k] for k in F}
    # integrals <ab|cd> over orbitals m
    I=np.zeros((5,)*4)
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        if ms[a]+ms[b]!=ms[c]+ms[d]: continue
        I[a,b,c,d]=sum(ca[k][a,c]*ca[k][d,b]*F[k] for k in F)
    h=np.zeros((5,5))
    for m,v in zip(ms,[Dq,-4*Dq,6*Dq,-4*Dq,Dq]): h[m+2,m+2]=v
    h[0,4]=h[4,0]=5*Dq
    N=len(dets); H=np.zeros((N,N))
    # build via operators
    def apply(op_list,det):
        # op_list: list of (type,orb) applied right to left; returns (sign,newdet) 
        occ=list(det); sign=1
        for t,o in reversed(op_list):
            if t=='a':
                if o not in occ: return 0,None
                p=occ.index(o); sign*=(-1)**p; occ.pop(p)
            else:
                if o in occ: return 0,None
                p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
        return sign,tuple(occ)
    for det in dets:
        j=idx[det]
        for p in range(10):
         for q in range(10):
          if so[p][1]!=so[q][1]: continue
          v=h[so[p][0]+2,so[q][0]+2]
          if v==0: continue
          s,nd=apply([('c',p),('a',q)],det)
          if s: H[idx[nd],j]+=s*v
        for p in range(10):
         for q in range(10):
          for r in range(10):
           for t in range(10):
            # 1/2 sum <pq|rt> c+p c+q a_t a_r
            if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]: continue
            v=I[so[p][0]+2,so[q][0]+2,so[r][0]+2,so[t][0]+2]
            if v==0: continue
            s,nd=apply([('c',p),('c',q),('a',t),('a',r)],det)
            if s: H[idx[nd],j]+=0.5*s*v
    return H
# S^2
def S2():
    N=len(dets);M=np.zeros((N,N))
    for det in dets:
        j=idx[det]
        nu=sum(1 for x in det if x%2==0); nd=6-nu
        Sz=(nu-nd)/2
        M[j,j]+=Sz*Sz+Sz
        # S- S+ : S+ flips down->up
        for m in ms:
            a=2*(m+2); b=a+1  # up=a (s=0), down=b
            pass
    return M
