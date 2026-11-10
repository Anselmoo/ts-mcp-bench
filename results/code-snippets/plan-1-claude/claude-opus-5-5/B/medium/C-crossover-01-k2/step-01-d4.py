import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=706.,2734.
F4p=C/35; F2p=B+5*F4p
Fk={0:0.0,2:49*F2p,4:441*F4p}
ml=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * gaunt... use formula
    return float((-1)**m1*5*__import__('sympy').physics.wigner.wigner_3j(2,k,2,0,0,0)*__import__('sympy').physics.wigner.wigner_3j(2,k,2,-m1,m1-m2,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml}
def R(m1,m2,m3,m4): # <m1 m2|1/r|m3 m4>
    if m1+m2!=m3+m4: return 0.
    return sum(CK[(k,m1,m3)]*CK[(k,m4,m2)]*Fk[k] for k in (0,2,4))
# crystal field in real basis -> complex: Oh Dq: m=0:6Dq, ±1:-4Dq, ±2: Dq, <2|V|-2>=5Dq
def hcf(Dq):
    h=np.zeros((5,5))
    i={m:j for j,m in enumerate(ml)}
    h[i[0],i[0]]=6*Dq
    for m in (1,-1): h[i[m],i[m]]=-4*Dq
    for m in (2,-2): h[i[m],i[m]]=Dq
    h[i[2],i[-2]]=h[i[-2],i[2]]=5*Dq
    return h
so=[(m,s) for m in ml for s in (0,1)]
dets=list(itertools.combinations(range(10),4))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def two_body():
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p,q in itertools.combinations(range(4),2):
            a,b=d[p],d[q]
            for c_,e in itertools.combinations(range(10),2):
                rest=[x for x in d if x not in(a,b)]
                if c_ in rest or e in rest: continue
                # matrix element <..c e..|V|..a b..> antisym
                ma,sa=so[a];mb,sb=so[b];mc,sc=so[c_];me,se=so[e]
                v=0
                if sa==sc and sb==se: v+=R(mc,me,ma,mb)
                if sa==se and sb==sc: v-=R(me,mc,ma,mb)
                if abs(v)<1e-12: continue
                # replace a->c, b->e: phase
                lst=list(d); lst[p]=c_; lst[q]=e
                perm=sorted(range(4),key=lambda k:lst[k])
                new=tuple(lst[k] for k in perm)
                # parity
                sgn=np.linalg.det(np.eye(4)[perm])
                H[idx[new],I]+=v*sgn
    return H
def one_body(h):
    H=np.zeros((N,N))
    for I,d in enumerate(dets):
        for p,a in enumerate(d):
            for c_ in range(10):
                if so[c_][1]!=so[a][1]: continue
                v=h[ml.index(so[c_][0]),ml.index(so[a][0])]
                if v==0: continue
                if c_!=a and c_ in d: continue
                lst=list(d); lst[p]=c_
                perm=sorted(range(4),key=lambda k:lst[k])
                new=tuple(lst[k] for k in perm)
                sgn=np.linalg.det(np.eye(4)[perm])
                H[idx[new],I]+=v*sgn
    return H
V=two_body(); H1=one_body(hcf(1.0))
Ms=np.array([sum(0.5 if so[x][1] else -0.5 for x in d) for d in dets])
def gap(Dq):
    H=V+Dq*H1
    sel=np.where(Ms==2)[0]; e5=np.linalg.eigvalsh(H[np.ix_(sel,sel)])[0]
    sel=np.where(Ms==1)[0]; e=np.linalg.eigvalsh(H[np.ix_(sel,sel)])
    # lowest Ms=1 states include quintet; get lowest non-quintet
    sel0=np.where(Ms==0)[0]; e0=np.linalg.eigvalsh(H[np.ix_(sel0,sel0)])
    return e5, e[:12], e0[:12]
for Dq in [0,1000,2000,2500,3000]:
    print(Dq,gap(Dq)[0],gap(Dq)[1][:5])
def f(Dq):
    H=V+Dq*H1
    sel=np.where(Ms==2)[0]; e5=np.linalg.eigvalsh(H[np.ix_(sel,sel)])[0]
    sel=np.where(Ms==1)[0]; e=np.linalg.eigvalsh(H[np.ix_(sel,sel)])
    lows=[x for x in e if abs(x-e5)>1e-6]
    return e5-lows[0]
print(brentq(f,1000,4000))
