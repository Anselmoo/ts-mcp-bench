
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # c^k(l m1, l m2)
    return float((-1)**m1*np.sqrt(25)*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2)) if abs(m1-m2)<=k else 0.0
C={}
for k in (2,4):
  for a in ms:
    for b in ms: C[k,a,b]=ck(k,a,b)
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cr):
  F4=Cr/35; F2=B+5*F4; Fk={2:49*F2,4:441*F4}
  h=np.zeros((5,5))
  for i,m in enumerate(ms):
    h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
  h[0,4]=h[4,0]=5*Dq
  def g(p,q,r,s): # <pq|rs>
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[p],so[q],so[r],so[s]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    return sum(C[k,m1,m3]*C[k,m4,m2]*Fk[k] for k in (2,4))
  N=len(dets);H=np.zeros((N,N))
  def apply(det):
    out={}
    occ=list(det)
    # one-body
    for i in occ:
      for j in range(10):
        if so[i][1]!=so[j][1]: continue
        v=h[ms.index(so[j][0]),ms.index(so[i][0])]
        if v==0: continue
        new=[x if x!=i else j for x in occ]
        if j!=i and j in occ: continue
        sign=1; arr=new[:]
        # sort with sign
        for a in range(3):
          for b in range(2-a):
            if arr[b]>arr[b+1]: arr[b],arr[b+1]=arr[b+1],arr[b]; sign=-sign
        out[tuple(arr)]=out.get(tuple(arr),0)+sign*v
    for i1,i2 in itertools.combinations(occ,2):
      for j1 in range(10):
        for j2 in range(10):
          if j1==j2: continue
          v=0.5*(g(j1,j2,i1,i2)-g(j1,j2,i2,i1))  # will double count ordered pairs
          if v==0: continue
          rest=[x for x in occ if x not in (i1,i2)]
          if j1 in rest or j2 in rest: continue
          # annihilate i2,i1 then create j1 j2: build via replacement
          arr=[j1 if x==i1 else (j2 if x==i2 else x) for x in occ]
          sign=1
          for a in range(3):
            for b in range(2-a):
              if arr[b]>arr[b+1]: arr[b],arr[b+1]=arr[b+1],arr[b]; sign=-sign
          out[tuple(arr)]=out.get(tuple(arr),0)+sign*v
    return out
  for d in dets:
    for k,v in apply(d).items(): H[idx[k],idx[d]]+=v
  return H
def spins(dets):
  return np.array([sum(1 if so[i][1]==0 else -1 for i in d) for d in dets])/2
Ms=spins(dets)
def levels(Dq,B,Cr):
  H=build(Dq,B,Cr); 
  sel=np.where(Ms==1.5)[0]; q=np.linalg.eigvalsh(H[np.ix_(sel,sel)])
  sel2=np.where(Ms==0.5)[0]; a=np.linalg.eigvalsh(H[np.ix_(sel2,sel2)])
  g=q[0]
  quart=np.round(q-g,1); allv=np.round(a-g,1)
  # doublets: levels in Ms=1/2 not in quartets
  from collections import Counter
  cq=Counter(quart); ca=Counter(allv)
  d=sorted([x for x in ca for _ in range(ca[x]-cq.get(x,0))])
  return sorted(set(quart)), sorted(set(d))
Dq=1743; B=11710/15
print(levels(Dq,B,4*B))
f=lambda Cr: levels(Dq,B,Cr)[1][0]-15410
Cr=brentq(f,1000,6000); print(Cr, Cr/B, levels(Dq,B,Cr))
EOF
python3 /tmp/d3.py
