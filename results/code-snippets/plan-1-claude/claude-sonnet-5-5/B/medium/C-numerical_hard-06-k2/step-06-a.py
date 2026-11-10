import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from sympy import N
ms=[-2,-1,0,1,2]
def c(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float(N((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,q,mp)))
ck={k:{(a,b):c(k,a,b) for a in ms for b in ms} for k in (2,4)}
so=[(m,s) for m in ms for s in (0,1)]
n=10
dets=[d for d in itertools.combinations(range(n),6) if sum(so[i][1] for i in d)==3]
idx={d:i for i,d in enumerate(dets)}
N_=len(dets)
def ann(p,d):
    if p not in d: return None
    return (-1)**sum(1 for x in d if x<p), tuple(x for x in d if x!=p)
def cre(p,d):
    if p in d: return None
    return (-1)**sum(1 for x in d if x<p), tuple(sorted(d+(p,)))
def g(a,b,cc,d,k4):
    if a[1]!=cc[1] or b[1]!=d[1]: return 0
    return sum(k4[k]*ck[k][(a[0],cc[0])]*ck[k][(d[0],b[0])] for k in (2,4))
def two(F):
    G=np.zeros((n,n,n,n))
    for i in range(n):
     for j in range(n):
      for k in range(n):
       for l in range(n): G[i,j,k,l]=g(so[i],so[j],so[k],so[l],F)
    H=np.zeros((N_,N_))
    for di,d in enumerate(dets):
        for r_ in d:
         for s_ in d:
          if r_==s_: continue
          r1=ann(r_,d); r2=ann(s_,r1[1]); sg=r1[0]*r2[0]
          for p in range(n):
           for q in range(n):
            val=G[p,q,r_,s_]
            if abs(val)<1e-12: continue
            r3=cre(q,r2[1]); 
            if not r3: continue
            r4=cre(p,r3[1])
            if not r4: continue
            H[idx[r4[1]],di]+=0.5*val*sg*r3[0]*r4[0]
    return H
def one():
    h=np.zeros((5,5)); r=2**-.5
    for v in ([0,0,1,0,0],[r,0,0,0,r]): v=np.array(v);h+=10*np.outer(v,v)
    H=np.zeros((N_,N_))
    for di,d in enumerate(dets):
        for p in range(n):
         for q in range(n):
          if so[p][1]==so[q][1] and h[so[p][0]+2,so[q][0]+2]!=0:
            r1=ann(q,d)
            if r1:
                r2=cre(p,r1[1])
                if r2: H[idx[r2[1]],di]+=h[so[p][0]+2,so[q][0]+2]*r1[0]*r2[0]
    return H
# S^2 = S-S+ + Sz^2 + Sz ; Sz=0 -> S-S+
def S2():
    M=np.zeros((N_,N_)); 
    Sp=np.zeros((N_*0+N_,N_))
    # S+ maps to Ms=1 space; compute S-S+ = sum over orbital pairs: S-S+ = sum_{ij} a†_{i dn} a_{i up} a†_{j up} a_{j dn}
    for di,d in enumerate(dets):
        for j in range(5):
            dn=2*j; up=2*j+1  # so index: (m,s) s=0 first
            # so[2j]=(m,0), so[2j+1]=(m,1); treat s=1 as up
            r1=ann(dn,d)
            if not r1: continue
            r2=cre(up,r1[1])
            if not r2: continue
            s1=r1[0]*r2[0]; d1=r2[1]
            for i in range(5):
                r3=ann(2*i+1,d1)
                if not r3: continue
                r4=cre(2*i,r3[1])
                if not r4: continue
                M[idx[r4[1]],di]+=s1*r3[0]*r4[0]
    return M
HD=one(); HB=two({2:1,4:0}); HC=two({2:1/7,4:1/35}); 
HC=two({2:1/7,4:1/35}); HB=two({2:1,4:0})
S=S2()
np.save('<SANDBOX_TMP>/m.npy',np.array([HD,HB,HC,S]))
