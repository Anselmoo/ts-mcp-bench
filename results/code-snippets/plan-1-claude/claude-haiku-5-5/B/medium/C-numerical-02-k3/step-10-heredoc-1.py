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
states=[tuple(c) for c in itertools.combinations(range(N),7)]
sub=[s for s in states if sum(1 for x in s if x%2==0)==5]; idx={s:i for i,s in enumerate(sub)}
def hmat(Dq,B,C=None):
    if C is None: C=4*B
    F4=C*441/35; F2=(441*B+5*F4)/9
    F={0:0.,2:F2,4:F4}
    hcf=np.zeros((5,5))
    for a in [0,1,2]: hcf[a,a]=-4*Dq
    for a in [3,4]: hcf[a,a]=6*Dq
    V={}
    for k in [0,2,4]:
        for a,b,c,d in itertools.product(range(5),repeat=4):
            val=F[k]*Ak[k][a,b,c,d]
            if abs(val)<1e-14: continue
            for s1 in range(2):
                for s2 in range(2):
                    key=(sord(a,s1),sord(b,s2),sord(c,s1),sord(d,s2))
                    V[key]=V.get(key,0)+val
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
def levels(Dq,B):
    ev=np.linalg.eigvalsh(hmat(Dq,B))
    # group degenerate
    g=[]; 
    for e in ev:
        if g and abs(e-g[-1][0])<1e-6: g[-1][1]+=1
        else: g.append([e,1])
    return g
print(levels(1.0,0.0))
print(levels(1.0,0.1))
pickle.dump(None,open('ok.pkl','wb'))
# fit: bands relative to ground
def bands(p):
    Dq,B=p
    g=levels(Dq,B)
    e0=g[0][0]
    return [x[0]-e0 for x in g[1:]], g
res=[]
for Dq0,B0 in [(946,800),(900,1000),(1000,600)]:
    pass
