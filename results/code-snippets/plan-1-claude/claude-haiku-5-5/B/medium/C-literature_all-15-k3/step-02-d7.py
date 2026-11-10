import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2
# spin orbitals: (m, s) s=+1 / -1
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
N=len(orbs)
def c(ma,mb,k,q):
    # <l ma|C^k_q|l mb>
    if ma-mb!=-q and False: pass
    if -ma+q+mb!=0: return 0.0
    if abs(q)>k: return 0.0
    w1=float(wigner_3j(l,k,l,-ma,q,mb))
    w0=float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-ma)*w1*(-1)**l*(2*l+1)*w0
def Vspat(m1,m2,m3,m4,k):
    # <m1 m2|C^k(1).C^k(2)|m3 m4> angular part, sum over q
    tot=0.0
    for q in range(-k,k+1):
        tot+=(-1)**q*c(m1,m3,k,q)*c(m2,m4,k,-q)
    return tot
# Coulomb matrix elements in spin-orbital basis: <ab|V|cd> = sum_k F^k * ang * delta(spin a,c) delta(spin b,d)
ks={0:None,2:None,4:None}
def Vel(a,b,cc,d,k):
    ma,sa=orbs[a]; mb,sb=orbs[b]; mc,sc=orbs[cc]; md,sd=orbs[d]
    if sa!=sc or sb!=sd: return 0.0
    return Vspat(ma,mb,mc,md,k)
# build M_k as 2-body operator matrices in Slater determinant basis
dets=[d for d in itertools.combinations(range(N),7)]
idx={d:i for i,d in enumerate(dets)}
def apply_ops(occ, ops):
    # ops: list of (type,i) applied right to left; type 'c' creation, 'a' annihilation
    s=list(occ); sign=1
    for t,i in reversed(ops):
        if t=='a':
            if i not in s: return None,0
            p=s.index(i); sign*=(-1)**p; s.pop(p)
        else:
            if i in s: return None,0
            # insert sorted
            p=sum(1 for x in s if x<i); sign*=(-1)**p; s.insert(p,i)
    return tuple(s),sign
def build_one(h):
    M=np.zeros((len(dets),len(dets)))
    for d in dets:
        for i in range(N):
            for j in range(N):
                if h[i,j]==0: continue
                new,sg=apply_ops(d,[('c',i),('a',j)])
                if new is None: continue
                M[idx[new],idx[d]]+=sg*h[i,j]
    return M
def build_two(k):
    M=np.zeros((len(dets),len(dets)))
    # V = 1/2 sum V_ijkl a_i^dag a_j^dag a_l a_k, V_ijkl=<ij|V|kl>
    for d in dets:
        for i in range(N):
            for j in range(N):
                for kk in range(N):
                    for ll in range(N):
                        v=Vel(i,j,kk,ll,k)
                        if v==0: continue
                        new,sg=apply_ops(d,[('c',i),('c',j),('a',ll),('a',kk)])
                        if new is None: continue
                        M[idx[new],idx[d]]+=0.5*sg*v
    return M
# one-electron Dq operator: h = -4 P_t2g + 6 P_eg (in units of Dq)
h=np.zeros((N,N))
def ms(m): return m
Pt=np.zeros((5,5)); Pe=np.zeros((5,5))
# basis index for m: m+2
Pe[2,2]=1; Pe[0,0]+=0.5; Pe[4,4]+=0.5; Pe[0,4]+=0.5; Pe[4,0]+=0.5
Pt[1,1]=1; Pt[3,3]=1; Pt[0,0]+=0.5; Pt[4,4]+=0.5; Pt[0,4]-=0.5; Pt[4,0]-=0.5
hm=-4*Pt+6*Pe
for i,(m,s) in enumerate(orbs):
    for j,(mm,ss) in enumerate(orbs):
        if s==ss: h[i,j]=hm[m+2,mm+2]
Mcf=build_one(h)
M2=build_two(2); M4=build_two(4); M0=build_two(0)
np.save('/work/mats.npy',np.array([Mcf,M0,M2,M4]))
print("built")
