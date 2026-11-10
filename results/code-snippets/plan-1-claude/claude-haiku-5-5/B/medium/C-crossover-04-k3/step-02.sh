
mkdir -p ~/d7 && cd ~/d7 && cat << 'EOF' > d7.py
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import brentq
ms=[-2,-1,0,1,2]
so=[(m,s) for s in (1,-1) for m in ms]
N=len(so)
nth,nph=40,80
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.full(nph,2*np.pi/nph))
Yd={m:sph_harm(m,2,PH,TH) for m in ms}
def gaunt_k(k,m1,m3,m2,m4):
    tot=0
    for q in range(-k,k+1):
        Ykq=sph_harm(q,k,PH,TH)
        a=np.sum(W*np.conj(Yd[m1])*np.conj(Ykq)*Yd[m3])
        b=np.sum(W*np.conj(Yd[m2])*Ykq*Yd[m4])
        tot+=a*b
    return tot*4*np.pi/(2*k+1)
# precompute angular coefficient tables
A={}
for k in (2,4):
  for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    if m1+m2==m3+m4:
        A[(k,m1,m2,m3,m4)]=gaunt_k(k,m1,m3,m2,m4)
def apply_ops(ops,occ):
    # ops: list of (type,index) applied right-to-left as written; here apply in order given (rightmost first)
    occ=list(occ); sign=1
    for typ,i in ops:
        if typ=='a':   # annihilate
            if i not in occ: return None,None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None,None
            q=sum(1 for x in occ if x<i); sign*=(-1)**q; occ.insert(q,i)
    return sign,tuple(occ)
def build_H(Dq,B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    F={2:F2,4:F4}
    idx={m:i for i,m in enumerate(ms)}
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[idx[m]]=c
        return v
    s2=np.sqrt(2)
    eg=[vec({0:1}),vec({2:1/s2,-2:1/s2})]
    t2=[vec({2:1/(1j*s2),-2:-1/(1j*s2)}),vec({1:1/s2,-1:1/s2}),vec({1:1/(1j*s2),-1:-1/(1j*s2)})]
    h=np.zeros((5,5),complex)
    for e in eg: h+=6*Dq*np.outer(e,e.conj())
    for t in t2: h+=-4*Dq*np.outer(t,t.conj())
    # two-electron integrals in spin-orbital basis
    def V(a,b,c,d):  # <ab|1/r|cd>, a..d spin-orbital indices
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
        if sa!=sc or sb!=sd: return 0
        if ma+mb!=mc+md: return 0
        return sum(F[k]*A[(k,ma,mb,mc,md)] for k in (2,4))
    states=list(itertools.combinations(range(N),7))
    sidx={s:i for i,s in enumerate(states)}
    D=len(states)
    H=np.zeros((D,D),complex)
    spo=lambda i: (ms.index(so[i][0]), so[i][1])
    for st in states:
        j=sidx[st]
        for a in range(N):
          for b in range(N):
            ia,sa=spo(a); ib,sb=spo(b)
            if sa!=sb or h[ia,ib]==0: continue
            sg,new=apply_ops([('a',b),('c',a)],st)
            if new is None: continue
            H[sidx[new],j]+=sg*h[ia,ib]
        # two-body: 1/2 sum V_abcd c+_a c+_b c_d c_c
        for a in range(N):
          for b in range(N):
            if a==b: continue
            for c in range(N):
              for d in range(N):
                if c==d: continue
                v=V(a,b,c,d)
                if v==0: continue
                sg,new=apply_ops([('a',c),('a',d),('c',b),('c',a)],st)
                if new is None: continue
                H[sidx[new],j]+=0.5*sg*v
    # S^2
    Sz=np.zeros(D); 
    for st in states:
        n_up=sum(1 for i in st if so[i][1]==1); n_dn=7-n_up
        Sz[sidx[st]]=0.5*(n_up-n_dn)
    return H,states,sidx,Sz
EOF
cat << 'EOF' > run.py
from d7 import *
import numpy as np
B,C=922.,4156.
# sanity: free ion (Dq=0) spectrum
H,states,sidx,Sz=build_H(0,B,C)
print("hermitian", np.allclose(H,H.conj().T))
ev=np.linalg.eigvalsh(H)
print(np.round(ev[:10],1))
EOF
time python3 run.py