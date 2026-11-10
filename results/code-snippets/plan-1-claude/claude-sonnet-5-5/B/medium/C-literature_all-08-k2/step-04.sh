cd /dev/shm; cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=[2,1,0,-1,-2]
def c(k,ma,mc):
    return float((-1)**ma*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-ma,ma-mc,mc))
C={(k,a,b):c(k,a,b) for k in(0,2,4) for a in ms for b in ms}
so=[(m,s) for s in(0.5,-0.5) for m in ms]
dets=[]
for up in itertools.combinations(range(5),4):
  for dn in range(5):
    dets.append(tuple(sorted(list(up)+[5+dn])))
idx={d:i for i,d in enumerate(dets)}
def V2(a,b,c_,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c_],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(C[(k,ma,mc)]*C[(k,md,mb)]*f for k,f in zip((0,2,4),F))
def ann(d,p):
    if p not in d: return None
    i=d.index(p);return tuple(x for x in d if x!=p),(-1)**i
def cre(d,p):
    if p in d: return None
    l=list(d);pos=sum(1 for x in l if x<p);l.insert(pos,p);return tuple(l),(-1)**pos
one=[];two=[]
for d in dets:
    j=idx[d]
    for p in range(10):
        for q in range(10):
            if (p<5)!=(q<5): continue
            r=ann(d,q)
            if not r: continue
            r2=cre(r[0],p)
            if r2 and r2[0] in idx: one.append((idx[r2[0]],j,p,q,r[1]*r2[1]))
    for c_ in d:
        for d_ in d:
            if c_==d_: continue
            r=ann(d,c_);r_=ann(r[0],d_);sg=r[1]*r_[1]
            for a in range(10):
                for b in range(10):
                    x=cre(r_[0],b)
                    if not x: continue
                    y=cre(x[0],a)
                    if not y or y[0] not in idx: continue
                    two.append((idx[y[0]],j,a,b,c_,d_,sg*x[1]*y[1]))
def build(F,Dq):
    n=len(dets);H=np.zeros((n,n));h=np.zeros((10,10))
    for s in range(2):
        for i,m in enumerate(ms): h[5*s+i,5*s+i]=Dq*{2:1,1:-4,0:6,-1:-4,-2:1}[m]
        h[5*s,5*s+4]=h[5*s+4,5*s]=5*Dq
    for i,j,p,q,s in one: H[i,j]+=h[p,q]*s
    for i,j,a,b,c_,d_,s in two:
        v=V2(a,b,c_,d_,F)
        if v: H[i,j]+=0.5*v*s
    return H
def levels(B,Cc,Dq):
    F4=441*Cc/35;F2=49*B+5*F4
    w=np.linalg.eigvalsh(build((0,F2,F4),Dq));w=w-w[0]
    u=[]
    for x in w:
        if not u or x-u[-1]>0.5:u.append(x)
    return u
u=levels(860,3200,800);print(np.round(u[:8]),10*860+5*3200)
def res(p):
    u=levels(*p);return [u[1]-19180,u[2]-22130,u[3]-23370]
for g in [(800,3000,700),(700,3000,900)]:
    r=least_squares(res,g,x_scale=[100,100,100]);print(r.x,r.fun)
E
python3 a.py