
cd $TMPDIR && cat > d3.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def cf(Dq):
    h=np.zeros((5,5)); d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): h[i,i]=d[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    return h
def ann(j,det):
    if j not in det: return None
    p=det.index(j); return det[:p]+det[p+1:], (-1)**p
def cre(i,det):
    if i in det: return None
    new=sorted(det+(i,)); p=new.index(i); return tuple(new),(-1)**p
def op(i,j,det):
    r=ann(j,det)
    if not r: return None
    s=cre(i,r[0])
    if not s: return None
    return s[0],r[1]*s[1]
N=len(dets)
Mh=np.zeros((N,N)); Mk={0:np.zeros((N,N)),2:np.zeros((N,N)),4:np.zeros((N,N))}
h=cf(1.0)
for J,D in enumerate(dets):
    for a in range(10):
        for b in range(10):
            if orbs[a][1]!=orbs[b][1]: continue
            v=h[orbs[a][0]+2,orbs[b][0]+2]
            if v==0: continue
            r=op(a,b,D)
            if r: Mh[idx[r[0]],J]+=v*r[1]
    for cc in D:
        for d in D:
            if cc==d: continue
            r1=ann(cc,D); r2=ann(d,r1[0])
            for a in range(10):
                for b in range(10):
                    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[cc],orbs[d]
                    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
                    r3=cre(b,r2[0])
                    if not r3: continue
                    r4=cre(a,r3[0])
                    if not r4: continue
                    s=0.5*r1[1]*r2[1]*r3[1]*r4[1]
                    for k in (0,2,4): Mk[k][idx[r4[0]],J]+=s*c(k,ma,mc)*c(k,md,mb)
def levels(Dq,B,C):
    M=Dq*Mh+(49*B+7*C)*Mk[2]+(441*C/35)*Mk[4]
    e=np.linalg.eigvalsh(M); e=e-e[0]
    out=[]
    for x in e:
        if not out or abs(x-out[-1][0])>0.5: out.append([x,1])
        else: out[-1][1]+=1
    return out
Dq,B=1417,878
def E2(C):
    return [x for x,n in levels(Dq,B,C) if n==4 and x>1][0]
Cs=brentq(lambda C:E2(C)-18540,2*B,8*B,xtol=0.01)
print(Cs,Cs/B)
for x,n in levels(Dq,B,Cs)[:9]: print(round(x,1),n)
EOF
python3 d3.py