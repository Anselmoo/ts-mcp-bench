import numpy as np, itertools
from math import factorial as f, sqrt
def w3j(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0
    if j3>j1+j2 or j3<abs(j1-j2) or abs(m1)>j1 or abs(m2)>j2 or abs(m3)>j3: return 0
    t=lambda x:f(int(round(x)))
    pre=(-1)**int(j1-j2-m3)*sqrt(t(j1+j2-j3)*t(j1-j2+j3)*t(-j1+j2+j3)/t(j1+j2+j3+1))
    pre*=sqrt(t(j1+m1)*t(j1-m1)*t(j2+m2)*t(j2-m2)*t(j3+m3)*t(j3-m3))
    s=0
    for k in range(0,40):
        a=[k,j1+j2-j3-k,j1-m1-k,j2+m2-k,j3-j2+m1+k,j3-j1-m2+k]
        if min(a)<0: continue
        s+=(-1)**k/np.prod([t(x) for x in a])
    return pre*s
def ck(k,m,mp):
    return (-1)**m*5*w3j(2,k,2,0,0,0)*w3j(2,k,2,-m,m-mp,mp)
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]  # index
N=10
dets=[c for c in itertools.combinations(range(N),5) if sum(o%2 for o in c)==2]  # 3 up,2 down
idx={d:i for i,d in enumerate(dets)}
def apply(op,d):
    # op list of (type,orb) applied right to left; return sign,newdet
    l=list(d);sg=1
    for t,o in reversed(op):
        if t=='a':
            if o not in l: return 0,None
            p=l.index(o);sg*=(-1)**p;l.pop(p)
        else:
            if o in l: return 0,None
            p=sum(1 for x in l if x<o);sg*=(-1)**p;l.insert(p,o)
    return sg,tuple(l)
def build(Dq,B,C):
    F4=C/35;F2=B+5*F4;F={0:0,2:49*F2,4:441*F4}
    # F0 irrelevant (constant for fixed N)
    def g(m1,m2,m3,m4):
        return sum(ck(k,m1,m3)*ck(k,m4,m2)*F[k] for k in (2,4))
    H=np.zeros((len(dets),)*2)
    # one-body
    h=-4*Dq*np.eye(5)+10*Dq*np.zeros((5,5))
    P=np.zeros((5,5));P[2,2]=1
    e=np.zeros(5);e[0]=e[4]=1/sqrt(2);P+=np.outer(e,e)
    h=-4*Dq*np.eye(5)+10*Dq*P
    for j,d in enumerate(dets):
        for a in range(5):
            for b in range(5):
                if h[a,b]==0: continue
                for s in (0,1):
                    sg,nd=apply([('c',2*a+s),('a',2*b+s)],d)
                    if sg: H[idx[nd],j]+=sg*h[a,b]
    G={}
    for m1 in ms:
     for m2 in ms:
      for m3 in ms:
       m4=m1+m2-m3
       if abs(m4)>2: continue
       G[(m1,m2,m3,m4)]=g(m1,m2,m3,m4)
    for (m1,m2,m3,m4),v in G.items():
        if abs(v)<1e-12: continue
        for s1 in (0,1):
         for s2 in (0,1):
          op=[('c',2*(m1+2)+s1),('c',2*(m2+2)+s2),('a',2*(m4+2)+s2),('a',2*(m3+2)+s1)]
          for j,d in enumerate(dets):
            sg,nd=apply(op,d)
            if sg: H[idx[nd],j]+=0.5*v*sg
    return H
# S^2
def S2():
    n=len(dets);M=np.zeros((n,n))
    Sz=0.5
    # S- S+ + Sz^2+Sz
    def sp(vec):
        out=np.zeros(n)
        for j,d in enumerate(dets):
            pass
    return None
