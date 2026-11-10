import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
l=2
CK={}
for k in (2,4):
  for m in range(-2,3):
    for mp in range(-2,3):
      CK[k,m,mp]=float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def V1(m,mp):
    if m==mp: return {0:6,1:-4,-1:-4,2:1,-2:1}[m]
    if abs(m-mp)==4: return 5
    return 0
def apply(ops,state):
    st=list(state);sign=1
    for o,dag in reversed(ops):
        if dag:
            if o in st: return None,0
            pos=sum(1 for x in st if x<o); sign*=(-1)**pos; st.insert(pos,o)
        else:
            if o not in st: return None,0
            pos=st.index(o); sign*=(-1)**pos; st.pop(pos)
    return tuple(st),sign
n=len(dets)
HD=np.zeros((n,n));H2=np.zeros((n,n));H4=np.zeros((n,n))
for j,e in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if so[p][1]!=so[q][1]: continue
            v=V1(so[p][0],so[q][0])
            if v==0: continue
            s,sg=apply([(p,1),(q,0)],e)
            if s: HD[idx[s],j]+=sg*v
    for a in range(10):
      for b in range(10):
        for c in e:
          for d in e:
            (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
            if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
            s,sg=apply([(a,1),(b,1),(d,0),(c,0)],e)
            if not s: continue
            H2[idx[s],j]+=0.5*sg*CK[2,ma,mc]*CK[2,md,mb]
            H4[idx[s],j]+=0.5*sg*CK[4,ma,mc]*CK[4,md,mb]
def levels(Dq,B,C):
    H=Dq*HD+(49*B+7*C)*H2+(441*C/35)*H4
    w=np.linalg.eigvalsh(H); w=w-w[0]
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        out.append((round(w[i],1),j-i)); i=j
    return out
print(levels(1449,599.3,4*599.3))
# quartets: need spin; levels deg 4*3=12 for 4T; 2E deg 4
def fit(Dq,B):
    f=lambda C: levels(Dq,B,C)[1][0]-12710
    C=brentq(f,1000,5000); return C
C=fit(1449,599.33); print(C, C/599.33); print(levels(1449,599.33,C)[:6])
