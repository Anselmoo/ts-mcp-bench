cd ~ 2>/dev/null; python3 - << 'EOF'
import itertools, numpy as np
from sympy.physics.wigner import wigner_3j
from math import pi, sqrt
from scipy.optimize import least_squares
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
N=len(orbs)
_c={}
def w3(a,b,c,d,e,f):
    key=(a,b,c,d,e,f)
    if key not in _c: _c[key]=float(wigner_3j(a,b,c,d,e,f))
    return _c[key]
def G(l1,l2,l3,m1,m2,m3):
    if m1+m2+m3!=0: return 0.0
    return sqrt((2*l1+1)*(2*l2+1)*(2*l3+1)/(4*pi))*w3(l1,l2,l3,0,0,0)*w3(l1,l2,l3,m1,m2,m3)
def ang(k,mi,mk,mj,ml):
    s=0.0
    for q in range(-k,k+1):
        A=(-1)**(mi+q)*G(l,k,l,-mi,-q,mk)
        if A==0: continue
        B=(-1)**mj*G(l,k,l,-mj,q,ml)
        s+=A*B
    return s
def build(Dq,B,C):
    F={0:0.0,2:49*B+7*C,4:63*C/5}
    V=np.zeros((N,N,N,N))
    for i,(mi,si) in enumerate(orbs):
     for j,(mj,sj) in enumerate(orbs):
      for k,(mk,sk) in enumerate(orbs):
       for ll,(ml,sl) in enumerate(orbs):
        if si!=sk or sj!=sl: continue
        if mi+mj!=mk+ml: continue
        V[i,j,k,ll]=sum(F[kk]*4*pi/(2*kk+1)*ang(kk,mi,mk,mj,ml) for kk in (0,2,4))
    h=np.zeros((N,N))
    v0=np.zeros(5); v0[2]=1.0
    vc=np.zeros(5); vc[0]=1/sqrt(2); vc[4]=1/sqrt(2)
    P=np.outer(v0,v0)+np.outer(vc,vc)
    hm=-4*Dq*np.eye(5)+10*Dq*P
    for i,(mi,si) in enumerate(orbs):
     for j,(mj,sj) in enumerate(orbs):
      if si==sj: h[i,j]=hm[mi+2,mj+2]
    return h,V
def dets_ms(nup,ndn):
    up=[i for i,(m,s) in enumerate(orbs) if s>0]
    dn=[i for i,(m,s) in enumerate(orbs) if s<0]
    return [tuple(sorted(a+b)) for a in itertools.combinations(up,nup) for b in itertools.combinations(dn,ndn)]
def ann(state,p):
    if p not in state: return None
    pos=state.index(p); return ((-1)**pos, tuple(x for x in state if x!=p))
def cre(state,p):
    if p in state: return None
    pos=sum(1 for x in state if x<p); return ((-1)**pos, tuple(sorted(state+(p,))))
def matrix(Dq,B,C):
    h,V=build(Dq,B,C)
    dets=dets_ms(5,2); idx={d:n for n,d in enumerate(dets)}
    M=np.zeros((len(dets),len(dets)))
    for c,dd in enumerate(dets):
        for j in dd:
            s1,st=ann(dd,j)
            for i in range(N):
                if h[i,j]==0: continue
                r=cre(st,i)
                if r is None: continue
                s2,st2=r
                M[idx[st2],c]+=s1*s2*h[i,j]
        for k in dd:
            s1,st=ann(dd,k)
            for ll in st:
                s2,st2=ann(st,ll)
                for j in range(N):
                    for i in range(N):
                        v=V[i,j,k,ll]
                        if v==0: continue
                        r3=cre(st2,j)
                        if r3 is None: continue
                        s3,st3=r3
                        r4=cre(st3,i)
                        if r4 is None: continue
                        s4,st4=r4
                        M[idx[st4],c]+=0.5*s1*s2*s3*s4*v
    return M
def bands(Dq,B,C):
    M=matrix(Dq,B,C); ev=np.sort(np.linalg.eigvalsh((M+M.T)/2))
    cl=[]; i=0
    while i<len(ev):
        j=i
        while j+1<len(ev) and abs(ev[j+1]-ev[i])<1e-3: j+=1
        cl.append((ev[i],j-i+1)); i=j+1
    gs=cl[0][0]
    return [c[0]-gs for c in cl]
obs=np.array([8620.,18410.,20250.])
def pred(Dq,B,ratio):
    t=bands(Dq,B,ratio*B)
    return np.array([t[1],t[2],t[3]])
for ratio in (4.0,4.5):
    f=lambda p: (pred(p[0],p[1],ratio)-obs)/obs
    s=least_squares(f,[900,900],xtol=1e-12,ftol=1e-12)
    print("C/B=",ratio,"Dq,B=",np.round(s.x,1),"pred",np.round(pred(*s.x,ratio),1),"obs",obs)
EOF