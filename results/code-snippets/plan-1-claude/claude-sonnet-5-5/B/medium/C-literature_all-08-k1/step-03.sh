python3 - <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
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
quad=[(a,b,cc,d) for a in orbs for b in orbs for cc in orbs for d in orbs if I(a,b,cc,d,{2:1,4:1})!=0 or I(a,b,cc,d,{2:1,4:0})!=0 or I(a,b,cc,d,{2:0,4:1})!=0]
def run(Dq,B,Cc):
    F={2:49*B+7*Cc,4:63*Cc/5}
    h=6*Dq*Peg-4*Dq*(np.eye(5)-Peg)
    n=len(keys);H=np.zeros((n,n))
    for j,st in enumerate(keys):
        for (a,b,cc,d) in quad:
            val=I(a,b,cc,d,F)
            s1,g1=apply([oi[d],oi[cc]],[oi[b],oi[a]],st)
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
    e=np.linalg.eigvalsh((H+H.T)/2);return e-e[0]
def lev(e):
    out=[];i=0
    while i<len(e):
        j=i
        while j<len(e) and abs(e[j]-e[i])<1e-3:j+=1
        out.append((e[i],j-i));i=j
    return out
print(lev(run(700,800,3000))[:8])
def res(p):
    L=lev(run(*p))
    # skip sextet(ground) ; first levels: 4T1(3),4T2(3),4A1/4E(3 total)
    q=[x for x in L[1:5]]
    return [q[0][0]-19180,q[1][0]-22130,q[2][0]-23370]
r=least_squares(res,[800,700,3000],x_scale=[100,100,300])
print(r.x,res(r.x),lev(run(*r.x))[:6])
E