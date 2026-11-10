import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (0,1)]
# ck coefficients
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(5*5/(2*k+1))*0+0)
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
def U(a,b,cc,d,F):  # <ab|1/r|cd>, a,c electron1
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[cc],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(c(k,ma,mc)*c(k,md,mb)*F[k] for k in (0,2,4))
# crystal field: cubic, real d-basis -> complex; use Dq oper
def hcf(Dq):
    h=np.zeros((5,5))
    # octahedral V in |m>: <±2|V|±2>=Dq, <0|V|0>=6Dq, <±1|±1>=-4Dq, <2|V|-2>=5Dq
    i={m:j for j,m in enumerate(ml)}
    h[i[2],i[2]]=h[i[-2],i[-2]]=Dq; h[i[0],i[0]]=6*Dq
    h[i[1],i[1]]=h[i[-1],i[-1]]=-4*Dq; h[i[2],i[-2]]=h[i[-2],i[2]]=5*Dq
    return h
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def H(Dq,B,C):
    F={0:0,2:49*B+7*C,4:441*C/35}
    F2=B*49+7*C; F4=C*63/5  # F2=49F2' etc: B=F2'-5F4', C=35F4', F2=49F2', F4=441F4'
    F={0:0,2:49*(B+5*C/35),4:441*C/35}
    h1=hcf(Dq); N=len(dets); M=np.zeros((N,N))
    def apply(ops,det):
        pass
    for I,d in enumerate(dets):
        # one-body
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=h1[ml.index(so[q][0]),ml.index(so[p][0])]
                if v==0: continue
                l=list(d); pos=l.index(p); 
                if q in l and q!=p: continue
                l[pos]=q; sign=1
                perm=sorted(range(3),key=lambda x:l[x]); 
                # parity
                s=np.linalg.det(np.eye(3)[perm]); 
                M[idx[tuple(sorted(l))],I]+=v*s
        # two-body
        for a,b in itertools.combinations(d,2):
            for cc in range(10):
                for dd in range(10):
                    if cc==dd: continue
                    rest=[x for x in d if x not in (a,b)]
                    if cc in rest or dd in rest: continue
                    v=U(cc,dd,a,b,F)
                    if v==0: continue
                    l=list(d); l[l.index(a)]=cc; l[l.index(b)]=dd
                    perm=sorted(range(3),key=lambda x:l[x])
                    s=np.linalg.det(np.eye(3)[perm])
                    M[idx[tuple(sorted(l))],I]+=v*s
    return M
def levels(Dq,B,C):
    M=H(Dq,B,C); e=np.linalg.eigvalsh(M); 
    return np.round(e-e[0],1)
import sys
Dq,B=1750,618
for C in [2000,3000]:
    e=levels(Dq,B,C); u=sorted(set(e)); print(C,u[:8])
