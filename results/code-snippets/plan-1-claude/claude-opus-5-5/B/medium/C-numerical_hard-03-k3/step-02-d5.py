import numpy as np, itertools, bisect
from sympy.physics.wigner import wigner_3j
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
CK={}
for k in (0,2,4):
  for a in range(-2,3):
    for c in range(-2,3):
      CK[k,a,c]=float((-1)**a*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-a,a-c,c))
def R(a,b,c,d,F):
    if a+b!=c+d: return 0
    return sum(CK[k,a,c]*CK[k,d,b]*F[k] for k in (0,2,4))
def Vcf(Dq):
    V=np.zeros((5,5)); V[2,2]=6*Dq
    V[1,1]=V[3,3]=-4*Dq; V[0,0]=V[4,4]=Dq; V[0,4]=V[4,0]=5*Dq
    return V
def build(ms2):
    dets=[d for d in itertools.combinations(range(10),5) if sum(1 if orbs[x][1]==0 else -1 for x in d)==ms2]
    return dets,{d:i for i,d in enumerate(dets)}
def H(Dq,B,C,ms2):
    dets,di=build(ms2)
    F={0:0,2:49*B+7*C,4:441*C/35}
    n=len(dets);Hm=np.zeros((n,n));V=Vcf(Dq)
    def g(a,b,c,dd):
        if orbs[a][1]!=orbs[c][1] or orbs[b][1]!=orbs[dd][1]: return 0
        return R(orbs[a][0],orbs[b][0],orbs[c][0],orbs[dd][0],F)
    for i,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if orbs[q][1]!=orbs[p][1]: continue
                v=V[orbs[q][0]+2,orbs[p][0]+2]
                if v==0 or (q!=p and q in d): continue
                lst=list(d);k=lst.index(p);sg=(-1)**k;lst.pop(k)
                k=bisect.bisect(lst,q);sg*=(-1)**k;lst.insert(k,q)
                Hm[di[tuple(lst)],i]+=sg*v
        for p,q in itertools.combinations(d,2):
            rest=[x for x in d if x not in (p,q)]
            for r in range(10):
                if r in rest: continue
                for s_ in range(r+1,10):
                    if s_ in rest: continue
                    val=g(r,s_,p,q)-g(r,s_,q,p)
                    if abs(val)<1e-12: continue
                    lst=list(d);sg=1
                    k=lst.index(q);sg*=(-1)**k;lst.pop(k)
                    k=lst.index(p);sg*=(-1)**k;lst.pop(k)
                    k=bisect.bisect(lst,s_);sg*=(-1)**k;lst.insert(k,s_)
                    k=bisect.bisect(lst,r);sg*=(-1)**k;lst.insert(k,r)
                    Hm[di[tuple(lst)],i]+=sg*val
    return Hm
def levels(Dq,B,C):
    e1=np.linalg.eigvalsh(H(Dq,B,C,1)); e3=np.linalg.eigvalsh(H(Dq,B,C,3)); e5=np.linalg.eigvalsh(H(Dq,B,C,5))
    def rnd(e): return np.round(e,4)
    from collections import Counter
    c1=Counter(rnd(e1));c3=Counter(rnd(e3))
    doub=[]
    for k,v in c1.items():
        nd=v-c3.get(k,0)
        doub+= [k]*nd
    return sorted(doub), sorted(e1)
if __name__=="__main__":
    # free-ion check: d5 terms
    d,a=levels(0,1000,4000)
    print(sorted(set(np.round(a,1))))
