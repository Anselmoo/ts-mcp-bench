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
Vk={}
for k in [0,2,4]:
    for a,b,c,d in itertools.product(range(5),repeat=4):
        val=Ak[k][a,b,c,d]
        if abs(val)<1e-14: continue
        for s1 in range(2):
            for s2 in range(2):
                key=(sord(a,s1),sord(b,s2),sord(c,s1),sord(d,s2))
                Vk.setdefault(key,{}); Vk[key][k]=Vk[key].get(k,0)+val
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
def hmat(Dq,B,C):
    F4=C*441/35; F2=(441*B+5*F4)/9
    F={0:0.,2:F2,4:F4}
    hcf=np.zeros((5,5))
    for a in [0,1,2]: hcf[a,a]=-4*Dq
    for a in [3,4]: hcf[a,a]=6*Dq
    H=np.zeros((len(sub),)*2)
    for it,si,sg,kd in ops2: H[it,si]+=sg*sum(F[k]*v for k,v in kd.items())
    for it,si,sg,(a,c) in ops1: H[it,si]+=sg*hcf[a,c]
    return H
def excit(p):
    ev=np.sort(np.linalg.eigvalsh(hmat(*p)))
    g=[]
    for e in ev:
        if g and abs(e-g[-1][0])<1e-6: g[-1][1]+=1
        else: g.append([e,1])
    return [x[0]-g[0][0] for x in g[1:]]
obs=np.array([9460,20160,21160.])
r=least_squares(lambda p: excit(p)[:3]-obs,[1070,860,3450],x_scale=[100,100,100])
print('Dq,B,C fit:',r.x, r.fun)
print('C/B=',r.x[2]/r.x[1])
