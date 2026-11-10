python3 - <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
def c(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float(np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m,q,mp)*(-1)**m)
C={(k,m,mp):c(k,m,mp) for k in (2,4) for m in ms for mp in ms}
orbs=[(m,s) for s in (0,1) for m in ms]
oi={o:i for i,o in enumerate(orbs)}
def I(a,b,cc,d,F):
    if a[1]!=cc[1] or b[1]!=d[1] or a[0]+b[0]!=cc[0]+d[0]: return 0
    return sum(C[(k,a[0],cc[0])]*C[(k,d[0],b[0])]*F[k] for k in (2,4))
idx=lambda m:m+2
v0=np.zeros(5);v0[2]=1
v2=np.zeros(5);v2[0]=v2[4]=1/np.sqrt(2)
Peg=np.outer(v0,v0)+np.outer(v2,v2)
keys=[]
for up in itertools.combinations(range(5),4):
    for dn in range(5):
        keys.append(tuple(sorted([oi[(ms[i],0)] for i in up]+[oi[(ms[dn],1)]])))
dset={k:i for i,k in enumerate(keys)}
def apply(ann,cre,state):
    s=list(state);sign=1
    for o in ann:
        if o not in s: return None,0
        p=s.index(o);sign*=(-1)**p;s.pop(p)
    for o in cre:
        if o in s: return None,0
        p=sum(1 for x in s if x<o);sign*=(-1)**p;s.insert(p,o)
    return tuple(s),sign
quad=[(a,b,cc,d) for a in orbs for b in orbs for cc in orbs for d in orbs if I(a,b,cc,d,{2:1,4:1})!=0 or I(a,b,cc,d,{2:1,4:-1})!=0]
# precompute matrices: H = Dq*Hd + B*HB + C*HC
def build(F,Dq):
    h=6*Dq*Peg-4*Dq*(np.eye(5)-Peg)
    n=len(keys);H=np.zeros((n,n))
    for j,st in enumerate(keys):
        for (a,b,cc,d) in quad:
            val=I(a,b,cc,d,F)
            s1,g1=apply([oi[cc],oi[d]],[oi[b],oi[a]],st)
            if s1 is None: continue
            H[dset[s1],j]+=0.5*val*g1
        for m in ms:
         for mp in ms:
          for s in (0,1):
            hv=h[idx(m),idx(mp)]
            if hv==0: continue
            s1,g1=apply([oi[(mp,s)]],[oi[(m,s)]],st)
            if s1 is None: continue
            H[dset[s1],j]+=hv*g1
    return H
Hd=build({2:0,4:0},1.0)
HB=build({2:49,4:0},0.0)
HC=build({2:7,4:63/5},0.0)
def run(Dq,B,Cc):
    H=Dq*Hd+B*HB+Cc*HC
    e=np.linalg.eigvalsh((H+H.T)/2);return e-e[0]
def res(p):
    e=run(*p)
    # levels: skip ground (idx0); sorted eigenvalues: 4T1 idx1-3, 4T2 idx4-6, then 4A1/4E idx7-9
    return [e[1]-19180,e[4]-22130,e[7]-23370]
for g in ([800,700,3000],[600,800,3500],[500,600,3000]):
    s=fsolve(res,g,xtol=1e-12);print(s,res(s),run(*s)[:11].round(0))
E