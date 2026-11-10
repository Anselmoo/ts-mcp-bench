
cd $(mktemp -d) && cat << 'EOF' > d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=range(-2,3)
orbs=[(m,s) for m in ms for s in (1,-1)]
def ck(k,m1,m2): # c^k(l m1, l m2)
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def U(Fk):
    n=10;V=np.zeros((n,n,n,n))
    for i,(m1,s1) in enumerate(orbs):
     for j,(m2,s2) in enumerate(orbs):
      for k_,(m3,s3) in enumerate(orbs):
       for l,(m4,s4) in enumerate(orbs):
        if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
        V[i,j,k_,l]=sum(Fk[k]*CK[(k,m1,m3)]*CK[(k,m4,m2)] for k in (2,4))
    return V
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def H(Dq,B,C):
    Fk={2:49*B+7*C,4:441*C/35}
    V=U(Fk)
    h=np.zeros((5,5))
    for i,m in enumerate(ms):
        h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    h[0,4]=h[4,0]=5*Dq
    h1=np.zeros((10,10))
    for i,(m1,s1) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            if s1==s2: h1[i,j]=h[m1+2,m2+2]
    N=len(dets);M=np.zeros((N,N))
    def apply(ops,det):
        # returns list of (sign,det) ; ops list of ('c'/'a',orb) applied right to left
        st=list(det);sign=1
        for t,o in reversed(ops):
            if t=='a':
                if o not in st: return None
                p=st.index(o);sign*=(-1)**p;st.pop(p)
            else:
                if o in st: return None
                st.insert(0,o)
                # sort
                p=sorted(st).index(o);sign*=(-1)**p;st=sorted(st)
        return sign,tuple(st)
    for J,d in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if h1[p,q]!=0:
                    r=apply([('c',p),('a',q)],d)
                    if r: M[idx[r[1]],J]+=r[0]*h1[p,q]
        for p in range(10):
         for q in range(10):
          for r_ in range(10):
           for s in range(10):
            v=V[p,q,r_,s]
            if v==0: continue
            r=apply([('c',p),('c',q),('a',s),('a',r_)],d)
            if r: M[idx[r[1]],J]+=0.5*r[0]*v
    return M
# S^2 to classify
def levels(Dq,B,C):
    e=np.linalg.eigvalsh(H(Dq,B,C)); e=e-e[0]
    # unique with degeneracies
    out=[];
    for x in e:
        if out and abs(x-out[-1][0])<1e-3: out[-1][1]+=1
        else: out.append([x,1])
    return out
for l in levels(1917,824,3300)[:8]: print(l)
EOF
python3 d3.py
