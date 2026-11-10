import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * int Y*_{m1} Y_{k,m1-m2} Y_{m2}
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def eri(a,b,c,d,F):  # <ab|cd> spatial, m values
    if a+b!=c+d: return 0.
    return sum(F[k]*CK[(k,a,c)]*CK[(k,d,b)] for k in (0,2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),6))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,C):
    F4=C*441/35; F2=49*(B+5*F4/441); F={0:0,2:F2,4:F4}
    h=np.zeros((5,5))
    for i,m in enumerate(ms):
        h[i,i]={0:6,1:-4,2:1}[abs(m)]*Dq
    h[0,4]=h[4,0]=5*Dq
    hs=np.zeros((10,10)); 
    for p in range(10):
        for q in range(10):
            if so[p][1]==so[q][1]: hs[p,q]=h[ms.index(so[p][0]),ms.index(so[q][0])]
    g=np.zeros((10,)*4)
    for p,q,r,s in itertools.product(range(10),repeat=4):
        if so[p][1]==so[r][1] and so[q][1]==so[s][1]:
            g[p,q,r,s]=eri(so[p][0],so[q][0],so[r][0],so[s][0],F)
    H=np.zeros((len(dets),)*2)
    for I,D in enumerate(dets):
        # apply H via second quantization
        occ=list(D)
        for p in range(10):
            for q in range(10):
                if hs[p,q]==0: continue
                r=apply([(p,1),(q,0)],occ)
                if r: H[idx[r[1]],I]+=r[0]*hs[p,q]
        for p in range(10):
         for q in range(10):
          for r_ in occ:
           for s in occ:
            v=g[p,q,r_,s]
            if v==0: continue
            r=apply([(p,1),(q,1),(s,0),(r_,0)],occ)
            if r: H[idx[r[1]],I]+=0.5*r[0]*v
    return H
def apply(ops,occ):
    occ=list(occ); sign=1
    for o,cr in reversed(ops):
        if cr:
            if o in occ: return None
            n=sum(1 for x in occ if x<o); sign*=(-1)**n; occ.append(o); occ.sort()
        else:
            if o not in occ: return None
            n=sum(1 for x in occ if x<o); sign*=(-1)**n; occ.remove(o)
    return sign,tuple(occ)
# S^2 for spin labeling
def S2():
    M=np.zeros((len(dets),)*2)
    for I,D in enumerate(dets):
        na=sum(1 for o in D if so[o][1]==0); nb=6-na
        sz=(na-nb)/2; M[I,I]+=sz*sz+sz  # S-S+ + Sz^2+Sz ; S^2 = S-S+ + Sz(Sz+1)
        for p in range(10):
         for q in range(10):
          if so[p][0]==so[q][0] and so[p][1]==1 and so[q][1]==1:
            for r_ in range(10):
             for s in range(10):
              if so[r_][0]==so[s][0] and so[r_][1]==0 and so[s][1]==0 and False: pass
    return M
import pickle
