import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def c(k,m,mp):
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
C={k:np.array([[c(k,m,mp) for mp in ms] for m in ms]) for k in (0,2,4)}
so=[(m,s) for m in ms for s in (0,1)]
dets=[sum(1<<i for i in comb) for comb in itertools.combinations(range(10),7)]
idx={d:i for i,d in enumerate(dets)}
N=10
def apply(d,ops):
    sign=1
    for i,cr in reversed(ops):
        if cr==(d>>i&1): return None,0
        if bin(d&((1<<i)-1)).count('1')%2: sign=-sign
        d^=1<<i
    return d,sign
# precompute sparse structure
one=[];two=[]
for d in dets:
    j=idx[d]
    for p in range(N):
        for q in range(N):
            if so[p][1]!=so[q][1]: continue
            d2,s=apply(d,[(p,1),(q,0)])
            if s: one.append((idx[d2],j,so[p][0],so[q][0],s))
    for k1 in range(N):
      for l1 in range(N):
        for p in range(N):
          for q in range(N):
            if so[p][1]!=so[k1][1] or so[q][1]!=so[l1][1]: continue
            if so[p][0]+so[q][0]!=so[k1][0]+so[l1][0]: continue
            d2,s=apply(d,[(p,1),(q,1),(l1,0),(k1,0)])
            if s: two.append((idx[d2],j,so[p][0],so[q][0],so[k1][0],so[l1][0],s))
def build(Dq,B,Cc):
    R={2:49*B+7*Cc,4:63*Cc/5}
    h=np.zeros((5,5))
    for m,v in zip([-1,0,1],[-4,6,-4]): h[m+2,m+2]=v*Dq
    h[0,0]=h[4,4]=Dq; h[0,4]=h[4,0]=5*Dq
    H=np.zeros((120,120))
    for i,j,a,b,s in one: H[i,j]+=h[a+2,b+2]*s
    for i,j,a,b,cc,d,s in two:
        v=sum(R[k]*C[k][a+2,cc+2]*C[k][d+2,b+2] for k in (2,4))
        H[i,j]+=0.5*v*s
    return H
Sz=np.array([sum((0.5 if so[i][1]==0 else -0.5) for i in range(10) if d>>i&1) for d in dets])
S2M=np.zeros((120,120))
for d in dets:
    j=idx[d]; sz=Sz[j]; S2M[j,j]+=sz*sz-sz
    for a in range(5):
        d1,s1=apply(d,[(2*a,1),(2*a+1,0)])
        if not s1: continue
        for b in range(5):
            e,t=apply(d1,[(2*b+1,1),(2*b,0)])
            if t: S2M[idx[e],j]+=s1*t
def levels(Dq,B,Cc):
    w,v=np.linalg.eigh(build(Dq,B,Cc))
    out=[];i=0
    while i<120:
        j=i
        while j<120 and abs(w[j]-w[i])<1e-6: j+=1
        V=v[:,i:j]; s2=np.trace(V.T@S2M@V)/(j-i)
        S=(-1+np.sqrt(1+4*s2))/2
        out.append((w[i],(j-i)//(round(2*S+1)),round(2*S+1)))
        i=j
    return out
L=levels(0,1000,4000)
print([(round(e-L[0][0]),d,m) for e,d,m in L[:8]])
def model(p):
    L=levels(*p); g=L[0][0]
    q=[(e-g,d) for e,d,m in L if m==4][1:]  # excited quartets
    q=[e-g for e,d,m in L if m==4][1:]
    dq=[e-g for e,d,m in L if m==2]
    return q,dq
for p in [(900,900,3900)]:
    L=levels(*p);g=L[0][0]
    print([(round(e-g),d,m) for e,d,m in L[:14]])
