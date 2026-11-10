
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=1.0;C=3473/800
F2=49*B+7*C;F4=63*C/5
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
def ck(k,m1,m2): # <l m1|C^k|l m2>
    from sympy.physics.wigner import wigner_3j
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2)) 
Fk={0:0,2:F2/49,4:F4/441}
def g(a,b,c,d):
    # <ab|1/r12|cd> = sum_k F^k c^k(a,c)c^k(d,b) with m conservation
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=a,b,c,d
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    t=0
    for k in (0,2,4):
        t+=Fk[k]*ck(k,m1,m3)*ck(k,m4,m2)
    return t
import functools
g=functools.lru_cache(None)(g)
def run(Dq):
    h=np.zeros((10,10))
    V=np.zeros((5,5)); idx={m:i for i,m in enumerate(ms)}
    for m in(-1,1):V[idx[m],idx[m]]=-4*Dq
    V[idx[0],idx[0]]=6*Dq
    V[idx[2],idx[2]]=V[idx[-2],idx[-2]]=Dq
    V[idx[2],idx[-2]]=V[idx[-2],idx[2]]=5*Dq
    for i,(m,s) in enumerate(orbs):
        for j,(n,t) in enumerate(orbs):
            if s==t:h[i,j]=V[idx[m],idx[n]]
    return h
dets=[d for d in itertools.combinations(range(10),5) if sum(orbs[i][1] for i in d)==0.5]
di={d:i for i,d in enumerate(dets)}
def H(Dq):
    h=run(Dq);N=len(dets);M=np.zeros((N,N))
    # build via second quantization
    def apply(ops,d):
        # ops list of (create/annih,index) applied right to left
        d=list(d);sign=1
        for typ,i in reversed(ops):
            if typ=='a':
                if i not in d:return None,0
                p=d.index(i);sign*=(-1)**p;d.pop(p)
            else:
                if i in d:return None,0
                p=sum(1 for x in d if x<i);sign*=(-1)**p;d.insert(p,i)
        return tuple(d),sign
    for d in dets:
        a=di[d]
        for i in range(10):
            for j in range(10):
                if h[i,j]!=0:
                    r,s=apply([('c',i),('a',j)],d)
                    if r is not None:M[di[r],a]+=h[i,j]*s
        for p in range(10):
         for q in range(10):
          for r_ in range(10):
           for s_ in range(10):
            v=g(orbs[p],orbs[q],orbs[r_],orbs[s_])
            if v==0:continue
            # 1/2 sum <pq|rs> c_p c_q a_s a_r
            r,s=apply([('c',p),('c',q),('a',s_),('a',r_)],d)
            if r is not None:M[di[r],a]+=0.5*v*s
    return M
for x in (1.45,2.55,3.25):
    w=np.linalg.eigvalsh(H(x));w=np.round(w-w[0],3)
    u=[]
    for e in w:
        if not u or abs(e-u[-1][0])>1e-2:u.append([e,1])
        else:u[-1][1]+=1
    print(x,u[:9])
E
python3 /tmp/a.py
