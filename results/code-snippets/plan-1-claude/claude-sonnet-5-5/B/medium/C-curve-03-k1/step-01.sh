cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N, pi, sqrt
B=1.0;C=3699/784
F4r=C/35;F2r=B+5*F4r;F=[0,0,49*F2r,0,441*F4r]
ms=[-2,-1,0,1,2]
def Y(m1,k,q,m3): # <m1|Y_kq|m3>
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
def run(dq):
    h=np.zeros((5,5))
    # eg/t2g in m basis
    r=1/np.sqrt(2);idx={m:i for i,m in enumerate(ms)}
    def vec(d):
        v=np.zeros(5)
        for m,c in d.items(): v[idx[m]]=c
        return v
    eg=[vec({0:1}),vec({2:r,-2:r})]
    t2=[vec({1:1}),vec({-1:1}),vec({2:r,-2:-r})]
    for v in eg: h+=6*dq*np.outer(v,v)
    for v in t2: h+=-4*dq*np.outer(v,v)
    # spin orbitals p=2*i+s
    n=10
    H1=np.kron(h,np.eye(2))
    g=np.zeros((n,n,n,n))
    for a,b,c,d in itertools.product(range(5),repeat=4):
        if G[a,b,c,d]!=0:
            for s in (0,1):
                for t in (0,1):
                    g[2*a+s,2*b+t,2*c+s,2*d+t]=G[a,b,c,d]
    dets=[sum(1<<i for i in cmb) for cmb in itertools.combinations(range(n),7)]
    di={d:i for i,d in enumerate(dets)}
    def ap(op,dt,create):
        occ=(dt>>op)&1
        if create==occ: return None
        sign=(-1)**bin(dt&((1<<op)-1)).count('1')
        return dt^(1<<op),sign
    N_=len(dets);Hm=np.zeros((N_,N_))
    for j,dt in enumerate(dets):
        for p in range(n):
            for q in range(n):
                if H1[p,q]==0: continue
                r1=ap(q,dt,0)
                if not r1: continue
                r2=ap(p,r1[0],1)
                if not r2: continue
                Hm[di[r2[0]],j]+=H1[p,q]*r1[1]*r2[1]
        for p,q,r_,s in itertools.product(range(n),repeat=4):
            x=g[p,q,r_,s]
            if x==0: continue
            # 1/2 x a†p a†q a_s a_r
            st=dt;sg=1
            ok=True
            for op,cr in ((r_,0),(s,0),(q,1),(p,1)):
                t=ap(op,st,cr)
                if not t: ok=False;break
                st,sg=t[0],sg*t[1]
            if ok: Hm[di[st],j]+=0.5*x*sg
    # S^2 via Sz and S+S-
    Sz=np.array([sum(0.5 if (not (d>>(2*i))&1)==0 and False else 0 for i in range(0)) for d in dets])
    return Hm,dets,di,ap
def levels(dq):
    Hm,dets,di,ap=run(dq)
    # restrict to Sz=1/2 : spin up (s=0) count 4, down 3 ; and also Ms=3/2 for quartets check
    def sz(d): return sum(0.5 if (d>>(2*i))&1 else 0 for i in range(5))-sum(0.5 if (d>>(2*i+1))&1 else 0 for i in range(5))*-1*-1
    def szz(d):
        u=sum((d>>(2*i))&1 for i in range(5));w=sum((d>>(2*i+1))&1 for i in range(5));return (u-w)/2
    out=[]
    for target,lab in ((1.5,'4'),(0.5,'2')):
        ids=[i for i,d in enumerate(dets) if szz(d)==target]
        e=np.linalg.eigvalsh(Hm[np.ix_(ids,ids)])
        out.append((lab,e))
    return out
for dq in (1.45,2.45,3.0):
    o=levels(dq)
    q=o[0][1]; d=o[1][1]
    def grp(e):
        g=[];
        for x in e:
            if g and abs(x-g[-1][0])<1e-6: g[-1][1]+=1
            else: g.append([x,1])
        return g
    gq=grp(q); 
    # Ms=1/2 contains quartets too; doublets = remove quartet levels
    gd=grp(d)
    qd={round(x,5):n for x,n in gq}
    doub=[]
    for x,nn in gd:
        k=qd.get(round(x,5),0)
        if nn-k>0: doub.append([x,nn-k])
    allv=[(x,n,'4') for x,n in gq]+[(x,n,'2') for x,n in doub]
    allv.sort(); e0=allv[0][0]
    print(dq,[(round(x-e0,3),n,s) for x,n,s in allv[:8]])
E
python3 /tmp/a.py