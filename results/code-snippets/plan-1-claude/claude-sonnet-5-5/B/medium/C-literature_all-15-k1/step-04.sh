cat > /tmp/d7.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2; ms=range(-2,3)
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*5*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m1,q,m2))
CK={k:{(a,b):ck(k,a,b) for a in ms for b in ms} for k in (0,2,4)}
so=[(m,s) for m in ms for s in (0,1)]
n=10
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(n),7)]
idx={d:i for i,d in enumerate(dets)}
def apply(op,d):  # op list of (type,i) applied right to left; return sign,d
    sign=1
    for t,i in reversed(op):
        occ=(d>>i)&1
        if t=='a':
            if not occ: return 0,0
        else:
            if occ: return 0,0
        sign*= (-1)**bin(d&((1<<i)-1)).count('1')
        d^=1<<i
    return sign,d
def build(Dq,B,C):
    F2=B+C/7; F4=C/35
    Fk={0:0,2:49*F2,4:441*F4}
    h=np.zeros((n,n))
    v={2:Dq,1:-4*Dq,0:6*Dq,-1:-4*Dq,-2:Dq}
    for s in (0,1):
        for m in ms: h[so.index((m,s)),so.index((m,s))]=v[m]
        h[so.index((2,s)),so.index((-2,s))]=5*Dq; h[so.index((-2,s)),so.index((2,s))]=5*Dq
    # g[a,b,c,d]=<ab|g|cd>
    g=np.zeros((n,n,n,n))
    for a,(m1,s1) in enumerate(so):
      for b,(m2,s2) in enumerate(so):
        for c,(m3,s3) in enumerate(so):
          for d_,(m4,s4) in enumerate(so):
            if s1==s3 and s2==s4 and m1+m2==m3+m4:
              g[a,b,c,d_]=sum(Fk[k]*CK[k][(m1,m3)]*CK[k][(m4,m2)] for k in (2,4))
    H=np.zeros((len(dets),len(dets)))
    for j,d in enumerate(dets):
        for i1 in range(n):
          for i2 in range(n):
            if h[i1,i2]!=0:
              s,d2=apply([('c',i1),('a',i2)],d)
              if s: H[idx[d2],j]+=s*h[i1,i2]
        for a in range(n):
         for b in range(n):
          for c in range(n):
           for e in range(n):
            if g[a,b,c,e]!=0:
              s,d2=apply([('c',a),('c',b),('a',e),('a',c)],d)
              if s: H[idx[d2],j]+=0.5*s*g[a,b,c,e]
    return H
# spin
def Sz2():
    S=np.zeros((len(dets),)*2)
    return S
def levels(Dq,B,C):
    H=build(Dq,B,C)
    w,V=np.linalg.eigh(H)
    # Sz restrict: use Sz=3/2 sector for quartets: det with up-n minus down-n
    return w,V
if __name__=="__main__":
    import sys
    # Sz sectors
    sz=np.array([ (sum((d>>i)&1 for i in range(0,n,2))-sum((d>>i)&1 for i in range(1,n,2)))/2 for d in dets])
    def lv(Dq,B,C):
        H=build(Dq,B,C)
        out={}
        for S2,name in ((1.5,'q'),(0.5,'d')):
            sel=np.where(sz==S2)[0]
            w=np.linalg.eigvalsh(H[np.ix_(sel,sel)])
            out[name]=w
        return out
    def groups(w,tol=1e-3):
        g=[];
        for x in w:
            if g and abs(x-g[-1][0])<tol: g[-1][1]+=1
            else: g.append([x,1])
        return g
    o=lv(900,800,3500)
    for name in 'qd':
        g=groups(o[name]); e0=groups(o['q'])[0][0]
        print(name,[(round(x-e0),c) for x,c in g])
E
python3 /tmp/d7.py