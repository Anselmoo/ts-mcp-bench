import numpy as np, itertools
from scipy.special import eval_legendre
from scipy.integrate import quad
from numpy.polynomial.legendre import leggauss
# real d orbitals as functions on unit sphere
def dorb(th,ph):
    x=np.sin(th)*np.cos(ph); y=np.sin(th)*np.sin(ph); z=np.cos(th)
    return [np.sqrt(15)/2*x*y, np.sqrt(15)/2*y*z, np.sqrt(5)/4*(3*z*z-1), np.sqrt(15)/2*x*z, np.sqrt(15)/4*(x*x-y*y)]
# quadrature grid
nt,npz=24,48
xg,wg=leggauss(nt); th=np.arccos(xg); ph=np.arange(npz)*2*np.pi/npz; wph=2*np.pi/npz
pts=[];W=[];
for i in range(nt):
    for j in range(npz):
        pts.append((th[i],ph[j])); W.append(wg[i]*wph)
W=np.array(W)
Y=np.array([dorb(t,p) for t,p in pts])  # npts x 5
n=len(pts)
# unit vectors
U=np.array([[np.sin(t)*np.cos(p),np.sin(t)*np.sin(p),np.cos(t)] for t,p in pts])
cosg=U@U.T
# angular coefficients a_k[a,b,c,d] = sum_{i,j} W_i W_j Y_a(i)Y_c(i) Y_b(j) Y_d(j) P_k(cos g_ij)
Ks=[0,2,4]
P={k:eval_legendre(k,cosg) for k in Ks}
A={}
for k in Ks:
    # M[i,j] weights
    T=np.einsum('i,ia,ic->iac',W,Y,Y)  # orbital pair density on grid 1
    S=np.einsum('j,jb,jd->jbd',W,Y,Y)
    A[k]=np.einsum('iac,ij,jbd->abcd',T,P[k],S)
# spin orbitals: index s = 2*orb + spin
norb=5; nso=10
def g_spin(k):
    G=np.zeros((nso,nso,nso,nso))
    for a in range(nso):
        for b in range(nso):
            for c in range(nso):
                for d in range(nso):
                    if (a%2)==(c%2) and (b%2)==(d%2):
                        G[a,b,c,d]=A[k][a//2,b//2,c//2,d//2]
    return G
G={k:g_spin(k) for k in Ks}
# basis: 7 electrons in 10 spin orbitals
basis=[]
for occ in itertools.combinations(range(nso),7):
    basis.append(sum(1<<i for i in occ))
idx={b:i for i,b in enumerate(basis)}
N=len(basis)
def apply_cdag_c(p,q,state):
    # a_p^dag a_q |state>, returns (sign,newstate) or None
    if not (state>>q)&1: return None
    s=1
    st=state
    # annihilate q
    sign=(-1)**bin(st & ((1<<q)-1)).count('1'); st ^= (1<<q)
    if (st>>p)&1: return None
    sign*= (-1)**bin(st & ((1<<p)-1)).count('1'); st |= (1<<p)
    return sign*1, st
def build_op_2body(Gt):
    H=np.zeros((N,N))
    for j,b in enumerate(basis):
        for a_ in range(nso):
          for b_ in range(nso):
            for c in range(nso):
              for d in range(nso):
                g=Gt[a_,b_,c,d]
                if abs(g)<1e-12: continue
                # a†_a a†_b a_d a_c
                st=b; sign=1; ok=True
                # apply a_c
                if not (st>>c)&1: continue
                sg=(-1)**bin(st & ((1<<c)-1)).count('1'); st^=(1<<c); sign*=sg
                if not (st>>d)&1: continue
                sg=(-1)**bin(st & ((1<<d)-1)).count('1'); st^=(1<<d); sign*=sg
                if (st>>b_)&1: continue
                sg=(-1)**bin(st & ((1<<b_)-1)).count('1'); st|=(1<<b_); sign*=sg
                if (st>>a_)&1: continue
                sg=(-1)**bin(st & ((1<<a_)-1)).count('1'); st|=(1<<a_); sign*=sg
                H[idx[st],j]+=0.5*g*sign
    return H
def build_1body(h):
    H=np.zeros((N,N))
    for j,b in enumerate(basis):
        for p in range(nso):
            for q in range(nso):
                if abs(h[p,q])<1e-14: continue
                r=apply_cdag_c(p,q,b)
                if r is None: continue
                sg,st=r
                H[idx[st],j]+=h[p,q]*sg
    return H
# octahedral one-electron potential: x^4+y^4+z^4 - 3/5 r^4 on unit sphere
Vang=np.array([ (U[:,0]**4+U[:,1]**4+U[:,2]**4-0.6) ])[0]
M=np.einsum('i,ia,ib->ab',W*Vang,Y,Y)
ev=np.linalg.eigvalsh(M)
print("one-electron eigen",ev)
# eg = higher pair (2), t2g = lower triplet
et=ev[0:3].mean(); ee=ev[3:5].mean()
# orbital indices: real d-orbitals assumed; find via eigen of M for generic check
np.save('/tmp/M.npy',M)
