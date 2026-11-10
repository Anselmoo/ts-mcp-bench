import numpy as np
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from scipy.optimize import brentq

B, C = 621.0, 2851.0
F2 = 49*B + 7*C
F4 = 63*C/5
Fk = {0:0.0, 2:F2, 4:F4}
ms = [-2,-1,0,1,2]
N = 10; dim = 2**N

def g(l1,l2,l3,m1,m2,m3):
    if abs(m1)>l1 or abs(m2)>l2 or abs(m3)>l3: return 0.0
    return float(gaunt(l1,l2,l3,m1,m2,m3))

def V2(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.0
    tot=0.0
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            g1=g(2,k,2,-m1,-q,m3)
            g2=g(2,k,2,-m2,q,m4)
            s += (-1)**(m1+q) * g1 * (-1)**m2 * g2
        tot += Fk[k]*4*pi/(2*k+1)*s
    return tot

def Yc(q):
    M=np.zeros((5,5),dtype=complex)
    for i,m1 in enumerate(ms):
        for j,m2 in enumerate(ms):
            if -m1+q+m2!=0: continue
            M[i,j]=(-1)**m1*g(2,4,2,-m1,q,m2)
    return M
Op = Yc(0) + sqrt(5/14)*(Yc(4)+Yc(-4))
w = np.linalg.eigvalsh(Op)
t, e = w[0], w[-1]
c1 = 10.0/(e-t); c0 = -4 - c1*t
h1 = c1*Op + c0*np.eye(5)
print("t2g/eg check:", np.round(np.diag(np.real(h1)),3) if np.allclose(h1,np.diag(np.diag(h1))) else np.round(np.linalg.eigvalsh(h1),3))

# fermion ops over 10 spin-orbitals, index a = 2*orb + spin  (spin 0=up,1=down)
def cop(a):
    M=np.zeros((dim,dim))
    for s in range(dim):
        if (s>>a)&1:
            sign=(-1)**bin(s & ((1<<a)-1)).count('1')
            M[s ^ (1<<a), s] = sign
    return M
C_ = [cop(a) for a in range(N)]
Cd = [m.T.copy() for m in C_]
# number conserving sector N=5
sel=[s for s in range(dim) if bin(s).count('1')==5]
def restrict(M): return M[np.ix_(sel,sel)]
Cd5=[restrict(m) for m in Cd]; C5=[restrict(m) for m in C_]
D=len(sel)
orb = lambda a: a//2; spn = lambda a: a%2
# one-body operator per Dq unit
H1 = np.zeros((D,D),dtype=complex)
for a in range(N):
  for b in range(N):
    if spn(a)!=spn(b): continue
    H1 += h1[orb(a),orb(b)] * (Cd5[a] @ C5[b])
# two-body
H2 = np.zeros((D,D))
for a in range(N):
 for b in range(N):
  for c in range(N):
   for d in range(N):
    if spn(a)!=spn(c) or spn(b)!=spn(d): continue
    v = V2(ms[orb(a)],ms[orb(b)],ms[orb(c)],ms[orb(d)])
    if abs(v)<1e-12: continue
    H2 += 0.5*v * (Cd5[a] @ Cd5[b] @ C5[d] @ C5[c])
# S^2
Sp = sum(Cd5[2*o] @ C5[2*o+1] for o in range(5))
Sz = 0.5*sum(Cd5[2*o]@C5[2*o]-Cd5[2*o+1]@C5[2*o+1] for o in range(5))
S2 = Sz@Sz + 0.5*(Sp@Sp.T + Sp.T@Sp)
print("H2 hermitian:", np.allclose(H2,H2.T))
mu=1e5
def levels(Dq):
    H = Dq*H1 + H2
    ev, vec = np.linalg.eigh(H + mu*S2)
    # classify by S
    out={}
    for val,v in zip(ev,vec.T):
        S2v = np.real(v.conj()@S2@v)
        S = round((-1+np.sqrt(1+4*S2v))/2*2)/2
        E = val - mu*S2v
        out.setdefault(S,[]).append(E)
    return {k:min(v) for k,v in out.items()}
for Dq in [0,500,1000,2000]:
    print(Dq, {k:round(v,1) for k,v in levels(Dq).items()})
