import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <2m1|C^k|2m2>
    return float(gaunt(2,k,2,-m1,m1-m2,m2)*(-1)**m1) if False else None
from sympy import Rational
from sympy.physics.quantum.cg import CG
def c(k,m1,m2):
    # <l m1|C^k_q|l m2>, q=m1-m2 ; = (-1)^m1 sqrt(5*5) 3j(2 -m1;k q;2 m2)
    from sympy.physics.wigner import wigner_3j
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
C={(k,a,b):c(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def ck_(k,a,b): return C[(k,a,b)]
# two-electron integrals <ab|1/r|cd> = sum_k F^k c^k(a,c) c^k(b,d)  (a->c electron1, b->d electron2)
def V(F):
    v=np.zeros((5,5,5,5))
    for i,a in enumerate(ms):
     for j,b in enumerate(ms):
      for k_,cc in enumerate(ms):
       for l,d in enumerate(ms):
        if a+b!=cc+d: continue
        v[i,j,k_,l]=sum(F[k]*ck_(k,a,cc)*ck_(k,d,b) for k in (0,2,4))
    return v
# spin orbitals: (m,s)
so=[(i,s) for i in range(5) for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(so[x][1] for x in d)==1]  # 2 down? Ms=1/2 -> 3up2down
print(len(dets))
idx={d:i for i,d in enumerate(dets)}
# one-body: crystal field in real d basis; use complex basis: Oh potential Dq*(...) 
# V_oh matrix elements: 21Dq/... use: <m|V|m'>: diag: m=±2:Dq, ±1:-4Dq, 0:6Dq; off <2|V|-2>=5Dq
h=np.zeros((5,5))
for m,vv in zip(ms,[1,-4,6,-4,1]): h[m+2,m+2]=vv
h[0,4]=h[4,0]=5
def build(Dq,B,Cc):
    F4=B*0  # Racah: B=F2-5F4, C=... use F2=49F4+... 
    # F2=7(... ) : A=F0-49F4, B=F2/49-5F4/441, C=35F4/441
    F4=Cc*441/35*0+0
    f4=Cc*441/35/1.0  # wrong placeholder
    return None
def Fs(B,Cc):
    # C=35F4/441 (F in Condon-Shortley F^k units -> use F4 = 441C/35? ) with B=(F2-5F4)/49
    F4=441*Cc/35; F2=49*B+5*F4
    return [0,F2,F4]
# check: with F^k=Racah F^k convention c^k as above? use F_k Slater: E uses F^k directly with c^k c^k
def H(Dq,B,Cc):
    F=Fs(B,Cc); v=V(F)
    Hm=np.zeros((len(dets),len(dets)))
    for I,d in enumerate(dets):
        # one body
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                hv=Dq*h[so[q][0],so[p][0]]
                if hv==0: continue
                if q!=p and q in d: continue
                nd=[x for x in d if x!=p]+[q] if q!=p else list(d)
                # sign
                sign=1
                l=list(d); pos=l.index(p); l[pos]=q
                # sort with parity
                perm=sorted(range(5),key=lambda i:l[i]); 
                par=np.linalg.det(np.eye(5)[perm]); nd=tuple(sorted(l))
                Hm[idx[nd],I]+=hv*par
        # two-body: 1/2 sum <pq|rs> a+p a+q a_s a_r
        for r in d:
          for s in d:
            if r==s: continue
            for p in range(10):
              for q in range(10):
                if p==q: continue
                if so[p][1]!=so[r][1] or so[q][1]!=so[s][1]: continue
                val=v[so[p][0],so[q][0],so[r][0],so[s][0]]
                if val==0: continue
                l=list(d)
                # apply a_s a_r: remove r then s with signs
                def rem(l,x):
                    i=l.index(x); return (-1)**i, l[:i]+l[i+1:]
                def add(l,x):
                    if x in l: return 0,l
                    l2=[x]+l; return 1,l2
                s1,l1=rem(l,r); s2,l2=rem(l1,s)
                # a_s a_r |d> : first r then s
                a1,l3=add(l2,q); 
                if a1==0: continue
                a2,l4=add(l3,p)
                if a2==0: continue
                # sort sign: list l4 order -> sorted
                perm=sorted(range(5),key=lambda i:l4[i]); par=np.linalg.det(np.eye(5)[perm])
                Hm[idx[tuple(sorted(l4))],I]+=0.5*val*s1*s2*par
    return Hm
def lev(Dq,B,Cc):
    e=np.linalg.eigvalsh(H(Dq,B,Cc)); e=np.round(e-e[0],3); return e
if __name__=="__main__":
    print(np.unique(np.round(lev(800,860,3850),0)))
