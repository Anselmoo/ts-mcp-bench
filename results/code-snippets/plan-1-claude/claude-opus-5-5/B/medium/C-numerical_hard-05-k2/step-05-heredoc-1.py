import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return np.sqrt(4*np.pi/(2*k+1))*float(gaunt(2,k,2,-m1,q,m2))*(-1)**m1
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
orbs=[(m,s) for m in ms for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),6) if sum(1 for o in d if o%2==0)==3]
idx={d:i for i,d in enumerate(dets)};N=len(dets)
def apply(ops,det):
    det=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in det: return 0,None
            p=det.index(o);sign*=(-1)**p;det.pop(p)
        else:
            if o in det: return 0,None
            p=sum(1 for x in det if x<o);sign*=(-1)**p;det.insert(p,o)
    return sign,tuple(det)
def g2(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.0
    return sum(CK[(k,ma,mc)]*CK[(k,md,mb)]*F[k] for k in (2,4))
def Hee(F):
    Hm=np.zeros((N,N))
    for j,d in enumerate(dets):
        for a in range(10):
          for b in range(10):
            if a==b: continue
            for c in d:
              for e in d:
                if c==e: continue
                val=g2(a,b,c,e,F)
                if val==0: continue
                s,nd=apply([('c',a),('c',b),('a',e),('a',c)],d)
                if s and nd in idx: Hm[idx[nd],j]+=0.5*s*val
    return Hm
def op1(f,ds=dets,ix=idx,n=None):
    M=np.zeros((N,N))
    for j,d in enumerate(dets):
        for p,q,v in f:
            s,nd=apply([('c',p),('a',q)],d)
            if s: M[idx[nd],j]+=s*v
    return M
Vd={2:1,1:-4,0:6};f=[]
for i,m in enumerate(ms):
    for s in (0,1): f.append((2*i+s,2*i+s,Vd[abs(m)]))
for s in (0,1): f.append((s,8+s,5));f.append((8+s,s,5))
HD=op1(f);HB=Hee({2:49,4:0});HC=Hee({2:7,4:441/35})
# S^2 within Sz=0: S-S+ ; build S+ to Sz=1 space manually
dets1=[d for d in itertools.combinations(range(10),6) if sum(1 for o in d if o%2==0)==4]
i1={d:i for i,d in enumerate(dets1)}
Sp=np.zeros((len(dets1),N))
for j,d in enumerate(dets):
    for i in range(5):
        s,nd=apply([('c',2*i),('a',2*i+1)],d)
        if s: Sp[i1[nd],j]+=s
S2=Sp.T@Sp
def sing(Dq,B,C):
    w,v=np.linalg.eigh(Dq*HD+B*HB+C*HC+1e5*S2)
    w=w[w<5e4]; w=w-w[0]
    out=[]
    for x in w:
        if out and abs(x-out[-1][0])<0.5: out[-1][1]+=1
        else: out.append([x,1])
    return out
def f2(p):
    g=sing(p[0],p[1],4.5*p[1]); return [g[1][0]-13960,g[2][0]-22740]
x=fsolve(f2,[1600,700]); print(x); print(sing(x[0],x[1],4.5*x[1])[:8])
