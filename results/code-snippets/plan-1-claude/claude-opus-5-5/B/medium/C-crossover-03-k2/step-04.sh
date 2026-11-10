
cd $TMPDIR && python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float(((-1)**m1)*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
print(C[(2,2,2)]*7, C[(4,2,2)]*21)
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
    for (Fs,Mt) in [({0:0,2:1/49*49/49,4:0},Hb),({0:0,2:0,4:1},Hc)]:
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
# Hb: coefficient of F^2, Hc: of F^4. F^2=49F2, F^4=441F4; F2=B+5C/35, F4=C/35
B,Cc=803,3078
F2=(B+Cc/7)*49; F4=Cc/35*441
for n in (2,6):
  for M in ((2 if n==2 else 4),0):
    m=run(n,M); w=np.linalg.eigvalsh(F2*m[1]+F4*m[2])
    print(n,M,np.round(np.unique(np.round(w,3)),1))
q=run(6,4); z=run(6,0)
E=lambda m,Dq: np.linalg.eigvalsh(Dq*m[0]+F2*m[1]+F4*m[2])
from scipy.optimize import brentq
h=lambda Dq: E(q,Dq)[0]-E(z,Dq)[0]
for x in range(1000,3000,100): print(x, round(h(x),1))
EOF
