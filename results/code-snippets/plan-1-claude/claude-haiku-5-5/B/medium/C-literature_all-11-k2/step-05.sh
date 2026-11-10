python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import fsolve
from math import sqrt
l=2
ms=list(range(-2,3))
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
                    if m1+m2==m3+m4:
                        Vk[k][i1,i2,i3,i4]=Acoef(k,m1,m2,m3,m4)
s2=sqrt(2)
U=np.zeros((5,5),dtype=complex)
idx={m:i for i,m in enumerate(ms)}
U[0,idx[0]]=1
U[1,idx[2]]=1/s2; U[1,idx[-2]]=1/s2
U[2,idx[2]]=1/(1j*s2); U[2,idx[-2]]=-1/(1j*s2)
U[3,idx[1]]=1/s2; U[3,idx[-1]]=-1/s2
U[4,idx[1]]=1/(1j*s2); U[4,idx[-1]]=1/(1j*s2)
def tor(V):
    return np.einsum('aw,bx,cy,dz,wxyz->abcd',U.conj(),U.conj(),U,U,V)
Vr={k:tor(Vk[k]).real for k in Vk}
for k in Vk: assert np.abs(tor(Vk[k]).imag).max()<1e-10
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
# precompute two-body operator list
quads=[]
for a in range(10):
  for b in range(10):
    for c in range(10):
      for d in range(10):
        if a%2!=c%2 or b%2!=d%2: continue
        quads.append((a,b,c,d))
N=len(states)
def build(Dq,B,C):
    F4=C*441/35.0
    F2=(B*441+5*F4)/9.0
    Vs=Vr[2]*F2+Vr[4]*F4
    h=np.diag([6*Dq,6*Dq,-4*Dq,-4*Dq,-4*Dq])
    H=np.zeros((N,N)); S2=np.zeros((N,N))
    for j,st in enumerate(states):
        for p in range(10):
            for q in range(10):
                if p%2!=q%2: continue
                hv=h[p//2,q//2]
                if hv==0: continue
                new,sg=apply_ops([(p,True),(q,False)],st)
                if new is not None: H[sidx[new],j]+=sg*hv
        for (a,b,c,d) in quads:
            v=Vs[a//2,b//2,c//2,d//2]
            if abs(v)<1e-12: continue
            new,sg=apply_ops([(a,True),(c,True),(d,False),(b,False)],st)
            if new is not None: H[sidx[new],j]+=0.5*sg*v
        Ms=sum(0.5 if p%2==0 else -0.5 for p in st)
        S2[j,j]+=Ms*Ms
        for o1 in range(5):
            for o2 in range(5):
                new,sg=apply_ops([(2*o1,True),(2*o1+1,False),(2*o2+1,True),(2*o2,False)],st)
                if new is not None: S2[sidx[new],j]+=sg
    return H,S2
Ms0=[j for j,st in enumerate(states) if sum(0.5 if p%2==0 else -0.5 for p in st)==0]
def singlets(Dq,B,C,n=12):
    H,S2=build(Dq,B,C)
    Hm=H[np.ix_(Ms0,Ms0)]; Sm=S2[np.ix_(Ms0,Ms0)]
    w,v=np.linalg.eigh(Sm)
    null=v[:,np.abs(w)<1e-8]
    e=np.linalg.eigvalsh(null.T@Hm@null)
    return e[:n]
e=singlets(1000,1000,4500)
print("free-check singlet levels (Dq=1000,B=1000,C=4500):")
print(np.round(e-e[0],1))
EOF