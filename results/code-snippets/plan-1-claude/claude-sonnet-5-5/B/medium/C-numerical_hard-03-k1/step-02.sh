
mkdir -p ~/w 2>/dev/null; cd ~/w 2>/dev/null || cd /dev/shm; pwd
cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
Ck={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
def sgn(seq):
    return (-1)**sum(1 for x in range(len(seq)) for y in range(x+1,len(seq)) if seq[x]>seq[y])
s=1/np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,x in d.items(): v[m+2]=x
    return v
eg=[vec({0:1}),vec({2:s,-2:s})]
t2=[vec({2:s,-2:-s}),vec({1:s,-1:-s}),vec({1:s,-1:s})]
h=sum(6*np.outer(v,v.conj()) for v in eg)+sum(-4*np.outer(v,v.conj()) for v in t2)  # times Dq
def V(a,b,c_,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c_],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(Ck[(k,mc,ma)]*Ck[(k,mb,md)]*F[k] for k in (2,4))
def build(twoMs):
    dets=[d for d in itertools.combinations(range(10),5) if sum(1 if so[i][1] else -1 for i in d)==twoMs]
    idx={d:i for i,d in enumerate(dets)}
    N=len(dets)
    H1=np.zeros((N,N),complex)
    for d in dets:
        for p,a in enumerate(d):
            for b in range(10):
                if so[a][1]!=so[b][1]: continue
                if b!=a and b in d: continue
                hv=h[so[b][0]+2,so[a][0]+2]
                if abs(hv)<1e-12: continue
                l=list(d);l[p]=b
                H1[idx[tuple(sorted(l))],idx[d]]+=hv*sgn(l)
    # two-electron: parts by F2,F4 separately
    H2={2:np.zeros((N,N),complex),4:np.zeros((N,N),complex)}
    for d in dets:
        for p in range(5):
         for q in range(p+1,5):
          a,b=d[p],d[q]
          rest=[x for x in d if x not in(a,b)]
          for c_ in range(10):
           for e in range(c_+1,10):
            if c_ in rest or e in rest: continue
            if so[c_][1]+so[e][1]!=so[a][1]+so[b][1] or so[c_][0]+so[e][0]!=so[a][0]+so[b][0]: continue
            seq=[c_,e]+rest
            for k in (2,4):
                F={2:0,4:0};F[k]=1
                amp=V(c_,e,a,b,F)-V(c_,e,b,a,F)
                if abs(amp)<1e-12: continue
                H2[k][idx[tuple(sorted(seq))],idx[d]]+=amp*sgn(seq)
    return H1,H2
B1=build(1);B3=build(3)
def spec(Dq,B,Cc):
    F2=49*B+7*Cc;F4=63*Cc/5
    def ev(Bd):
        H=Dq*Bd[0]+F2*Bd[1][2]+F4*Bd[1][4]
        return np.linalg.eigvalsh((H+H.conj().T)/2)
    w1=list(ev(B1));
    for x in ev(B3):
        j=int(np.argmin([abs(x-y) for y in w1]));w1.pop(j)
    return np.array(sorted(w1))
if __name__=="__main__":
    w=spec(3000/10,800,3680);print(len(w));print(np.round(w-w[0])[:25])
E
python3 a.py
