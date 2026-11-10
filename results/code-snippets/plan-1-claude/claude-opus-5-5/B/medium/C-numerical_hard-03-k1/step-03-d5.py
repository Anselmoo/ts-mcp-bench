import numpy as np, itertools
from sympy.physics.wigner import gaunt
ml=[-2,-1,0,1,2]
orbs=[(m,s) for m in ml for s in (0,1)]
def ck(k,m1,m2):
    return float((-1)**m1*5*gaunt(2,k,2,-m1,m1-m2,m2)*np.sqrt(4*np.pi/(2*k+1)))
C={k:{(a,b):ck(k,a,b) for a in ml for b in ml} for k in (0,2,4)}
def U(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=a,b,c,d
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(F[k]*C[k][(ma,mc)]*C[k][(md,mb)] for k in (2,4))
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
V=np.zeros((5,5))
V[0,0]=V[4,4]=1;V[2,2]=6;V[1,1]=V[3,3]=-4;V[0,4]=V[4,0]=5
def apply(ops,det):
    d=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in d: return 0,None
            p=d.index(o);sign*=(-1)**p;d.pop(p)
        else:
            if o in d: return 0,None
            p=sum(1 for x in d if x<o);sign*=(-1)**p;d.insert(p,o)
    return sign,tuple(d)
n=len(dets)
HV=np.zeros((n,n));HF2=np.zeros((n,n));HF4=np.zeros((n,n))
for j,d in enumerate(dets):
    for p in range(10):
        for q in range(10):
            if orbs[p][1]!=orbs[q][1]: continue
            v=V[ml.index(orbs[p][0]),ml.index(orbs[q][0])]
            if v==0: continue
            s,nd=apply([('c',p),('a',q)],d)
            if s: HV[idx[nd],j]+=s*v
    for p in range(10):
      for q in range(10):
        if p==q: continue
        for r in d:
          for t in d:
            if r>=t: continue
            for F,M in (({2:1,4:0},HF2),({2:0,4:1},HF4)):
                val=U(orbs[p],orbs[q],orbs[r],orbs[t],F)-U(orbs[p],orbs[q],orbs[t],orbs[r],F)
                if abs(val)<1e-12: continue
                s,nd=apply([('c',p),('c',q),('a',t),('a',r)],d)
                if s: M[idx[nd],j]+=0.5*s*val
Ssq=np.zeros((n,n))
for j,d in enumerate(dets):
    ms=sum(0.5 if orbs[o][1]==0 else -0.5 for o in d)
    Ssq[j,j]+=ms*ms+ms
    for m in ml:
      up=orbs.index((m,0));dn=orbs.index((m,1))
      for m2 in ml:
        up2=orbs.index((m2,0));dn2=orbs.index((m2,1))
        s,nd=apply([('c',dn2),('a',up2),('c',up),('a',dn)],d)
        if s: Ssq[idx[nd],j]+=s
np.savez('mats.npz',HV=HV,HF2=HF2,HF4=HF4,S=Ssq)
