import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (0,1)]
cc_={}
def c(k,m1,m2):
    key=(k,m1,m2)
    if key not in cc_: cc_[key]=float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
    return cc_[key]
def U(a,b,cc,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[cc],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(c(k,ma,mc)*c(k,md,mb)*F[k] for k in (0,2,4))
def hcf(Dq):
    h=np.zeros((5,5)); i={m:j for j,m in enumerate(ml)}
    h[i[2],i[2]]=h[i[-2],i[-2]]=Dq; h[i[0],i[0]]=6*Dq
    h[i[1],i[1]]=h[i[-1],i[-1]]=-4*Dq; h[i[2],i[-2]]=h[i[-2],i[2]]=5*Dq
    return h
dets=list(itertools.combinations(range(10),3)); idx={d:i for i,d in enumerate(dets)}
def sgn(l):
    s=1
    for i in range(3):
        for j in range(i+1,3):
            if l[i]>l[j]: s=-s
    return s
def H(Dq,B,C):
    F={0:0,2:49*(B+C/7),4:441*C/35}
    h1=hcf(Dq); N=len(dets); M=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=h1[ml.index(so[q][0]),ml.index(so[p][0])]
                if v==0: continue
                l=list(d)
                if q in l and q!=p: continue
                l[l.index(p)]=q
                M[idx[tuple(sorted(l))],I]+=v*sgn(l)
        for a,b in itertools.combinations(d,2):
            rest=[x for x in d if x not in (a,b)]
            for x in range(10):
                for y in range(10):
                    if x==y or x in rest or y in rest: continue
                    v=U(x,y,a,b,F)
                    if v==0: continue
                    l=list(d); ia=d.index(a); ib=d.index(b); l[ia]=x; l[ib]=y
                    M[idx[tuple(sorted(l))],I]+=v*sgn(l)
    return M
def levels(Dq,B,C):
    e=np.linalg.eigvalsh(H(Dq,B,C)); return e-e[0]
def uniq(e):
    u=[]
    for x in e:
        if not u or x-u[-1][0]>0.5: u.append([x,1])
        else: u[-1][1]+=1
    return [(round(a,1),n) for a,n in u]
print(uniq(levels(0,618,2800))[:5])
from scipy.optimize import brentq
f=lambda C: uniq(levels(1750,618,C))[1][0]-12090
print(uniq(levels(1750,618,3000))[:8])
C=brentq(f,1500,4000); print(C, C/618, uniq(levels(1750,618,C))[:8])
