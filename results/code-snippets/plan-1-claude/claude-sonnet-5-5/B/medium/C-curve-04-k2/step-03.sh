cat > /tmp/a.py <<'E'
import numpy as np, itertools
from math import factorial as f, sqrt
def tj(j1,j2,j3,m1,m2,m3):
    if m1+m2+m3!=0: return 0
    if abs(m1)>j1 or abs(m2)>j2 or abs(m3)>j3: return 0
    if j3<abs(j1-j2) or j3>j1+j2: return 0
    D=lambda a,b,c: f(a+b-c)*f(a-b+c)*f(-a+b+c)/f(a+b+c+1)
    pre=(-1)**(j1-j2-m3)*sqrt(D(j1,j2,j3)*f(j1+m1)*f(j1-m1)*f(j2+m2)*f(j2-m2)*f(j3+m3)*f(j3-m3))
    s=0
    for t in range(0,40):
        a=[t,j3-j2+t+m1,j3-j1+t-m2,j1+j2-j3-t,j1-t-m1,j2-t+m2]
        if min(a)<0: continue
        d=1
        for x in a:d*=f(x)
        s+=(-1)**t/d
    return pre*s
def ck(k,m,mp): # <2m|C^k|2m'>
    return (-1)**m*5*tj(2,k,2,0,0,0)*tj(2,k,2,-m,m-mp,mp)
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
def run(B,C,Dq):
    F4=C/35;F2=B+5*F4
    Fk={0:0,2:49*F2,4:441*F4}
    V={}
    # <ab|cd> direct-form: <ab|1/r12|cd>
    def eri(a,b,c,d):
        if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]: return 0
        return sum(ck(k,a[0],c[0])*ck(k,d[0],b[0])*Fk[k] for k in (2,4))
    # note k=0 omitted (constant)
    h=np.zeros((10,10))
    cf={2:1,1:-4,0:6,-1:-4,-2:1}
    for i,a in enumerate(orbs):
        for j,b in enumerate(orbs):
            if a[1]!=b[1]:continue
            if a[0]==b[0]: h[i,j]=cf[a[0]]*Dq
            elif abs(a[0])==2 and a[0]==-b[0]: h[i,j]=5*Dq
    g=np.zeros((10,)*4)
    for i,j,k,l in itertools.product(range(10),repeat=4):
        g[i,j,k,l]=eri(orbs[i],orbs[j],orbs[k],orbs[l])
    dets=[c for c in itertools.combinations(range(10),5)]
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets);H=np.zeros((N,N))
    def ap(op,det): # apply a†_p a_q etc; returns list
        pass
    def anni(q,d):
        if q not in d:return None
        s=(-1)**sum(1 for x in d if x<q);return s,tuple(x for x in d if x!=q)
    def crea(p,d):
        if p in d:return None
        s=(-1)**sum(1 for x in d if x<p);return s,tuple(sorted(d+(p,)))
    nz1=[(p,q) for p in range(10) for q in range(10) if abs(h[p,q])>1e-12]
    nz2=[(p,q,r,s) for p in range(10) for q in range(10) for r in range(10) for s in range(10) if abs(g[p,q,r,s])>1e-12]
    for d in dets:
        i=idx[d]
        for p,q in nz1:
            r=anni(q,d)
            if r is None:continue
            r2=crea(p,r[1])
            if r2 is None:continue
            H[idx[r2[1]],i]+=h[p,q]*r[0]*r2[0]
        # 1/2 sum <pq|rs> a†p a†q a_s a_r
        for p,q,r_,s_ in nz2:
            x=anni(r_,d)
            if x is None:continue
            y=anni(s_,x[1])
            if y is None:continue
            z=crea(q,y[1])
            if z is None:continue
            w=crea(p,z[1])
            if w is None:continue
            H[idx[w[1]],i]+=0.5*g[p,q,r_,s_]*x[0]*y[0]*z[0]*w[0]
    return np.array(H),dets
import sys
B=800.;C=3473.
for x in (1.45,2.55,3.25):
    H,dets=run(1.0,C/B,x)
    # restrict Ms=1/2 sector
    sel=[i for i,d in enumerate(dets) if sum(orbs[o][1] for o in d)==0.5]
    Hs=H[np.ix_(sel,sel)]
    # S^2 not needed: use Ms=5/2 sector for sextet energy
    w=np.linalg.eigvalsh(Hs)
    # group
    g=[];
    for e in w:
        if g and abs(e-g[-1][0])<1e-6:g[-1][1]+=1
        else:g.append([e,1])
    print(x,[(round(e-w[0],3),n) for e,n in g[:14]])
E
python3 /tmp/a.py