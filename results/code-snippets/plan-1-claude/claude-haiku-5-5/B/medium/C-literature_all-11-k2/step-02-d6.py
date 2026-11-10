import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq, fsolve
from math import sqrt
l=2
ms=list(range(-2,3))
def ang(k,m1,m3):  # <l m1|C^k_q|l m3> as function of q
    pass
# Gaunt-like angular coefficient for Coulomb: A_k(m1,m2,m3,m4)=sum_q (-1)^q <m1|C^k_q|m3><m2|C^k_-q|m4>
def Ck(k,q,m,mp):
    if abs(q)>k: return 0.0
    return float((-1)**(l-m)*wigner_3j(l,k,l,-m,q,mp)*wigner_3j(l,k,l,0,0,0)*(2*l+1))
def Acoef(k,m1,m2,m3,m4):
    s=0.0
    for q in range(-k,k+1):
        s+=(-1)**q*Ck(k,q,m1,m3)*Ck(k,-q,m2,m4)
    return s
# complex-basis Coulomb tensor per F^k
Vk={k:np.zeros((5,5,5,5)) for k in (0,2,4)}
for k in (0,2,4):
    for i1,m1 in enumerate(ms):
        for i2,m2 in enumerate(ms):
            for i3,m3 in enumerate(ms):
                for i4,m4 in enumerate(ms):
                    if m1+m2!=m3+m4: continue
                    Vk[k][i1,i2,i3,i4]=Acoef(k,m1,m2,m3,m4)
# real orbital basis: rows = real orbitals in complex basis coefficients
s2=sqrt(2)
U=np.zeros((5,5),dtype=complex)  # order: z2, x2-y2, xy, xz, yz
idx={m:i for i,m in enumerate(ms)}
U[0,idx[0]]=1
U[1,idx[2]]=1/s2; U[1,idx[-2]]=1/s2
U[2,idx[2]]=1/(1j*s2); U[2,idx[-2]]=-1/(1j*s2)
U[3,idx[1]]=1/s2; U[3,idx[-1]]=-1/s2
U[4,idx[1]]=1/(1j*s2); U[4,idx[-1]]=1/(1j*s2)
def tor(V):
    # phi_a = sum_m U[a,m] |m>; <ab|cd>=sum conj(U_a m1) conj(U_b m2) U_c m3 U_d m4 V
    return np.einsum('aw,bx,cy,dz,wxyz->abcd',U.conj(),U.conj(),U,U,V)
Vr={k:tor(Vk[k]).real for k in Vk}
# check imaginary part small
for k in Vk: assert np.abs(tor(Vk[k]).imag).max()<1e-10
# spin orbitals: index = 2*orb + spin (0 up,1 down)
norb=5
states=[c for c in itertools.combinations(range(10),6)]
sidx={s:i for i,s in enumerate(states)}
def apply_ops(ops,state):
    # ops: list of (index, dagger bool) applied right-to-left as given in list order (leftmost first)
    occ=list(state); sign=1
    for (p,dag) in reversed(ops):
        if dag:
            if p in occ: return None,0
            # insert p: sign = (-1)^(number of occupied below p)
            n=sum(1 for o in occ if o<p)
            sign*= (-1)**n
            occ.append(p); occ.sort()
        else:
            if p not in occ: return None,0
            n=sum(1 for o in occ if o<p)
            sign*= (-1)**n
            occ.remove(p)
    return tuple(occ),sign
def build(Dq,B,C):
    F4=C*441/35.0
    F2=(B*441+5*F4)/9.0
    F0=0.0
    Vs=Vr[0]*F0+Vr[2]*F2+Vr[4]*F4
    # one-body cubic field: eg (orb 0,1) +6Dq, t2g (2,3,4) -4Dq
    h=np.diag([6*Dq,6*Dq,-4*Dq,-4*Dq,-4*Dq])
    N=len(states); H=np.zeros((N,N))
    for j,st in enumerate(states):
        # one-body
        for p in range(10):
            for q in range(10):
                if p%2!=q%2: continue
                hv=h[p//2,q//2]
                if hv==0: continue
                if p//2!=q//2 and hv==0: continue
                new,sg=apply_ops([(p,True),(q,False)],st)
                if new is None: continue
                H[sidx[new],j]+=sg*hv
        # two-body: 1/2 sum V_{abcd} a+_a a+_c a_d a_b  with spatial <ab|cd>, spins
        for a in range(10):
            for b in range(10):
                for c in range(10):
                    for d in range(10):
                        if a%2!=c%2 or b%2!=d%2: continue
                        v=Vs[a//2,b//2,c//2,d//2]
                        if abs(v)<1e-12: continue
                        new,sg=apply_ops([(a,True),(c,True),(d,False),(b,False)],st)
                        if new is None: continue
                        H[sidx[new],j]+=0.5*sg*v
    # S^2 operator and Ms=0 restriction
    S2=np.zeros((N,N))
    Sz=lambda s: 0.5*(1 if s%2==0 else -1)
    # S+ S- : S^2 = Sz^2 + (S+S- + S-S+)/2 ; build S+ S-
    for j,st in enumerate(states):
        # diagonal Sz^2 part with Ms
        Ms=sum(Sz(p) for p in st)
        S2[j,j]+=Ms**2
        for p in range(0,10,2):  # spin up orb p -> p+1 down? index 2*orb+spin
            pass
    S2=np.zeros((N,N))
    for j,st in enumerate(states):
        Ms=sum(Sz(p) for p in st)
        S2[j,j]+=Ms*Ms
        # S+ S- : sum_{i,k} a+_i up a_i' ... implement via S- S+ = sum_{ij} a+_{j dn}a_{j up}...
        for o1 in range(5):
            for o2 in range(5):
                # S+ S- = sum a+_{o1 up} a_{o1 dn} a+_{o2 dn} a_{o2 up}
                new,sg=apply_ops([(2*o1,True),(2*o1+1,False),(2*o2+1,True),(2*o2,False)],st)
                if new is not None: S2[sidx[new],j]+=sg
    return H,S2
def singlet_levels(Dq,B,C,n=4):
    H,S2=build(Dq,B,C)
    # Ms=0 subspace
    Ms0=[j for j,st in enumerate(states) if sum(1 if p%2==0 else -1 for p in st)==0]
    Hm=H[np.ix_(Ms0,Ms0)]; Sm=S2[np.ix_(Ms0,Ms0)]
    w,v=np.linalg.eigh(Sm)
    null=v[:,np.abs(w)<1e-8]
    Hs=null.T@Hm@null
    e,vec=np.linalg.eigh(Hs)
    return e[:n], vec, null, Ms0, H
if __name__=="__main__":
    e,_,_,_,_=singlet_levels(1000,1000,4500,n=12)
    print(np.round(e,1))
