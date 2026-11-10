import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def g(a,b,cc,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[cc],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(c(k,ma,mc)*c(k,md,mb)*F[k] for k in (0,2,4))
def cf(Dq):
    h=np.zeros((5,5)); d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): h[i,i]=d[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    return h
def ann(j,det):
    if j not in det: return None
    p=det.index(j); return det[:p]+det[p+1:], (-1)**p
def cre(i,det):
    if i in det: return None
    new=sorted(det+(i,)); p=new.index(i); return tuple(new),(-1)**p
def op(i,j,det):
    r=ann(j,det)
    if not r: return None
    s=cre(i,r[0])
    if not s: return None
    return s[0],r[1]*s[1]
G={}
for a in range(10):
 for b in range(10):
  for cc in range(10):
   for d in range(10):
    G[(a,b,cc,d)]=None
def Hmat(Dq,B,C):
    F={0:0,2:49*B+7*C,4:441*C/35}
    h=cf(Dq); N=len(dets); M=np.zeros((N,N))
    for J,D in enumerate(dets):
        for a in range(10):
            for b in range(10):
                if orbs[a][1]!=orbs[b][1]: continue
                v=h[orbs[a][0]+2,orbs[b][0]+2]
                if v==0: continue
                r=op(a,b,D)
                if r: M[idx[r[0]],J]+=v*r[1]
        # 1/2 sum g(ab,cd) a+ b+ d c
        for cc in D:
            for d in D:
                if cc==d: continue
                r1=ann(cc,D); r2=ann(d,r1[0])
                for a in range(10):
                    for b in range(10):
                        v=g(a,b,cc,d,F)
                        if v==0: continue
                        r3=cre(b,r2[0])
                        if not r3: continue
                        r4=cre(a,r3[0])
                        if not r4: continue
                        M[idx[r4[0]],J]+=0.5*v*r1[1]*r2[1]*r3[1]*r4[1]
    return M
Dq,B=1417,878
def levels(C):
    e=np.linalg.eigvalsh(Hmat(Dq,B,C)); e=e-e[0]
    out=[]
    for x in e:
        if not out or abs(x-out[-1][0])>0.5: out.append([x,1])
        else: out[-1][1]+=1
    return [(round(x,1),n) for x,n in out]
print(levels(4*B)[:8])
f=lambda C: levels(C)[1][0]-18540
Cs=brentq(f,2*B,6*B,xtol=0.1); print(Cs,Cs/B,levels(Cs)[:8])
