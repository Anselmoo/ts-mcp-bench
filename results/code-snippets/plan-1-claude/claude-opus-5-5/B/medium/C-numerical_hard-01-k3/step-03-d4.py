import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]  # s=1 alpha
def ck(k,m1,m2): return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
Ck={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
dets=[d for d in itertools.combinations(range(10),4) if sum(so[i][1] for i in d)==3]
idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def apply_ann(state,p):
    # state tuple sorted; returns (sign,newstate) or None
    if p not in state: return None
    i=state.index(p); return ((-1)**i, state[:i]+state[i+1:])
def apply_cre(state,p):
    if p in state: return None
    L=sorted(state+(p,)); i=L.index(p); return ((-1)**i, tuple(L))
def op_string(state,ops):  # ops list applied right to left: [(type,p),...] last first
    sg=1
    for t,p in reversed(ops):
        r=apply_cre(state,p) if t=='c' else apply_ann(state,p)
        if r is None: return None
        sg*=r[0]; state=r[1]
    return sg,state
# precompute one-body and two-body operator matrices in basis
def onebody(mat):
    M=np.zeros((N,N))
    for I,D in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if mat[p,q]==0: continue
                r=op_string(D,[('c',p),('a',q)])
                if r: M[idx[r[1]],I]+=r[0]*mat[p,q]
    return M
def twobody(k):
    M=np.zeros((N,N))
    for I,D in enumerate(dets):
        for p in range(10):
          for q in range(10):
            for r_ in range(10):
              for s in range(10):
                (a,sa),(b,sb),(c,sc),(d,sd)=so[p],so[q],so[r_],so[s]
                if sa!=sc or sb!=sd or a+b!=c+d: continue
                v=Ck[(k,a,c)]*Ck[(k,d,b)]
                if v==0: continue
                r=op_string(D,[('c',p),('c',q),('a',s),('a',r_)])
                if r: M[idx[r[1]],I]+=0.5*r[0]*v
    return M
cf=np.zeros((10,10)); dq={-2:1,-1:-4,0:6,1:-4,2:1}
for i,(m,s) in enumerate(so):
    for j,(m2,s2) in enumerate(so):
        if s!=s2: continue
        if m==m2: cf[i,j]=dq[m]
        if abs(m-m2)==4: cf[i,j]=5
VCF=onebody(cf); G2=twobody(2); G4=twobody(4)
# S^2 = S-S+ + Sz^2 + Sz, Sz=1
Sp=np.zeros((10,10)); Sm=np.zeros((10,10))
for i,(m,s) in enumerate(so):
    for j,(m2,s2) in enumerate(so):
        if m==m2 and s==1 and s2==0: Sp[i,j]=1
Spm=onebody(Sp); S2=Spm.T@Spm+2*np.eye(N)
np.savez('mats.npz',VCF=VCF,G2=G2,G4=G4,S2=S2)
