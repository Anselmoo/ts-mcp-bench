
python3 - << 'EOF' 2>&1 | tail -5
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
orbs=[(m,s) for m in range(-2,3) for s in (0.5,-0.5)]
cc_={}
def c(k,m1,m2):
    key=(k,m1,m2)
    if key not in cc_: cc_[key]=float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
    return cc_[key]
def eri(a,b,cc,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[cc],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(c(k,ma,mc)*c(k,md,mb)*F[k] for k in (2,4))
def cf(Dq):
    V=np.zeros((5,5))
    for m in range(-2,3): V[m+2,m+2]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    return V
dets=list(itertools.combinations(range(10),3)); idx={d:i for i,d in enumerate(dets)}
def psign(nd):
    s=1
    for i in range(3):
        for j in range(i+1,3):
            if nd[i]>nd[j]: s=-s
    return s
def H(Dq,B,C):
    F={2:49*B+7*C,4:441*C/35}
    n=len(dets);Hm=np.zeros((n,n));V=cf(Dq)
    for i,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=V[orbs[q][0]+2,orbs[p][0]+2]
                if v==0 or (q!=p and q in d): continue
                nd=list(d); nd[nd.index(p)]=q
                Hm[idx[tuple(sorted(nd))],i]+=psign(nd)*v
        for a,b in itertools.combinations(d,2):
            rest=[x for x in d if x not in (a,b)]
            for x in range(10):
                for y in range(x+1,10):
                    if x in rest or y in rest: continue
                    val=eri(x,y,a,b,F)-eri(x,y,b,a,F)
                    if abs(val)<1e-12: continue
                    nd=list(d); nd[nd.index(a)]=x; nd[nd.index(b)]=y
                    Hm[idx[tuple(sorted(nd))],i]+=psign(nd)*val
    return Hm
def levels(Dq,B,C):
    e=np.linalg.eigvalsh(H(Dq,B,C)); e=e-e[0]; u=[]
    for x in e:
        if u and abs(x-u[-1][0])<0.5: u[-1][1]+=1
        else: u.append([x,1])
    return u
B=(64000-52290)/15
from scipy.optimize import brentq
g=lambda C: min(a for a,b in levels(1743,B,C)[1:] if b in (4,6))-15410
Cs=brentq(g,2000,3800); print(B,Cs, Cs/B)
print([(round(a),b) for a,b in levels(1743,B,Cs)[:6]])
EOF
