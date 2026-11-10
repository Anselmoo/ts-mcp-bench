
cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B=922.;C=4156.
F4=C/35;F2=B+5*F4
ms=range(-2,3)
def ck(k,m1,m2): # <m1|C^k_q|m2> , q=m1-m2
    q=m1-m2
    return float((-1)**m1*np.sqrt(5*5)*0+ 0) 
from sympy import Rational, sqrt as ssqrt
def c(k,m1,m2):
    # <2 m1|C^k_{m1-m2}|2 m2>=(-1)^m1 *5*3j(2 -m1;k q;2 m2)*3j(2 0;k 0;2 0)
    from sympy.physics.wigner import wigner_3j
    q=m1-m2
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,q,m2)*wigner_3j(2,k,2,0,0,0))
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
idx={o:i for i,o in enumerate(orbs)}
# two-electron <m1 m2|g|m3 m4> direct form: sum_k a_k c(k,m1,m3)c(k,m2,m4)... with m1+m2=m3+m4
Fk={0:0,2:F2,4:F4}
def g(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0
    return sum(Fk[k]*c(k,m1,m3)*c(k,m4,m2)*(-1)**(m1-m3) *1 for k in (2,4))
# check sign convention: <ab|1/r|cd>=sum ck(a,c) ck(d,b) F^k with c^k(l m,l m')
def gg(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0
    return sum(Fk[k]*c(k,m1,m3)*c(k,m4,m2) for k in (2,4))
G={}
for a in itertools.product(ms,repeat=4): G[a]=gg(*a)
def H(Dq,Ms2):
    N=3 # d7 -> use 7 electrons
    n=7
    dets=[d for d in itertools.combinations(range(10),n) if sum(orbs[i][1] for i in d)==Ms2/2]
    pos={d:i for i,d in enumerate(dets)}
    h=np.zeros((10,10))
    for (m,s) in orbs:
        i=idx[(m,s)]
        d={2:1,-2:1,1:-4,-1:-4,0:6}[m]*Dq
        h[i,i]=d
        if abs(m)==2: h[i,idx[(-m,s)]]=5*Dq
    # build second quantized
    V={}
    for a in orbs:
     for b in orbs:
      for cc in orbs:
       for d in orbs:
        if a[1]==cc[1] and b[1]==d[1]:
         v=G[(a[0],b[0],cc[0],d[0])]
         if v: V[(idx[a],idx[b],idx[cc],idx[d])]=v
    M=np.zeros((len(dets),len(dets)))
    def apply(ops,det):
        s=list(det);sign=1
        for (o,cr) in ops:
            if cr:
                if o in s: return None,0
                p=sum(1 for x in s if x<o); sign*=(-1)**p; s.append(o); s.sort()
            else:
                if o not in s: return None,0
                p=sum(1 for x in s if x<o); sign*=(-1)**p; s.remove(o)
        return tuple(s),sign
    for d in dets:
        j=pos[d]
        for p in range(10):
            for q in range(10):
                if h[p,q]:
                    r,sg=apply([(q,0),(p,1)],d)
                    if r is not None: M[pos[r],j]+=sg*h[p,q]
        for (a,b,cc,dd),v in V.items():
            # 1/2 sum a+ b+ d c  <ab|cd>
            r,sg=apply([(cc,0),(dd,0),(b,1),(a,1)],d)
            if r is not None: M[pos[r],j]+=0.5*sg*v
    return np.linalg.eigvalsh((M+M.T)/2)
def f(Dq):
    q=H(Dq,3)[0]
    e=H(Dq,1)
    dq=[x for x in e if np.min(abs(H(Dq,3)-x))>1e-6]
    return dq[0]-q
for D in (500,1000,1500,2000): print(D,f(D))
print(brentq(f,500,2500,xtol=0.1))
E
python3 /tmp/a.py
