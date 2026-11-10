import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float(((-1)**m1)*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def two(a,b,c,d,F):
    if a[1]!=c[1] or b[1]!=d[1]: return 0.
    if a[0]+b[0]!=c[0]+d[0]: return 0.
    return sum(F[k]*C[(k,a[0],c[0])]*C[(k,d[0],b[0])] for k in (0,2,4))
V=np.zeros((5,5))
for i,m in enumerate(ms): V[i,i]={2:1,1:-4,0:6}[abs(m)]
V[0,4]=V[4,0]=5
def sgn(arr):
    s=1
    for i in range(len(arr)):
      for j in range(i+1,len(arr)):
        if arr[i]>arr[j]: s=-s
    return s
def run(n,Ms2):
  dets=[d for d in itertools.combinations(range(10),n) if sum(1 if orbs[i][1] else -1 for i in d)==Ms2]
  idx={d:i for i,d in enumerate(dets)}
  N=len(dets); Hv=np.zeros((N,N)); Hb=np.zeros((N,N)); Hc=np.zeros((N,N))
  h=np.zeros((10,10))
  for p in range(10):
    for q in range(10):
      if orbs[p][1]==orbs[q][1]: h[p,q]=V[ms.index(orbs[p][0]),ms.index(orbs[q][0])]
  for d in dets:
    I=idx[d]
    for p in d:
      for q in range(10):
        if h[q,p]==0 or (q!=p and q in d): continue
        new=list(d); new[new.index(p)]=q
        Hv[idx[tuple(sorted(new))],I]+=sgn(new)*h[q,p]
    for (Fs,Mt) in [({0:0,2:1,4:0},Hb),({0:0,2:0,4:1},Hc)]:
     for i1 in range(n):
      for i2 in range(n):
        if i1==i2: continue
        c,dd=d[i1],d[i2]
        for a in range(10):
          for b in range(10):
            if a==b: continue
            val=two(orbs[a],orbs[b],orbs[c],orbs[dd],Fs)
            if val==0: continue
            lst=list(d); s=1
            pc=lst.index(c); s*=(-1)**pc; lst.pop(pc)
            pd=lst.index(dd); s*=(-1)**pd; lst.pop(pd)
            if b in lst or a in lst: continue
            lst=[a,b]+lst
            Mt[idx[tuple(sorted(lst))],I]+=0.5*s*sgn(lst)*val
  return Hv,Hb,Hc
B,Cc=803,3078
F2=(B+Cc/7)*49; F4=Cc/35*441
m=run(2,0); w=np.linalg.eigvalsh(F2*m[1]+F4*m[2]); u=np.unique(np.round(w,2)); print((u-u[0])/B)
q=run(6,4); z=run(6,0)
E=lambda m,Dq: np.linalg.eigvalsh(Dq*m[0]+F2*m[1]+F4*m[2])
from scipy.optimize import brentq
h=lambda Dq: E(q,Dq)[0]-E(z,Dq)[0]
for x in range(1000,3000,200): print(x, round(h(x),1))
r=brentq(lambda x: h(x)-1e-6 if False else E(q,x)[0]-E(z,x)[0]-0.0 if x>0 else 0, 1500,2500) if False else None
# find crossing: below crossing, lowest Ms=0 equals quintet (h=0); above, h>0
xs=np.linspace(1000,3000,2001)
hs=[h(x) for x in xs]
for x,v in zip(xs,hs):
  if v>1e-3: print('first',x,v); break
# precise: singlet 1A1 lowest-energy = lowest eigenvalue among states not degenerate with quintet; compute singlet lowest via S^2? use E(z) second distinct
def sing(x):
  ez=E(z,x); eq=E(q,x)
  # remove quintet roots (one each of the Ms=0 components)
  rest=list(ez)
  for e in eq:
    i=np.argmin(abs(np.array(rest)-e)); rest.pop(i)
  return min(rest)
f=lambda x: sing(x)-E(q,x)[0]
print(brentq(f,1000,3000))
