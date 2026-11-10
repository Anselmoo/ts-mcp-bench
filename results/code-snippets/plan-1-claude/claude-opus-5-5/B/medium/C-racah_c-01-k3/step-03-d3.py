import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt as ssqrt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * int Y*_{m1} Y_{k,m1-m2} Y_{m2}
    q=m1-m2
    if abs(q)>k: return 0.0
    import math
    g=gaunt(2,k,2,-m1,q,m2)*(-1)**m1
    return float(g)*math.sqrt(4*math.pi/(2*k+1))
C={k:{(a,b):ck(k,a,b) for a in ms for b in ms} for k in (0,2,4)}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cc):
    F={0:0.0,2:49*(B+5*Cc/35),4:441*Cc/35}
    V=np.zeros((5,5))
    for i,m in enumerate(ms):
        V[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    h=np.zeros((10,10))
    for a in range(10):
        for b in range(10):
            if so[a][1]==so[b][1]: h[a,b]=V[ms.index(so[a][0]),ms.index(so[b][0])]
    def g(a,b,c,d): # <ab|cd>
        if so[a][1]!=so[c][1] or so[b][1]!=so[d][1]: return 0
        m1,m2,m3,m4=so[a][0],so[b][0],so[c][0],so[d][0]
        if m1+m2!=m3+m4: return 0
        return sum(C[k][(m1,m3)]*C[k][(m4,m2)]*F[k] for k in (0,2,4))
    N=len(dets);H=np.zeros((N,N))
    # second quantization brute force
    def apply(ops,det):
        # ops list of (type,orb) applied right to left; return sign,det
        st=list(det);sign=1
        for t,o in reversed(ops):
            if t=='a':
                if o not in st: return 0,None
                p=st.index(o);sign*=(-1)**p;st.pop(p)
            else:
                if o in st: return 0,None
                p=sum(1 for x in st if x<o);sign*=(-1)**p;st.insert(p,o)
        return sign,tuple(st)
    for j,d in enumerate(dets):
        for a in range(10):
            for b in range(10):
                if h[a,b]!=0:
                    s,nd=apply([('c',a),('a',b)],d)
                    if s: H[idx[nd],j]+=s*h[a,b]
        for p in range(10):
         for q in range(10):
          for r in d:
           for t in d:
            v=g(p,q,r,t)
            if v==0: continue
            s,nd=apply([('c',p),('c',q),('a',t),('a',r)],d)
            if s: H[idx[nd],j]+=0.5*s*v
    # S^2
    return H
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc);e=np.linalg.eigvalsh(H);e=e-e[0]
    u=[];
    for x in e:
        if not u or x-u[-1][0]>1e-3: u.append([x,1])
        else: u[-1][1]+=1
    return u
for x in levels(1417,878,3500)[:8]: print(x)
