import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt as ssqrt, N, pi
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
def c(k,m,mp):
    return float(N(ssqrt(4*pi/(2*k+1))*gaunt(2,k,2,-m,m-mp,mp)*(-1)**m))
C={(k,m,mp):c(k,m,mp) for k in (2,4) for m in ms for mp in ms}
orbs=[(m,s) for s in (0,1) for m in ms]
n=10
dets=[d for d in itertools.combinations(range(n),5) if sum(1 for o in d if o<5)==4]
idx={d:i for i,d in enumerate(dets)}
def apply(ops,det):
    occ=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in occ: return 0,None
            p=occ.index(o); sign*=(-1)**p; occ.pop(p)
        else:
            if o in occ: return 0,None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
    return sign,tuple(occ)
# precompute operator structures
T1=[];T2=[]
for det in dets:
    j=idx[det]
    for a in range(n):
        for b in range(n):
            if orbs[a][1]!=orbs[b][1]: continue
            s,nd=apply([('c',a),('a',b)],det)
            if s: T1.append((idx[nd],j,a,b,s))
    for a in range(n):
     for b in range(n):
      for cc in range(n):
       for d in range(n):
        if orbs[a][0]+orbs[b][0]!=orbs[cc][0]+orbs[d][0]: continue
        if orbs[a][1]!=orbs[cc][1] or orbs[b][1]!=orbs[d][1]: continue
        s,nd=apply([('c',a),('c',b),('a',d),('a',cc)],det)
        if s: T2.append((idx[nd],j,a,b,cc,d,s))
def ham(Dq,B,Cc):
    F4=63*Cc/5; F2=(441*B+5*F4)/9; F={2:F2,4:F4}
    Pe=np.zeros((5,5)); Pe[2,2]=1
    v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2); Pe+=np.outer(v,v)
    h=6*Dq*Pe-4*Dq*(np.eye(5)-Pe)
    H=np.zeros((len(dets),)*2)
    for i,j,a,b,s in T1:
        if orbs[a][1]==orbs[b][1]: H[i,j]+=s*h[orbs[a][0]+2,orbs[b][0]+2]
    for i,j,a,b,cc,d,s in T2:
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[cc],orbs[d]
        if sa==sc and sb==sd:
            H[i,j]+=0.5*s*sum(C[(k,ma,mc)]*C[(k,md,mb)]*F[k] for k in (2,4))
    return H
def levels(Dq,B,Cc):
    w=np.linalg.eigvalsh(ham(Dq,B,Cc)); w=w-w[0]
    u=[]
    for x in w:
        if not u or abs(x-u[-1][0])>1: u.append([x,1])
        else: u[-1][1]+=1
    return u
if __name__=="__main__":
    print(levels(800,860,3200)[:8], 10*860+5*3200)
    def f(p):
        u=levels(*p)
        return [u[1][0]-19180,u[2][0]-22130,u[3][0]-23370]
    print([ (x[0],x[1]) for x in levels(800,860,3200)[:6]])
