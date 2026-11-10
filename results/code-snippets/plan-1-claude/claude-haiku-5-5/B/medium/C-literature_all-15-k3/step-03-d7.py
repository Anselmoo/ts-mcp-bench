import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]
N=len(orbs)
W3={}
def w3(a,b,c,d,e,f):
    key=(a,b,c,d,e,f)
    if key not in W3: W3[key]=float(wigner_3j(a,b,c,d,e,f))
    return W3[key]
def c(ma,mb,k,q):
    if -ma+q+mb!=0 or abs(q)>k: return 0.0
    return (-1)**(l-ma)*w3(l,k,l,-ma,q,mb)*(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
def Vspat(m1,m2,m3,m4,k):
    return sum((-1)**q*c(m1,m3,k,q)*c(m2,m4,k,-q) for q in range(-k,k+1))
def Vel(a,b,cc,d,k):
    ma,sa=orbs[a]; mb,sb=orbs[b]; mc,sc=orbs[cc]; md,sd=orbs[d]
    if sa!=sc or sb!=sd: return 0.0
    return Vspat(ma,mb,mc,md,k)
dets=list(itertools.combinations(range(N),7))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(occ, ops):
    s=list(occ); sign=1
    for t,i in reversed(ops):
        if t=='a':
            if i not in s: return None,0
            p=s.index(i); sign*=(-1)**p; s.pop(p)
        else:
            if i in s: return None,0
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
    for d in dets:
        for i in range(N):
            for j in range(N):
                for kk in range(N):
                    for ll in range(N):
                        v=Vel(i,j,kk,ll,k)
                        if abs(v)<1e-14: continue
                        new,sg=apply_ops(d,[('c',i),('c',j),('a',ll),('a',kk)])
                        if new is None: continue
                        M[idx[new],idx[d]]+=0.5*sg*v
    return M
Pt=np.zeros((5,5)); Pe=np.zeros((5,5))
Pe[2,2]=1; Pe[0,0]+=0.5; Pe[4,4]+=0.5; Pe[0,4]+=0.5; Pe[4,0]+=0.5
Pt[1,1]=1; Pt[3,3]=1; Pt[0,0]+=0.5; Pt[4,4]+=0.5; Pt[0,4]-=0.5; Pt[4,0]-=0.5
hm=-4*Pt+6*Pe
h=np.zeros((N,N))
for i,(m,s) in enumerate(orbs):
    for j,(mm,ss) in enumerate(orbs):
        if s==ss: h[i,j]=hm[m+2,mm+2]
Mcf=build_one(h)
M0=build_two(0); M2=build_two(2); M4=build_two(4)
np.savez('mats.npz',Mcf=Mcf,M0=M0,M2=M2,M4=M4)
# check: free-ion term energies. F-only: F0 should give constant; check trace
print("built", np.allclose(M0, M0.T))
