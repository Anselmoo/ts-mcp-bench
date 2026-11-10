
mkdir -p ~/w 2>/dev/null; cd ~/w 2>/dev/null || cd $TMPDIR; pwd
cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
Ck={(k,a,b):c(k,a,b) for k in (2,4) for a in ms for b in ms}
so=[(i,s) for i in range(5) for s in (0,1)]
dets=[d for d in itertools.combinations(range(10),5) if sum(so[x][1] for x in d)==2]
idx={d:i for i,d in enumerate(dets)}
h=np.zeros((5,5))
for m,vv in zip(ms,[1,-4,6,-4,1]): h[m+2,m+2]=vv
h[0,4]=h[4,0]=5
def sortsign(l):
    l=list(l);s=1
    for i in range(len(l)):
        for j in range(len(l)-1-i):
            if l[j]>l[j+1]: l[j],l[j+1]=l[j+1],l[j]; s=-s
    return s,tuple(l)
def rem(l,x):
    i=l.index(x); return (-1)**i,l[:i]+l[i+1:]
def add(l,x):
    if x in l: return 0,l
    return 1,[x]+l
# precompute with unit params
def two(F2,F4):
    v=np.zeros((5,5,5,5))
    for i,a in enumerate(ms):
     for j,b in enumerate(ms):
      for k,cc in enumerate(ms):
       for l,d in enumerate(ms):
        if a+b==cc+d:
          v[i,j,k,l]=F2*Ck[(2,a,cc)]*Ck[(2,d,b)]+F4*Ck[(4,a,cc)]*Ck[(4,d,b)]
    return v
def mats():
    n=len(dets);H1=np.zeros((n,n));parts={}
    for I,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                hv=h[so[q][0],so[p][0]]
                if hv==0 or (q!=p and q in d): continue
                l=list(d);l[l.index(p)]=q
                s,nd=sortsign(l);H1[idx[nd],I]+=hv*s
    return H1
H1=mats()
def twobody(v):
    n=len(dets);H2=np.zeros((n,n))
    for I,d in enumerate(dets):
      for r in d:
        for s in d:
          if r==s: continue
          for p in range(10):
            for q in range(10):
              if p==q or so[p][1]!=so[r][1] or so[q][1]!=so[s][1]: continue
              val=v[so[p][0],so[q][0],so[r][0],so[s][0]]
              if val==0: continue
              s1,l1=rem(list(d),r);s2,l2=rem(l1,s)
              a1,l3=add(l2,q)
              if a1==0: continue
              a2,l4=add(l3,p)
              if a2==0: continue
              s3,nd=sortsign(l4)
              H2[idx[nd],I]+=0.5*val*s1*s2*s3
    return H2
HB=twobody(two(49,0)) ; 
HC=twobody(two(7,441/35.))
HB=twobody(two(49,0))  # B coeff
def lev(Dq,B,C):
    Hm=Dq*H1+B*HB+C*HC
    e=np.linalg.eigvalsh(Hm);return e-e[0]
if __name__=="__main__":
    e=np.unique(np.round(lev(800,860,3850),0));print(e[:30])
    print(10*860+5*3850)
E
python3 a.py