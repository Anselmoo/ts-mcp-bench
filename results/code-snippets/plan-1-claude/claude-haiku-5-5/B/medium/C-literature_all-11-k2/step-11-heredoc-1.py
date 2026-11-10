import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from math import sqrt
l=2; ms=list(range(-2,3))
def Ck(k,q,m,mp):
    if abs(q)>k: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*wigner_3j(l,k,l,0,0,0)*(2*l+1))
def Acoef(k,m1,m2,m3,m4):
    return sum((-1)**q*Ck(k,q,m1,m3)*Ck(k,-q,m2,m4) for q in range(-k,k+1))
Vk={k:np.zeros((5,5,5,5)) for k in (0,2,4)}
for k in (0,2,4):
    for i1,m1 in enumerate(ms):
        for i2,m2 in enumerate(ms):
            for i3,m3 in enumerate(ms):
                for i4,m4 in enumerate(ms):
                    if m1+m2==m3+m4: Vk[k][i1,i2,i3,i4]=Acoef(k,m1,m2,m3,m4)
s2=sqrt(2)
U=np.zeros((5,5),dtype=complex)
idx={m:i for i,m in enumerate(ms)}
U[0,idx[0]]=1
U[1,idx[2]]=1/s2; U[1,idx[-2]]=1/s2
U[2,idx[2]]=1/(1j*s2); U[2,idx[-2]]=-1/(1j*s2)
U[3,idx[1]]=1/s2; U[3,idx[-1]]=-1/s2
U[4,idx[1]]=1/(1j*s2); U[4,idx[-1]]=1/(1j*s2)
Vr={k:np.einsum('aw,bx,cy,dz,wxyz->abcd',U.conj(),U.conj(),U,U,Vk[k]).real for k in Vk}
states=list(itertools.combinations(range(10),6))
sidx={s:i for i,s in enumerate(states)}
def apply_ops(ops,state):
    occ=list(state); sign=1
    for (p,dag) in reversed(ops):
        n=sum(1 for o in occ if o<p)
        if dag:
            if p in occ: return None,0
            sign*=(-1)**n; occ.append(p); occ.sort()
        else:
            if p not in occ: return None,0
            sign*=(-1)**n; occ.remove(p)
    return tuple(occ),sign
N=len(states)
F2=1.0; F4=0.0
Vs=Vr[2]*F2
H=np.zeros((N,N))
quads=[(a,b,c,d) for a in range(10) for b in range(10) for c in range(10) for d in range(10) if a%2==c%2 and b%2==d%2]
for j,st in enumerate(states):
    for (a,b,c,d) in quads:
        v=Vs[a//2,b//2,c//2,d//2]
        if abs(v)<1e-12: continue
        new,sg=apply_ops([(a,True),(c,True),(d,False),(b,False)],st)
        if new is not None: H[sidx[new],j]+=0.5*sg*v
print("nonzero H:",np.count_nonzero(np.abs(H)>1e-12), "maxabs",np.abs(H).max())
print("sym err", np.abs(H-H.T).max())
print(np.round(np.linalg.eigvalsh(H)[:20],4))
