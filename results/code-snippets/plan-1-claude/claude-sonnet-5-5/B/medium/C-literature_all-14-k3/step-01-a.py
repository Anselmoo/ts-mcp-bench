import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def ck(k,m1,m2): # <m1|C^k_q|m2> via gaunt: (-1)^m1 * sqrt... use gaunt
    return float(gaunt(2,k,2,-m1,m1-m2,m2))
# use Gaunt-based: c^k(m1,m2)=sqrt(4pi/(2k+1)) * int Y2m1* Y_k,(m1-m2) Y2m2
def c(k,m1,m2):
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2))
def build(Dq,B,C):
    F2=49*B+7*C;F4=63*C/5
    Fk={0:0,2:F2,4:F4}
    # a^k = F_k * (2l+1)^... use Condon-Shortley: F^k/ (stuff) -> use direct: g(m1m2m3m4)=sum_k a_k...
    # direct Coulomb <ab|1/r|cd> = sum_k c^k(a,c)c^k(d,b) F_k  (with Slater F_k, 4 pi/(2k+1) incl in c) 
    states=list(itertools.combinations(range(10),7))
    idx={s:i for i,s in enumerate(states)}
    n=len(states)
    # one-body: cubic field in real basis; in m basis: Dq*(...) 
    h=np.zeros((10,10))
    # cubic: <2|V|2>=<-2|V|-2>=Dq,<1|..>=<-1|..>=-4Dq,<0>=6Dq,<2|V|-2>=5Dq
    for m,v in {2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}.items():
        for s in (0,1): h[2*(m+2)+s,2*(m+2)+s]=v
    for s in (0,1): h[2*4+s,2*0+s]=5*Dq; h[2*0+s,2*4+s]=5*Dq
    # two-body V[a,b,c,d]=<ab|g|cd>
    V=np.zeros((10,10,10,10))
    for a,(m1,s1) in enumerate(orbs):
     for b,(m2,s2) in enumerate(orbs):
      for cc,(m3,s3) in enumerate(orbs):
       for d,(m4,s4) in enumerate(orbs):
        if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
        V[a,b,cc,d]=sum(c(k,m1,m3)*c(k,m4,m2)*Fk[k] for k in (2,4))
    return states,idx,h,V
