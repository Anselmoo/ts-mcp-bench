
cd /tmp/tsbench-run-zqezmkn7 && timeout 500 python3 - << 'EOF'
import numpy as np, itertools, pickle
from scipy.optimize import least_squares
Ak=pickle.load(open('Ak.pkl','rb'))
N=10
def sord(o,s): return 2*o+s
def apply(occ, ops):
    s=list(occ); sign=1
    for typ,i in reversed(ops):
        if typ=='a':
            if i not in s: return 0,None
            p=s.index(i); sign*=(-1)**p; s.pop(p)
        else:
            if i in s: return 0,None
            p=sum(1 for x in s if x<i); sign*=(-1)**p; s.insert(p,i)
    return sign,tuple(s)
nel=7
states=[tuple(c) for c in itertools.combinations(range(N),nel)]
sel=[i for i,s in enumerate(states) if sum(1 for x in s if x%2==0)==5]
sub=[states[i] for i in sel]; idx={s:i for i,s in enumerate(sub)}
# precompute two-body operator as list of (a,b,c,d,val) grouped in spatial form
def pieces(F):
    terms=[]
    for k in [0,2,4]:
        for a,b,c,d in itertools.product(range(5),repeat=4):
            val=F[k]*Ak[k][a,b,c,d]
            if abs(val)>1e-14: terms.append((a,b,c,d,val))
    return terms
def hmat(Dq,B,C=None):
    if C is None: C=4*B
    F4=C*441/35; F2=(441*B+5*F4)/9
    F={0:0.,2:F2,4:F4}
    hcf=np.zeros((5,5))
    for a in [0,1,2]: hcf[a,a]=-4*Dq
    for a in [3,4]: hcf[a,a]=6*Dq
    V={}
    for a,b,c,d,val in pieces(F):
        for s1 in range(2):
            for s2 in range(2):
                V[(sord(a,s1),sord(b,s2),sord(c,s1),sord(d,s2))]=V.get((sord(a,s1),sord(b,s2),sord(c,s1),sord(d,s2)),0)+val
    H=np.zeros((len(sub),)*2)
    for si,s in enumerate(sub):
        for a in range(5):
            for c in range(5):
                if hcf[a,c]!=0:
                    for sp in range(2):
                        sg,t=apply(s,[('c',sord(a,sp)),('a',sord(c,sp))])
                        if t is not None and t in idx: H[idx[t],si]+=sg*hcf[a,c]
        for (a,b,c,d),v in V.items():
            sg,t=apply(s,[('c',a),('c',b),('a',d),('a',c)])
            if t is not None and t in idx: H[idx[t],si]+=0.5*sg*v
    return H
H=hmat(0.0,1.0)
print('free-ion d7 quartet (B=1, C=4):',np.round(np.linalg.eigvalsh(H),3))
EOF