
cd /tmp/tsbench-run-9aa2jt5t; cat > b.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B,C=621.,2851.
Fk={2:B+5*C/35,4:C/35}
def c(k,m1,m2):
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,q,m2)*wigner_3j(2,k,2,0,0,0))
SIGN=int(__import__('sys').argv[1])
def V(a,b,cc,d):
    if a-cc!=d-b: return 0
    return sum(Fk[k]*c(k,a,cc)*c(k,d,b)*((-1)**(a-cc) if SIGN else 1) for k in (2,4))
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def build(nup):
    return [d for d in itertools.combinations(range(10),5) if sum(orbs[i][1]==0 for i in d)==nup]
Vt={}
for a in range(10):
 for b in range(10):
  for cc in range(10):
   for d in range(10):
    if orbs[a][1]==orbs[cc][1] and orbs[b][1]==orbs[d][1]:
      v=V(orbs[a][0],orbs[b][0],orbs[cc][0],orbs[d][0])
      if abs(v)>1e-12:Vt[(a,b,cc,d)]=v
s2=1/np.sqrt(2)
T=np.zeros((5,5));ix=lambda m:m+2
T[ix(0),0]=1;T[ix(2),1]=s2;T[ix(-2),1]=s2
T[ix(1),2]=1;T[ix(-1),3]=1;T[ix(2),4]=s2;T[ix(-2),4]=-s2
def H(dets,Dq):
    h1=(T@np.diag([6,6,-4,-4,-4])@T.T)*Dq
    idx={d:i for i,d in enumerate(dets)};n=len(dets);M=np.zeros((n,n))
    for d in dets:
        i=idx[d]
        for a in range(10):
          for b in range(10):
            if orbs[a][1]!=orbs[b][1]:continue
            h=h1[orbs[a][0]+2,orbs[b][0]+2]
            if abs(h)<1e-12 or b not in d:continue
            l=list(d);p=l.index(b);sg=(-1)**p;l.pop(p)
            if a in l:continue
            l2=sorted(l+[a]);sg*=(-1)**l2.index(a)
            M[idx[tuple(l2)],i]+=h*sg
        for (a,b,cc,dd),v in Vt.items():
            l=list(d);sg=1;ok=True
            for an in (cc,dd):
                if an not in l:ok=False;break
                p=l.index(an);sg*=(-1)**p;l.pop(p)
            if not ok:continue
            for cr in (b,a):
                if cr in l:ok=False;break
                l2=sorted(l+[cr]);sg*=(-1)**l2.index(cr);l=l2
            if ok:M[idx[tuple(l)],i]+=0.5*v*sg
    return M
d6=build(5);d2=build(3)
def gap(Dq):
    e6=np.linalg.eigvalsh(H(d6,Dq))[0]
    w=np.linalg.eigvalsh(H(d2,Dq))
    return w[0]-e6
print([round(gap(x),1) for x in (0,1000,2000)])
lo,hi=500,4000
for _ in range(40):
    m=(lo+hi)/2
    if gap(m)<-1e-6:hi=m
    else:lo=m
print(lo)
E
python3 b.py 0; python3 b.py 1