import numpy as np, itertools, functools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=621.,2851.
F4s=C/35; F2s=B+5*F4s
Fk={0:0.,2:49*F2s,4:441*F4s}
ml=[-2,-1,0,1,2]
def ck(k,m1,m2):
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2))
@functools.lru_cache(None)
def g(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*Fk[k] for k in (0,2,4))
V=np.zeros((5,5)); idx={m:i for i,m in enumerate(ml)}
V[idx[0],idx[0]]=6; V[idx[1],idx[1]]=-4; V[idx[-1],idx[-1]]=-4
V[idx[2],idx[2]]=1; V[idx[-2],idx[-2]]=1; V[idx[2],idx[-2]]=5; V[idx[-2],idx[2]]=5
so=[(m,s) for m in ml for s in (0,1)]
dets=list(itertools.combinations(range(10),5)); D={d:i for i,d in enumerate(dets)}; N=len(dets)
H1=np.zeros((N,N)); H2=np.zeros((N,N))
def apply(ops,det):
    st=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return 0,None
            i=st.index(o); sign*=(-1)**i; st.pop(i)
        else:
            if o in st: return 0,None
            i=sum(1 for x in st if x<o); sign*=(-1)**i; st.insert(i,o)
    return sign,tuple(st)
for d in dets:
    j=D[d]
    for p in range(10):
        for q in range(10):
            if so[p][1]!=so[q][1]: continue
            v=V[idx[so[p][0]],idx[so[q][0]]]
            if v==0: continue
            s,nd=apply([('c',p),('a',q)],d)
            if s: H1[D[nd],j]+=s*v
    for p in range(10):
     for q in range(10):
      for r in range(10):
       for t in range(10):
        if so[p][1]!=so[r][1] or so[q][1]!=so[t][1]: continue
        v=g(so[p][0],so[q][0],so[r][0],so[t][0])
        if abs(v)<1e-12: continue
        s,nd=apply([('c',p),('c',q),('a',t),('a',r)],d)
        if s: H2[D[nd],j]+=0.5*s*v
def Ms(d): return sum(0.5 if so[o][1]==0 else -0.5 for o in d)
sel52=[i for i,d in enumerate(dets) if Ms(d)==2.5]
sel32=[i for i,d in enumerate(dets) if Ms(d)==1.5]
sel12=[i for i,d in enumerate(dets) if Ms(d)==0.5]
def f(Dq):
    H=H1*Dq+H2
    e52=np.linalg.eigvalsh(H[np.ix_(sel52,sel52)])[0]
    e32=np.linalg.eigvalsh(H[np.ix_(sel32,sel32)])
    e12=np.linalg.eigvalsh(H[np.ix_(sel12,sel12)])
    dbl=[e for e in e12 if np.min(abs(e32-e))>1e-6][0]
    qrt=[e for e in e32 if abs(e-e52)>1e-6][0]
    return e52,qrt,dbl
print(f(0))
for Dq in [1500,2000,2500,3000]: print(Dq,f(Dq))
r=brentq(lambda x:f(x)[2]-f(x)[0],1000,5000); print(r, f(r))
print('diag approx',(15*B+10*C)/20)
