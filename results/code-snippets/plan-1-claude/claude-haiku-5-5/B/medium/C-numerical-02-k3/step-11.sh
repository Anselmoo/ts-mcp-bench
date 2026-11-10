
cd /tmp/tsbench-run-zqezmkn7 && timeout 550 python3 - << 'EOF'
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
# precompute operator action list (spin-orbital two-body terms) once for F-independent Ak pieces
Vk={}
for k in [0,2,4]:
    for a,b,c,d in itertools.product(range(5),repeat=4):
        val=Ak[k][a,b,c,d]
        if abs(val)<1e-14: continue
        for s1 in range(2):
            for s2 in range(2):
                key=(sord(a,s1),sord(b,s2),sord(c,s1),sord(d,s2))
                Vk.setdefault(key,{}); Vk[key][k]=Vk[key].get(k,0)+val
# action lists
ops2=[]
for (a,b,c,d),kd in Vk.items():
    for si,s in enumerate(sub):
        sg,t=apply(s,[('c',a),('c',b),('a',d),('a',c)])
        if t is not None and t in idx: ops2.append((idx[t],si,sg*0.5,kd))
ops1=[]
for a in range(5):
    for c in range(5):
        for sp in range(2):
            for si,s in enumerate(sub):
                sg,t=apply(s,[('c',sord(a,sp)),('a',sord(c,sp))])
                if t is not None and t in idx: ops1.append((idx[t],si,sg,(a,c)))
def hmat(Dq,B,C=None):
    if C is None: C=4*B
    F4=C*441/35; F2=(441*B+5*F4)/9
    F={0:0.,2:F2,4:F4}
    hcf=np.zeros((5,5))
    for a in [0,1,2]: hcf[a,a]=-4*Dq
    for a in [3,4]: hcf[a,a]=6*Dq
    H=np.zeros((len(sub),)*2)
    for it,si,sg,kd in ops2:
        H[it,si]+=sg*sum(F[k]*v for k,v in kd.items())
    for it,si,sg,(a,c) in ops1:
        H[it,si]+=sg*hcf[a,c]
    return H
def levels(Dq,B):
    ev=np.linalg.eigvalsh(hmat(Dq,B))
    g=[]
    for e in ev:
        if g and abs(e-g[-1][0])<1e-6: g[-1][1]+=1
        else: g.append([e,1])
    return g
obs=[9460,20160,21160]
def excit(p):
    g=levels(*p); e0=g[0][0]
    return [x[0]-e0 for x in g[1:]], [x[1] for x in g]
print(excit((946,800)))
best=None
for perm in itertools.permutations(range(3)):
    pass
# assume groups: sorted excited levels g1,g2,g3 ; try fit with ordering
def resid(p):
    ex,_=excit(p)
    return np.array(ex[:3])-np.array([9460,20160,21160])
for guess in [(946,800),(946,1000),(900,600),(1000,900)]:
    try:
        r=least_squares(resid,guess,x_scale=[100,100])
        print(guess, r.x, r.fun, excit(r.x))
    except Exception as e: print('err',e)
EOF