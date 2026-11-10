cd /tmp && cat > ts.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
l=2
ms=[-2,-1,0,1,2]
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def ang(k,m,q,mp):
    if abs(q)>k or abs(m)>l or abs(mp)>l: return 0.0
    return (-1)**(l-m)*w3(l,k,l,-m,q,mp)*(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
def g(k,m1,m2,m3,m4):
    return sum((-1)**q*ang(k,m1,-q,m3)*ang(k,m2,q,m4) for q in range(-k,k+1))
def Vspat(F):
    V=np.zeros((5,5,5,5))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        m1,m2,m3,m4=ms[a],ms[b],ms[c],ms[d]
        if m1+m2!=m3+m4: continue
        V[a,b,c,d]=sum(Fk*g(k,m1,m2,m3,m4) for k,Fk in ((2,F[2]),(4,F[4])))
    return V
def hspat(Dq):
    idx={m:i for i,m in enumerate(ms)}
    v=np.zeros(5); v[idx[2]]=1/np.sqrt(2); v[idx[-2]]=1/np.sqrt(2)
    u=np.zeros(5); u[idx[2]]=1/np.sqrt(2); u[idx[-2]]=-1/np.sqrt(2)
    e0=np.zeros(5); e0[idx[0]]=1
    e1=np.zeros(5); e1[idx[1]]=1
    em1=np.zeros(5); em1[idx[-1]]=1
    Peg=np.outer(e0,e0)+np.outer(v,v)
    Pt2g=np.outer(e1,e1)+np.outer(em1,em1)+np.outer(u,u)
    return -4*Dq*Pt2g+6*Dq*Peg
states=[sum(1<<i for i in c) for c in itertools.combinations(range(10),6)]
sidx={s:i for i,s in enumerate(states)}
so=[(i//2, i%2) for i in range(10)]
def apply_ops(st, ops):
    s=st; sign=1
    for (i,dag) in ops:
        occ=(s>>i)&1
        if dag and occ: return None
        if (not dag) and (not occ): return None
        if bin(s & ((1<<i)-1)).count('1')%2: sign=-sign
        s ^= (1<<i)
    return sign,s
def build(Dq,B,C):
    F={2:49*B+5*C,4:9*C}
    V=Vspat(F); h=hspat(Dq)
    N=len(states); H=np.zeros((N,N))
    for col,st in enumerate(states):
        for i in range(10):
            for j in range(10):
                if so[i][1]!=so[j][1]: continue
                hv=h[so[i][0],so[j][0]]
                if abs(hv)<1e-14: continue
                r=apply_ops(st,[(i,True),(j,False)])
                if r is None: continue
                H[sidx[r[1]],col]+=r[0]*hv
        for a in range(10):
          for b in range(10):
            if a==b: continue
            for c in range(10):
              for d in range(10):
                if c==d: continue
                if so[a][1]!=so[c][1] or so[b][1]!=so[d][1]: continue
                v=V[so[a][0],so[b][0],so[c][0],so[d][0]]
                if abs(v)<1e-14: continue
                r=apply_ops(st,[(a,True),(b,True),(d,False),(c,False)])
                if r is None: continue
                H[sidx[r[1]],col]+=0.5*r[0]*v
    return H
# total spin S^2 operator in Fock basis via Sz and S+S-
def S2(N=None):
    Sz=np.zeros((210,210)); 
    for col,st in enumerate(states):
        sz=0
        for o in range(5):
            n_up=(st>>(2*o))&1; n_dn=(st>>(2*o+1))&1
            sz+=0.5*(n_up-n_dn)
        Sz[col,col]=sz
    # S+ = sum_o c+_{o,up} c_{o,dn}
    Sp=np.zeros((210,210))
    for col,st in enumerate(states):
        for o in range(5):
            r=apply_ops(st,[(2*o,True),(2*o+1,False)])
            if r is None: continue
            Sp[sidx[r[1]],col]+=r[0]
    Sm=Sp.T
    return Sm@Sp+Sz@Sz+Sz
if __name__=="__main__":
    H=build(0,1.0,4.0)
    w,U=np.linalg.eigh(H)
    S2m=S2()
    S2e=np.einsum('ia,ij,ja->a',U,S2m,U)
    vals=np.round(w,4)
    u=[]
    for v,s in zip(vals,S2e):
        if u and abs(u[-1][0]-v)<1e-3: u[-1][1]+=1; u[-1][2].append(round(s,2))
        else: u.append([v,1,[round(s,2)]])
    for x in u: print(x[0],x[1],set(x[2]))
EOF
python3 ts.py