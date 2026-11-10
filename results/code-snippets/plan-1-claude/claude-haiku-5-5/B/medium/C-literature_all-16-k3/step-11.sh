
cat << 'EOF' | python3 -
import numpy as np
from scipy.special import sph_harm_y as SY
from scipy.optimize import least_squares
nth, nph = 30, 60
x, w = np.polynomial.legendre.leggauss(nth)
th = np.arccos(x); ph = np.linspace(0, 2*np.pi, nph, endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nph))*(2*np.pi/nph)
ms = list(range(-2,3))
Ylm = {m: SY(2,m,TH,PH) for m in ms}
def ang_k(k):
    A = np.zeros((5,5,5,5), complex)
    for q in range(-k,k+1):
        Yq = SY(k,q,TH,PH)
        P1 = np.array([[np.sum(W*np.conj(Ylm[a])*np.conj(Yq)*Ylm[c]) for c in ms] for a in ms])
        P2 = np.array([[np.sum(W*np.conj(Ylm[b])*Yq*Ylm[d]) for d in ms] for b in ms])
        A += (4*np.pi/(2*k+1))*np.einsum('ac,bd->abcd', P1, P2)
    return A.real
A = {k:ang_k(k) for k in (0,2,4)}
states = [st for st in range(1<<10) if bin(st).count('1')==8]
index = {st:i for i,st in enumerate(states)}; n=len(states)
def ann(i,st):
    if not (st>>i)&1: return None
    return (-1)**bin(st & ((1<<i)-1)).count('1'), st ^ (1<<i)
def cre(i,st):
    if (st>>i)&1: return None
    return (-1)**bin(st & ((1<<i)-1)).count('1'), st | (1<<i)
def op2(a,b,c,d):  # proper c+_a c+_b c_d c_c  (c applied first)
    M = np.zeros((n,n))
    for st in states:
        r=ann(c,st)
        if r is None: continue
        s1,t=r; r=ann(d,t)
        if r is None: continue
        s2,t=r; r=cre(b,t)
        if r is None: continue
        s3,t=r; r=cre(a,t)
        if r is None: continue
        s4,t=r
        M[index[t],index[st]] += s1*s2*s3*s4
    return M
so=lambda o,s: 2*o+s
def Hee(Am):
    H=np.zeros((n,n))
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        v=Am[a,b,c,d]
        if abs(v)<1e-12: continue
        for s in (0,1):
         for t in (0,1):
          # c+_{a s} c+_{b t} c_{d t} c_{c s}: rightmost c_{c s} first -> pass (c,s) as 'd' slot
          H += 0.5*v*op2(so(a,s),so(b,t),so(c,s),so(d,t))
    return H
H0=Hee(A[0]); print("F0 const", np.round(np.linalg.eigvalsh(H0)[[0,-1]],6))
H2=Hee(A[2]); H4=Hee(A[4])
np.savez
Sz = np.array([sum(((st>>(2*o))&1)-((st>>(2*o+1))&1) for o in range(5)) for st in states])
iz=np.where(Sz==2)[0]; i0=np.where(Sz==0)[0]
# free ion with B=1,C=0 etc: F2=49B+7C,F4=12.6C
def fi(B,C):
    H = (49*B+7*C)*H2 + 12.6*C*H4
    et=np.sort(np.linalg.eigvalsh(H[np.ix_(iz,iz)]))
    ez=np.sort(np.linalg.eigvalsh(H[np.ix_(i0,i0)]))
    return et,ez
et,ez=fi(1000,4000)
print("triplet", np.round(et-et[0],1))
print("Sz0 all", np.round(ez-et[0],1))
EOF
