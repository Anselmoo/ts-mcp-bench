import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
from math import sqrt,pi
ms=[-2,-1,0,1,2]
def c(k,m1,m3):
    q=m1-m3
    if abs(q)>k: return 0.0
    return float((-1)**m1*sqrt(4*pi/(2*k+1))*gaunt(2,k,2,-m1,q,m3))
so=[(m,s) for s in (1,-1) for m in ms]
Cc_={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
def psign(l):
    s=1
    for i in range(len(l)):
        for j in range(i+1,len(l)):
            if l[i]>l[j]: s=-s
    return s
def V(i,j,k,l,F):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[i],so[j],so[k],so[l]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    return sum(Cc_[(kk,m1,m3)]*Cc_[(kk,m4,m2)]*F[kk] for kk in (2,4))
def H(B,C,Dq,Ms):
    F={2:49*B+7*C,4:63*C/5}
    dets=[d for d in itertools.combinations(range(10),4) if sum(so[i][1] for i in d)==Ms]
    idx={d:i for i,d in enumerate(dets)}
    n=len(dets);M=np.zeros((n,n))
    vd={2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}
    for d in dets:
        a=idx[d]
        for p in d: M[a,a]+=vd[so[p][0]]
        for p in d:
            m,s=so[p]
            if m in(2,-2):
                q=so.index((-m,s))
                if q in d: continue
                nd=list(d);nd[nd.index(p)]=q
                M[idx[tuple(sorted(nd))],a]+=5*Dq*psign(nd)
        for (p,q) in itertools.combinations(d,2):
            rest=[x for x in d if x not in(p,q)]
            for r in range(10):
              for t in range(r+1,10):
                if r in rest or t in rest: continue
                amp=0
                for (k,l) in((p,q),(q,p)):
                    for (rr,tt) in((r,t),(t,r)):
                        val=V(rr,tt,k,l,F)
                        if val==0: continue
                        i=list(d).index(k);s1=(-1)**i
                        d2=[x for x in d if x!=k];j=d2.index(l);s2=(-1)**j
                        o=[x for x in d2 if x!=l]
                        o=[rr,tt]+o
                        amp+=0.5*val*s1*s2*psign(o)
                if amp!=0:
                    nd=tuple(sorted(rest+[r,t]))
                    M[idx[nd],a]+=amp
    return M
def trip(B,C,Dq):
    e1=np.linalg.eigvalsh(H(B,C,Dq,2)); e2=list(np.linalg.eigvalsh(H(B,C,Dq,4)))
    t=list(e1)
    for q in e2:
        k=int(np.argmin([abs(x-q) for x in t])); t.pop(k)
    return np.array(sorted(t))
M=H(900,4230,2000,2);print(np.abs(M-M.T).max())
t=trip(900,4230,2000);print(t[:8]-t[0])
obs=np.array([18850,19750,20560])
def res(p):
    t=trip(p[1],4.7*p[1],p[0]);return (t[1:4]-t[0])-obs
for g in [(2000,600),(2400,700),(1800,900),(2800,500)]:
    r=least_squares(res,g,x_scale=[100,50]);print(g,r.x,r.fun,r.cost)
