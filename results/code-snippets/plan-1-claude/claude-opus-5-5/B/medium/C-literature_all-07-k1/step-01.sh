
cat << 'EOF' > /tmp/d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (0,1)]
# Coulomb integrals <ab|cd> with F0,F2,F4
def ck(k,m1,m2):
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5
cache={}
def U(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*ck(k,ma,mc)*ck(k,md,mb) for k in (0,2,4))
dets=list(itertools.combinations(range(10),5))
dets=[d for d in dets if sum(1 if so[i][1] else -1 for i in d)==3]  # Ms=3/2
idx={d:i for i,d in enumerate(dets)}
# crystal field in real d basis: t2g -4Dq, eg +6Dq ; in complex ml basis
V=np.zeros((5,5))
# ml basis: Oh: <2|V|2>=Dq, <0|V|0>=6Dq, <1|V|1>=-4Dq, <2|V|-2>=5Dq
def cf(Dq):
    M=np.diag([Dq,-4*Dq,6*Dq,-4*Dq,Dq]); M[0,4]=M[4,0]=5*Dq; return M
def H(Dq,B,C):
    F2=(B*49+C*7/5*0)  # use F2=49B+7C ->F2(scaled) ; F4=441C/35
    F={0:0,2:(49*B+7*C)/49* 1,4:(441*C/35)/441}
    # ck normalized such that F^k / D_k: F2=F^2/49,F4=F^4/441; ck as computed are c^k*? compute raw c^k
    n=len(dets); Hm=np.zeros((n,n))
    v=cf(Dq)
    for I,d in enumerate(dets):
        for i in d:
            for j in range(10):
                if so[j][1]!=so[i][1]: continue
                val=v[ml.index(so[j][0]),ml.index(so[i][0])]
                if val==0: continue
                if j!=i and j in d: continue
                nd=list(d); nd[nd.index(i)]=j
                perm=np.argsort(nd); sgn=np.linalg.det(np.eye(5)[perm]) 
                Hm[idx[tuple(sorted(nd))],I]+=val*round(sgn)
        for a,b in itertools.combinations(d,2):
            for c,e in itertools.combinations(range(10),2):
                rest=[x for x in d if x not in (a,b)]
                if c in rest or e in rest: continue
                val=U(c,e,a,b,F)-U(c,e,b,a,F)
                if abs(val)<1e-12: continue
                nd=list(d); nd[nd.index(a)]=c; nd[nd.index(b)]=e
                perm=np.argsort(nd); sgn=round(np.linalg.det(np.eye(5)[perm]))
                Hm[idx[tuple(sorted(nd))],I]+=val*sgn
    return Hm
# check raw ck normalization: ck(2,2,2) should be -2/7 times? standard c2(2,2)=-2/7 -> with F2=F^2/49 multiply by 7
print(ck(2,2,2),ck(4,2,2))
EOF
python3 /tmp/d5.py
