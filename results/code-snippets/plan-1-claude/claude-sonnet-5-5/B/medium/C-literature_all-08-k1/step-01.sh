cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def c(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    # c^k(m,m')=sqrt(4pi/(2k+1)) int Y2m* Ykq Y2m'
    return float(np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m,q,mp)*(-1)**m) if True else 0
# check sign convention: int Y*_{2m} = (-1)^m Y_{2,-m}
C={(k,m,mp):c(k,m,mp) for k in (2,4) for m in ms for mp in ms}
orbs=[(m,s) for s in (0,1) for m in ms]
def I(a,b,cc,d,F):  # <ab|1/r|cd>, a,c electron1; b,d electron 2
    if a[1]!=cc[1] or b[1]!=d[1]: return 0
    if a[0]+b[0]!=cc[0]+d[0]: return 0
    return sum(C[(k,a[0],cc[0])]*C[(k,d[0],b[0])]*F[k] for k in (2,4))
# h
P=np.zeros((5,5))
def idx(m): return m+2
v0=np.zeros(5);v0[2]=1
v2=np.zeros(5);v2[idx(2)]=v2[idx(-2)]=1/np.sqrt(2)
Peg=np.outer(v0,v0)+np.outer(v2,v2)
def run(Dq,B,Cc):
    F={2:49*B+7*Cc,4:63*Cc/5}
    h=6*Dq*Peg-4*Dq*(np.eye(5)-Peg)
    # ms=3/2 : 4 up 1 down? Ms=3/2 -> 4 up,1 down
    dets=[]
    for up in itertools.combinations(range(5),4):
        for dn in range(5):
            dets.append(tuple([(ms[i],0) for i in up]+[(ms[dn],1)]))
    n=len(dets);H=np.zeros((n,n))
    # build via second quantization with ordered orbital index
    oi={o:i for i,o in enumerate(orbs)}
    dset={tuple(sorted(oi[o] for o in d)):i for i,d in enumerate(dets)}
    keys=list(dset)
    def apply(ann,cre,state):
        s=list(state);sign=1
        for o in ann:
            if o not in s: return None,0
            p=s.index(o);sign*=(-1)**p;s.pop(p)
        for o in cre:
            if o in s: return None,0
            p=sum(1 for x in s if x<o);sign*=(-1)**p;s.insert(p,o)
        return tuple(s),sign
    # use dets as sorted tuples; operator a†_p a†_q a_s a_r
    V={}
    for a in orbs:
     for b in orbs:
      for cc in orbs:
       for d in orbs:
        val=I(a,b,cc,d,F)
        if val!=0: V[(oi[a],oi[b],oi[cc],oi[d])]=val
    for j,st in enumerate(keys):
        for (a,b,cc,d),val in V.items():
            # 1/2 sum a†_a a†_b a_d a_cc
            s1,g1=apply([d,cc],[b,a],st)
            if s1 is None: continue
            # apply order: annihilate d first then cc ; create b then a
            H[dset[s1],j]+=0.5*val*g1
        for m in ms:
         for mp in ms:
          for s in (0,1):
            hv=h[idx(m),idx(mp)]
            if hv==0: continue
            s1,g1=apply([oi[(mp,s)]],[oi[(m,s)]],st)
            if s1 is None: continue
            H[dset[s1],j]+=hv*g1
    e=np.linalg.eigvalsh((H+H.T)/2)
    return e
e=run(700,800,3000)
e-=e[0]
print(np.round(e[:20],0))
E
python3 /tmp/a.py