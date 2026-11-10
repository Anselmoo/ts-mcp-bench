import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=706.,2734.
F={0:0.,2:49*B+7*C,4:63*C/5}
ml=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = <l m1|C^k_{m1-m2}|l m2>
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(25)*np.sqrt(4*np.pi/(2*k+1))*0+0) if False else \
      float((-1)**m1*5*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,q,m2))
def U(a,b,c,d): # <ab|1/r|cd> spatial m
    if a+b!=c+d: return 0.
    return sum(F[k]*ck(k,a,c)*ck(k,d,b) for k in (0,2,4))
so=[(m,s) for s in (1,-1) for m in ml]
def V(Dq):
    v=np.zeros((5,5)); i={m:j for j,m in enumerate(ml)}
    v[i[0],i[0]]=6*Dq; v[i[1],i[1]]=v[i[-1],i[-1]]=-4*Dq
    v[i[2],i[2]]=v[i[-2],i[-2]]=Dq; v[i[2],i[-2]]=v[i[-2],i[2]]=5*Dq
    return v
def H(Ms2,Dq):
    dets=[d for d in itertools.combinations(range(10),4) if sum(so[x][1] for x in d)==Ms2]
    idx={d:i for i,d in enumerate(dets)}; n=len(dets); h=np.zeros((n,n))
    v=V(Dq)
    def g(p,q,r,s):
        (a,sa),(b,sb),(c,sc),(d,sd)=so[p],so[q],so[r],so[s]
        return U(a,b,c,d)*(sa==sc)*(sb==sd)
    # second quantization: H = sum h_pq a+p aq + 1/2 sum <pq|rs> a+p a+q a_s a_r
    def apply(ops,det):
        det=list(det); sign=1
        for op,o in reversed(ops):
            if op=='a':
                if o not in det: return None,0
                k=det.index(o); sign*=(-1)**k; det.pop(k)
            else:
                if o in det: return None,0
                det.insert(0,o); # then sort
                k=sorted(det).index(o); det=sorted(det); sign*=(-1)**k
        return tuple(det),sign
    for d in dets:
        j=idx[d]
        for p in range(10):
            for q in d:
                if so[p][1]!=so[q][1]: continue
                val=v[ml.index(so[p][0]),ml.index(so[q][0])]
                if val==0: continue
                nd,s=apply([('c',p),('a',q)],d)
                if nd: h[idx[nd],j]+=s*val
        for r,s_ in itertools.permutations(d,2):
            for p in range(10):
                for q in range(10):
                    if p==q: continue
                    val=g(p,q,r,s_)
                    if val==0: continue
                    nd,sg=apply([('c',p),('c',q),('a',s_),('a',r)],d)
                    if nd: h[idx[nd],j]+=0.5*sg*val
    return h
def f(Dq):
    e2=np.linalg.eigvalsh(H(4,Dq))[0]; e1=np.linalg.eigvalsh(H(2,Dq))[0]
    return e1-e2
print(f(0),f(1000),f(3000))
r=brentq(f,1000,3000,xtol=1e-6); print(r)
print(np.linalg.eigvalsh(H(0,0))[:20])
