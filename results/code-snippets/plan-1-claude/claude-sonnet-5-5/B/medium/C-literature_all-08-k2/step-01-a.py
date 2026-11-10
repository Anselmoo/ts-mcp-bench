import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
from math import sqrt
ms=[2,1,0,-1,-2]
def ck(k,ma,mc):
    # <l ma|C^k|l mc>
    return float((-1)**ma*sqrt(5*5)*0+0) 
from sympy.physics.wigner import wigner_3j
def c(k,ma,mc):
    return float((-1)**ma*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-ma,ma-mc,mc))
C={(k,a,b):c(k,a,b) for k in(0,2,4) for a in ms for b in ms}
so=[(m,s) for s in(0.5,-0.5) for m in ms]
dets=[]
for up in itertools.combinations(range(5),4):
  for dn in range(5):
    dets.append(tuple(sorted([i for i in up]+[5+dn])))
idx={d:i for i,d in enumerate(dets)}
def V2(a,b,c_,d,F):
    # <ab|g|cd>
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c_],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    t=0
    for k,f in zip((0,2,4),F):
        t+=C[(k,ma,mc)]*C[(k,md,mb)]*f
    return t
def apply(op_list,det):
    pass
def build(F,Dq):
    n=len(dets);H=np.zeros((n,n))
    h=np.zeros((10,10))
    for s in range(2):
        for i,m in enumerate(ms):
            h[5*s+i,5*s+i]=Dq*{2:1,1:-4,0:6,-1:-4,-2:1}[m]
        h[5*s+0,5*s+4]=h[5*s+4,5*s+0]=5*Dq
    def ann(d,p):
        if p not in d: return None
        i=d.index(p);return tuple(x for x in d if x!=p),(-1)**i
    def cre(d,p):
        if p in d: return None
        l=list(d);pos=sum(1 for x in l if x<p);l.insert(pos,p);return tuple(l),(-1)**pos
    for d in dets:
        j=idx[d]
        for p in range(10):
            for q in range(10):
                if h[p,q]==0: continue
                r=ann(d,q)
                if not r: continue
                r2=cre(r[0],p)
                if not r2: continue
                H[idx[r2[0]],j]+=h[p,q]*r[1]*r2[1]
        # two-body 1/2 sum <ab|cd> a†b†dc
        for c_ in d:
            for d_ in d:
                if c_==d_: continue
                r=ann(d,c_)
                r=(r[0],r[1]); r_=ann(r[0],d_)
                sg=r[1]*r_[1]
                for a in range(10):
                    for b in range(10):
                        v=V2(a,b,c_,d_,F)
                        if v==0: continue
                        x=cre(r_[0],b)
                        if not x: continue
                        y=cre(x[0],a)
                        if not y: continue
                        H[idx[y[0]],j]+=0.5*v*sg*x[1]*y[1]
    return H
def F(B,Cc):
    F4=63*Cc/5*0+Cc*35/441*0
    # B=(F2-5F4)/49, C=35F4/441
    F4=441*Cc/35;F2=49*B+5*F4
    return (0,F2,F4)
def levels(B,Cc,Dq):
    H=build(F(B,Cc),Dq);w=np.linalg.eigvalsh(H);w=np.round(w-w[0],3)
    return w
w=levels(860,3200,800);print(sorted(set(np.round(w))))
def res(p):
    B,Cc,Dq=p;w=levels(B,Cc,Dq);u=np.array(sorted(set(np.round(w,1))))
    return u
