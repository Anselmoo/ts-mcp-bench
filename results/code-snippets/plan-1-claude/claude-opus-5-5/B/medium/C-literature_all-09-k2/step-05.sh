cat > d5.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5*gaunt(2,k,2,-m1,m1-m2,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms if abs(a-b)<=k}
so=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(1 for o in d if so[o][1]==0)==4]
idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def apply2(det,p,q,r,s):
    d=list(det); sign=1
    for op,orb in (('a',r),('a',s),('c',q),('c',p)):
        if op=='a':
            if orb not in d: return None,0
            i=d.index(orb); sign*=(-1)**i; d.pop(i)
        else:
            if orb in d: return None,0
            i=sum(1 for x in d if x<orb); sign*=(-1)**i; d.insert(i,orb)
    return tuple(d),sign
def build(F):
    H=np.zeros((N,N))
    for i,det in enumerate(dets):
      for p in range(10):
        for q in range(10):
          for r in range(10):
            for s in range(10):
              mp,sp=so[p];mq,sq=so[q];mr,sr=so[r];m4,ss=so[s]
              if sp!=sr or sq!=ss or mp+mq!=mr+m4: continue
              v=sum(C.get((k,mp,mr),0)*C.get((k,m4,mq),0)*F[k] for k in (2,4))
              if v==0: continue
              nd,sg=apply2(det,p,q,r,s)
              if nd is None: continue
              H[idx[nd],i]+=0.5*sg*v
    return H
H2=build({2:1,4:0}); H4=build({2:0,4:1})
V=np.zeros((5,5))
for m,v in zip(ms,[1,-4,6,-4,1]): V[ms.index(m),ms.index(m)]=v
V[0,4]=V[4,0]=5
HV=np.zeros((N,N))
for i,det in enumerate(dets):
    for a in det:
        for b in range(10):
            if so[a][1]!=so[b][1]: continue
            v=V[ms.index(so[b][0]),ms.index(so[a][0])]
            if v==0: continue
            d=list(det); ia=d.index(a); sg=(-1)**ia; d.pop(ia)
            if b in d and b!=a: continue
            ib=sum(1 for x in d if x<b); sg*=(-1)**ib; d.insert(ib,b)
            HV[idx[tuple(d)],i]+=sg*v
np.save('m.npy',np.array([H2,H4,HV]))
EOF
python3 d5.py && cat > fit.py <<'EOF'
import numpy as np
from scipy.optimize import least_squares
H2,H4,HV=np.load('m.npy')
def levels(Dq,B,Cc):
    F4=Cc/35*441/441*441/441; F4=Cc*441/35/441  # F4 (Condon-Shortley scaled) : C=35F4 with F4=F^4/441
    # B=F2-5F4, C=35F4 with F2=F^2/49,F4=F^4/441
    f4=Cc/35; f2=B+5*f4
    H=f2*49*H2+f4*441*H4+Dq*HV
    e=np.linalg.eigvalsh(H); e=np.round(e-e[0],3)
    u,c=np.unique(e,return_counts=True); return list(zip(u,c))
print(levels(0,1000,4000)[:6])
print(levels(800,800,3200)[:8])
def res(x):
    L=levels(*x); q=[u for u,c in L[1:]]
    return np.array(q[:3])-[19720,23260,24980]
s=least_squares(res,[800,800,3200]); print(s.x, res(s.x)); print(levels(*s.x)[:6])
EOF
python3 fit.py