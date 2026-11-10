cat > /tmp/a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import fsolve
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    # <l m|C^k_{m-mp}|l mp>
    return float(gaunt(2,k,2,-m,m-mp,mp)*(-1)**m)*np.sqrt(5)*5/ np.sqrt(5)*1 if False else None
from sympy import sqrt as ssqrt, N
def c(k,m,mp):
    # c^k(lm,lm') = sqrt(4pi/(2k+1)) int Y*_lm Y_k,m-m' Y_lm'
    from sympy import pi
    return float(N(ssqrt(4*pi/(2*k+1))*gaunt(2,k,2,-m,m-mp,mp)*(-1)**m))
C={(k,m,mp):c(k,m,mp) for k in (0,2,4) for m in ms for mp in ms}
# orbitals index (m,s); s=0 up,1 down
orbs=[(m,s) for s in (0,1) for m in ms]
n=10
def build(Dq,B,Cc):
    F4=63*Cc/5; F2=(441*B+5*F4)/9
    F={0:0,2:F2,4:F4}
    h=np.zeros((5,5))
    h[2,2]+=6*Dq
    for a in (0,4): pass
    Pe=np.zeros((5,5)); Pe[2,2]=1
    v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2)
    Pe+=np.outer(v,v)
    h=6*Dq*Pe-4*Dq*(np.eye(5)-Pe)
    H1=np.zeros((n,n))
    for i,(m,s) in enumerate(orbs):
        for j,(mp,sp) in enumerate(orbs):
            if s==sp: H1[i,j]=h[m+2,mp+2]
    # <ab|cd> = delta spins (a,c),(b,d) * sum_k c^k(a,c) c^k(d,b) F^k
    V=np.zeros((n,n,n,n))
    for a,(ma,sa) in enumerate(orbs):
     for b,(mb,sb) in enumerate(orbs):
      for cc,(mc,sc) in enumerate(orbs):
       for d,(md,sd) in enumerate(orbs):
        if sa==sc and sb==sd and ma+mb==mc+md:
          V[a,b,cc,d]=sum(C[(k,ma,mc)]*C[(k,md,mb)]*F[k] for k in (2,4))
    return H1,V
def ham(Dq,B,Cc):
    H1,V=build(Dq,B,Cc)
    dets=[d for d in itertools.combinations(range(n),5) if sum(1 for o in d if o<5)==4]
    idx={d:i for i,d in enumerate(dets)}
    N_=len(dets); H=np.zeros((N_,N_))
    def apply(ops,det):
        # ops list of (type,orb) applied right to left; return sign,newdet
        occ=list(det); sign=1
        for t,o in reversed(ops):
            if t=='a':
                if o not in occ: return 0,None
                p=occ.index(o); sign*=(-1)**p; occ.pop(p)
            else:
                if o in occ: return 0,None
                p=sum(1 for x in occ if x<o); sign*=(-1)**p; occ.insert(p,o)
        return sign,tuple(occ)
    for det in dets:
        j=idx[det]
        for a in range(n):
            for b in range(n):
                if H1[a,b]!=0:
                    s,nd=apply([('c',a),('a',b)],det)
                    if s: H[idx[nd],j]+=s*H1[a,b]
        for a in range(n):
         for b in range(n):
          for cc in range(n):
           for d in range(n):
            x=V[a,b,cc,d]
            if x!=0:
              s,nd=apply([('c',a),('c',b),('a',d),('a',cc)],det)
              if s: H[idx[nd],j]+=0.5*s*x
    return H
def levels(Dq,B,Cc):
    w=np.linalg.eigvalsh(ham(Dq,B,Cc)); w=w-w[0]
    u=[]
    for x in w:
        if not u or abs(x-u[-1][0])>1: u.append([x,1])
        else: u[-1][1]+=1
    return u
if __name__=="__main__":
    print(levels(800,860,3200)[:8])
E
python3 /tmp/a.py