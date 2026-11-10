cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m*gaunt(2,k,2,-m,q,mp))
C={k:np.array([[ck(k,m,mp) for mp in ms] for m in ms]) for k in (0,2,4)}
so=[(m,s) for s in (0.5,-0.5) for m in ms]
dets=[d for d in itertools.combinations(range(10),5) if sum(so[i][1] for i in d)==1.5]
idx={d:i for i,d in enumerate(dets)}
def apply(op,d):  # op list of (create/annihilate idx) applied right to left; return (sign,newdet) 
    occ=list(d);sign=1
    for (t,i) in reversed(op):
        if t=='a':
            if i not in occ: return 0,None
            p=occ.index(i);sign*=(-1)**p;occ.pop(p)
        else:
            if i in occ: return 0,None
            p=sum(1 for o in occ if o<i);sign*=(-1)**p;occ.insert(p,i)
    return sign,tuple(occ)
def H(Dq,B,Cc):
    F={0:0,2:49*B+7*Cc,4:63*Cc/5}
    h=np.zeros((len(dets),len(dets)))
    V=np.zeros((5,5))
    for i,m in enumerate(ms): V[i,i]={2:1,1:-4,0:6,-1:-4,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    for d in dets:
        for a in range(10):
            for b in range(10):
                if so[a][1]!=so[b][1]: continue
                v=V[so[a][0]+2,so[b][0]+2]
                if v==0: continue
                s,n=apply([('c',a),('a',b)],d)
                if s: h[idx[n],idx[d]]+=s*v
    # two-body 1/2 sum <ab|g|cd> a†_a a†_b a_d a_c
    for a in range(10):
     for b in range(10):
      if a==b: continue
      for c in range(10):
       for dd in range(10):
        if dd==c: continue
        if so[a][1]!=so[c][1] or so[b][1]!=so[dd][1]: continue
        m1,m2,m3,m4=so[a][0],so[b][0],so[c][0],so[dd][0]
        if m1+m2!=m3+m4: continue
        g=0
        for k in (0,2,4):
            g+=F[k]*C[k][m1+2,m3+2]*C[k][m4+2,m2+2]
        if abs(g)<1e-12: continue
        for d in dets:
            s,n=apply([('c',a),('c',b),('a',dd),('a',c)],d)
            if s: h[idx[n],idx[d]]+=0.5*s*g
    return h
def lev(p):
    e=np.linalg.eigvalsh(H(*p)); e=e-e[0]
    return e
obs=np.array([19720,23260,24980])
def lv(p):
    e=lev(p); u=np.unique(np.round(e,3)); 
    return e
e=lev((1000,800,3000));print(np.round(e,0))
E
python3 /tmp/a.py