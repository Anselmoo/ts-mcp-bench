cat > ts.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
_g={}
def G(ma,mc,k,q):
    if ma-mc!=q: return 0.0
    key=(ma,mc,k,q)
    if key not in _g:
        _g[key]=float((-1)**(l-ma)*(2*l+1)*wigner_3j(l,k,l,-ma,q,mc)*wigner_3j(l,k,l,0,0,0))
    return _g[key]
def Vint(a,b,c,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd: return 0.0
    tot=0.0
    for k in (0,2,4):
        s=sum((-1)**q*G(ma,mc,k,q)*G(mb,md,k,-q) for q in range(-k,k+1))
        tot+=F[k]*s
    return tot
idx={m:i for i,m in enumerate(range(-2,3))}
PEG=np.zeros((5,5)); PEG[idx[0],idx[0]]=1
v=np.zeros(5); v[idx[2]]=v[idx[-2]]=1/np.sqrt(2); PEG+=np.outer(v,v)
def apply(ket,ops):
    occ=list(ket); sign=1
    for typ,o in reversed(ops):
        if typ=='a':
            if o not in occ: return None
            p=occ.index(o); sign*=(-1)**p; occ.remove(o)
        else:
            if o in occ: return None
            p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.append(o); occ.sort()
    return sign,tuple(occ)
def Hmat(F,Dq,nel=3,Sz2=None):
    h1=np.zeros((10,10))
    for i,(mi,si) in enumerate(orbs):
        for j,(mj,sj) in enumerate(orbs):
            if si==sj:
                oi=mi+2; oj=mj+2
                h1[i,j]=-4*Dq*(oi==oj)+10*Dq*PEG[oi,oj]
    V={}
    for a,b,c,d in itertools.product(range(10),repeat=4):
        x=Vint(a,b,c,d,F)
        if abs(x)>1e-12: V[(a,b,c,d)]=x
    states=[]
    for occ in itertools.combinations(range(10),nel):
        sz=sum(1 if orbs[o][1]==0 else -1 for o in occ)
        if Sz2 is None or sz==Sz2: states.append(occ)
    n=len(states); H=np.zeros((n,n))
    for J,ket in enumerate(states):
        # one-body
        for i in range(10):
            for j in range(10):
                if abs(h1[i,j])<1e-14: continue
                r=apply(ket,[('a',j),('c',i)])
                if r is None: continue
                s,st=r
                if st in states: H[states.index(st),J]+=s*h1[i,j]
        for (a,b,c,d),x in V.items():
            r=apply(ket,[('a',c),('a',d),('c',b),('c',a)])
            if r is None: continue
            s,st=r
            if st in states: H[states.index(st),J]+=0.5*s*x
    return H,states
EOF
cat > test.py << 'EOF'
from ts import *
B,C=1.0,4.0
F={0:0.0,4:63*C/5}; F[2]=49*B+F[4]/9
H,st=Hmat(F,0.0,Sz2=3)
ev=np.linalg.eigvalsh(H); print("quartet free ion", np.round(ev-ev.min(),4))
H,st=Hmat(F,0.0,Sz2=1)
ev=np.linalg.eigvalsh(H); print("Sz=1/2 free ion", np.round(ev-ev.min(),4))
EOF
time python3 test.py