mkdir -p /w && cat > /w/d5.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi, sqrt
from scipy.optimize import brentq
from functools import lru_cache

B, C = 621.0, 2851.0
F2 = 49*B + 7*C
F4 = 63*C/5
Fk = {0:0.0, 2:F2, 4:F4}
ms = list(range(-2,3))

@lru_cache(None)
def G(m1,m2,m3,k,l=2):  # gaunt for (l,k,l) with m's
    return float(gaunt(l,k,l,m1,m2,m3))

def V2(m1,m2,m3,m4):
    # <m1 m2|1/r12|m3 m4>
    tot=0.0
    if m1+m2!=m3+m4: return 0.0
    for k in (0,2,4):
        s=0.0
        for q in range(-k,k+1):
            if abs(m1-m3+0)>2*0 and False: pass
            if abs(-m1-q)>2 or abs(m3)>2 or abs(-m2+q)>2 : pass
            # electron1: (-1)^(m1+q) G(-m1,-q,m3); electron2: (-1)^m2 G(-m2,q,m4)
            if abs(-m1)>2 or abs(-q)>k or abs(m3)>2: continue
            if abs(-m2)>2 or abs(q)>k or abs(m4)>2: continue
            g1=float(gaunt(2,k,2,-m1,-q,m3)) if abs(-q)<=k and abs(-m1+(-q)*0)<=2 else 0.0
            g2=float(gaunt(2,k,2,-m2,q,m4)) if abs(q)<=k else 0.0
            s+= (-1)**(m1+q) * g1 * (-1)**m2 * g2
        tot += Fk[k]*4*pi/(2*k+1)*s
    return tot

# one-electron cubic field operator: Y40 + sqrt(5/14)(Y44+Y4-4)
from sympy import Integer
def Ymat(q):
    M=np.zeros((5,5))
    for i,m1 in enumerate(ms):
        for j,m2 in enumerate(ms):
            if m1 - m2 != q*0 and -m1+q+m2 !=0: continue
            M[i,j]=(-1)**m1*float(gaunt(2,4,2,-m1,q,m2))
    return M
# complex; build full operator with complex entries
def Yc(q):
    M=np.zeros((5,5),dtype=complex)
    for i,m1 in enumerate(ms):
        for j,m2 in enumerate(ms):
            if -m1+q+m2!=0: continue
            M[i,j]=(-1)**m1*float(gaunt(2,4,2,-m1,q,m2))
    return M
Op = Yc(0) + sqrt(5/14)*(Yc(4)+Yc(-4))
w,U = np.linalg.eigh(Op)
print("cubic eigenvalues (Y40 ref):", np.round(w,4))
# t2g = lower triplet, eg = upper doublet; scale: h = a*Op with t2g->-4Dq, eg->+6Dq
# Use Op eigen: low triplet value t, high doublet value e: a*(e-t)=10 Dq ; choose shift so barycenter 0
t = w[0]; e = w[-1]
# Build one-electron matrix h(Dq) = Dq*(c1*Op + c0*I)
c1 = 10.0/(e-t)
c0 = -4 - c1*t   # so t2g: c1*t+c0=-4 ; eg: c1*e+c0 = 6
print("check t2g,eg:", c1*w[0]+c0, c1*w[-1]+c0)
Hcf_unit = c1*Op + c0*np.eye(5)  # multiply by Dq

# Fock space
norb=10
def idx(orb,s): return 2*orb+s  # s=0 up,1 down
# spin orbital list
so=[(ms[i//2] if False else ms[(i)//2], (i)%2) for i in range(10)]
N=10
dim=2**N
def occ_states(n):
    return [s for s in range(dim) if bin(s).count('1')==n]
sts=occ_states(5)
pos={s:i for i,s in enumerate(sts)}
D=len(sts)
def cdag_c(a,b):
    # c_a^dag c_b on basis of N=5 states
    M=np.zeros((D,D))
    for s in sts:
        if not (s>>b)&1: continue
        s1 = s ^ (1<<b)
        sign = (-1)**bin(s1 & ((1<<b)-1)).count('1')
        if (s1>>a)&1: continue
        s2 = s1 | (1<<a)
        sign *= (-1)**bin(s2 & ((1<<a)-1)).count('1')
        M[pos[s2],pos[s]] += sign
    return M
# one-body
Hcf = np.zeros((D,D),dtype=complex)  # per unit Dq
Hee = np.zeros((D,D))
# prebuild c†a c_b
CC={}
for a in range(N):
    for b in range(N):
        CC[(a,b)] = cdag_c(a,b)
for a in range(N):
    for b in range(N):
        ma,sa=ms[a//2],a%2; mb,sb=ms[b//2],b%2
        if sa!=sb: continue
        Hcf += Hcf_unit[a//2, b//2] * CC[(a,b)]
# two-body: 1/2 sum <ab|V|cd> c†_a c†_b c_d c_c
def cdcd(a,b,c,d):
    # c†_a c†_b c_d c_c = c†_a (c†_b c_d) c_c
    # compute as product of matrices
    return CC[(a,b)]  # placeholder
Vsum = np.zeros((D,D))
# use product: c†_a c†_b c_d c_c = (c†_a c_c)(c†_b c_d) - delta_bc c†_a c_d
for a in range(N):
  for b in range(N):
    for c in range(N):
      for d in range(N):
        ma,sa=ms[a//2],a%2; mb,sb=ms[b//2],b%2
        mc,sc=ms[c//2],c%2; md,sd=ms[d//2],d%2
        if sa!=sc or sb!=sd: continue
        v = V2(ma,mb,mc,md)
        if abs(v)<1e-12: continue
        # c†_a c†_b c_d c_c
        if b==c:
            # c†_a c†_b c_d c_c with b==c : c†_b c_d c_c... use normal product
            pass
        M = CC[(a,c)] @ CC[(b,d)]
        # careful: c†_a c†_b c_d c_c = c†_a (c†_b c_d) c_c  -> reorder via anticommutation
        # Use the identity: c†_a c†_b c_d c_c = c†_a (δ_bc - c_c c†_b) c_d... simpler build directly:
        Vsum += 0.5*v*(CDAG(a,b,c,d) if False else 0)
EOF
echo