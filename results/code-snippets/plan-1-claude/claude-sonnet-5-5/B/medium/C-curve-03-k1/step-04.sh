cat > <SANDBOX_TMP>/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
B=1.0;C=3699/784
F4r=C/35;F2r=B+5*F4r;F=[0,0,49*F2r,0,441*F4r]
ms=[-2,-1,0,1,2]
def Y(m1,k,q,m3):
    return float(N((-1)**m1*gaunt(2,k,2,-m1,q,m3)))
def V(a,b,c,d):
    s=0
    for k in (2,4):
        t=0
        for q in range(-k,k+1):
            t+=Y(a,k,q,c)*(-1)**q*Y(b,k,-q,d)
        s+=F[k]*4*np.pi/(2*k+1)*t
    return s
G=np.zeros((5,5,5,5))
for a,b,c,d in itertools.product(range(5),repeat=4):
    if ms[a]+ms[b]==ms[c]+ms[d]: G[a,b,c,d]=V(ms[a],ms[b],ms[c],ms[d])
n=10
g=np.zeros((n,n,n,n))
for a,b,c,d in itertools.product(range(5),repeat=4):
    if G[a,b,c,d]!=0:
        for s in (0,1):
            for t in (0,1):
                g[2*a+s,2*b+t,2*c+s,2*d+t]=G[a,b,c,d]
def szz(d):
    u=sum((d>>(2*i))&1 for i in range(5));w=sum((d>>(2*i+1))&1 for i in range(5));return (u-w)/2
def ap(op,dt,create):
    occ=(dt>>op)&1
    if create==occ: return None
    return dt^(1<<op),(-1)**bin(dt&((1<<op)-1)).count('1')
def run(dq,target):
    h=np.zeros((5,5));r=1/np.sqrt(2);idx={m:i for i,m in enumerate(ms)}
    def vec(d):
        v=np.zeros(5)
        for m,c in d.items(): v[idx[m]]=c
        return v
    eg=[vec({0:1}),vec({2:r,-2:r})];t2=[vec({1:1}),vec({-1:1}),vec({2:r,-2:-r})]
    for v in eg: h+=6*dq*np.outer(v,v)
    for v in t2: h+=-4*dq*np.outer(v,v)
    H1=np.kron(h,np.eye(2))
    dets=[sum(1<<i for i in c) for c in itertools.combinations(range(n),7)]
    dets=[d for d in dets if szz(d)==target]
    di={d:i for i,d in enumerate(dets)}
    Hm=np.zeros((len(dets),)*2)
    nz=[tuple(x) for x in np.argwhere(g!=0)]
    for j,dt in enumerate(dets):
        for p in range(n):
            for q in range(n):
                if H1[p,q]==0: continue
                r1=ap(q,dt,0)
                if not r1: continue
                r2=ap(p,r1[0],1)
                if not r2: continue
                Hm[di[r2[0]],j]+=H1[p,q]*r1[1]*r2[1]
        for p,q,r_,s in nz:
            st=dt;sg=1;ok=True
            for op,cr in ((r_,0),(s,0),(q,1),(p,1)):
                t=ap(op,st,cr)
                if not t: ok=False;break
                st,sg=t[0],sg*t[1]
            if ok: Hm[di[st],j]+=0.5*g[p,q,r_,s]*sg
    return np.linalg.eigvalsh(Hm)
def grp(e):
    o=[]
    for x in e:
        if o and abs(x-o[-1][0])<1e-6: o[-1][1]+=1
        else: o.append([x,1])
    return o
for dq in (1.45,2.45,3.0):
    gq=grp(run(dq,1.5));gd=grp(run(dq,0.5))
    qd={round(x,4):m for x,m in gq}
    allv=[(x,m,'4') for x,m in gq]
    for x,m in gd:
        k=qd.get(round(x,4),0)
        if m-k>0: allv.append((x,m-k,'2'))
    allv.sort();e0=allv[0][0]
    print(dq,[(round(x-e0,3),m,s) for x,m,s in allv[:8]],flush=True)
E
python3 <SANDBOX_TMP>/a.py