import numpy as np, itertools
from scipy.optimize import brentq
# angular quadrature on sphere
xg, wg = np.polynomial.legendre.leggauss(12)
phis = np.linspace(0, 2*np.pi, 24, endpoint=False)
pts=[]; ws=[]
for ct, w in zip(xg, wg):
    st = np.sqrt(1-ct*ct)
    for ph in phis:
        pts.append([st*np.cos(ph), st*np.sin(ph), ct]); ws.append(w*2*np.pi/len(phis))
P=np.array(pts); W=np.array(ws)
x,y,z=P.T
funcs=[x*y, y*z, x*z, 2*z*z-x*x-y*y, x*x-y*y]  # t2g: 0,1,2 ; eg: 3,4
# normalize
for i in range(5):
    n=np.sum(W*funcs[i]**2); funcs[i]=funcs[i]/np.sqrt(n)
F=np.array(funcs)  # 5 x npts
# Legendre P_k of cos gamma
def Pk(k, c):
    return np.polynomial.legendre.Legendre.basis(k)(c)
g = P@P.T  # cos between points
Ik={}
for k in [0,2,4]:
    Pm = Pk(k, np.clip(g,-1,1))
    # I_k[a,c,b,d] = sum_1,2 f_a(1) f_c(1) P_k f_b(2) f_d(2) W1 W2
    A = F*W  # weighted
    Ik[k]=np.einsum('ap,bq,pq,cp,dq->abcd', A, A, Pm, F, F, optimize=True)
    # note: uses f_a(1)W1 f_c(1) etc. ordering handled below
# spin-orbitals: index = 2*m + s  (m in 0..4, s 0/1)
norb=10
def sp(i): return i//2, i%2
# Coulomb V[i,j,k,l] = <ij|1/r|kl> = sum_k F^k Ik[mi,mk,mj,ml] * delta(si,sk)*delta(sj,sl)
# with Ik[a,c,b,d] = int f_a(1) f_c(1) P_k f_b(2) f_d(2): electron1 goes a->c? we define <i j| k l> = int phi_i*(1) phi_k(1) phi_j*(2) phi_l(2)
def V(i,j,k,l):
    mi,si=sp(i); mj,sj=sp(j); mk,sk=sp(k); ml,sl=sp(l)
    if si!=sk or sj!=sl: return 0.0
    return sum(Fk[kk]*Ik[kk][mi,mk,mj,ml] for kk in [0,2,4])
# Slater integrals: F4/F2 = 0.625; B=(9F2-5F4)/441, C=35F4/441
def slater(B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    return {0:1.0,2:F2,4:F4}  # F0 arbitrary
import sys
Bv=803.0; Cv=3078.0
Fk=slater(Bv,Cv)
# basis: 6 electrons among 10 spin-orbitals
states=[]
for occ in itertools.combinations(range(10),6):
    states.append(sum(1<<o for o in occ))
idx={s:i for i,s in enumerate(states)}
D=len(states)
def apply_cdag_c(p,q,s):
    # a_p^dag a_q on bitstring s; returns (sign,newstate) or None
    if not (s>>q)&1: return None
    sign=(-1)**bin(s & ((1<<q)-1)).count('1')
    s2=s & ~(1<<q)
    if (s2>>p)&1 and p!=q: return None
    sign2=(-1)**bin(s2 & ((1<<p)-1)).count('1')
    s3=s2 | (1<<p)
    if p==q: return (1,s)
    return (sign*sign2, s3)
# one-electron: diagonal ligand field, orbital energies
def build(Dq):
    h=np.zeros(5); h[0:3]=-4*Dq; h[3:5]=6*Dq
    H=np.zeros((D,D))
    # Coulomb: 1/2 sum V_ijkl a+_i a+_j a_l a_k
    for s in states:
        j0=idx[s]
        occ=[o for o in range(10) if (s>>o)&1]
        # diagonal one-body
        H[j0,j0]+=sum(h[o//2] for o in occ)
        # two-body: sum over i,j,k,l
        for k_ in occ:
            for l_ in occ:
                if l_==k_: continue
                # a_k a... careful: apply a_l then a_k to s, then a+_j, a+_i
                # operator a+_i a+_j a_l a_k with ordering
                pass
    return H
