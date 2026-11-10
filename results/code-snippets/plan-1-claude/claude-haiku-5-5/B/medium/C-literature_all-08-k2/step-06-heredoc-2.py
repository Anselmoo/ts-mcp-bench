import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
A={}
for k in (0,2,4):
    arr=np.zeros((5,5,5,5))
    for i1,m1 in enumerate(range(-2,3)):
     for i2,m2 in enumerate(range(-2,3)):
      for i3,m3 in enumerate(range(-2,3)):
       for i4,m4 in enumerate(range(-2,3)):
        tot=0.0
        for q in range(-k,k+1):
            if (-m1)-q+m3!=0 or (-m2)+q+m4!=0: continue
            g1=float(gaunt(2,k,2,-m1,-q,m3)); g2=float(gaunt(2,k,2,-m2,q,m4))
            tot+=(-1)**(m1+q+m2)*g1*g2
        arr[i1,i2,i3,i4]=4*pi/(2*k+1)*tot
    A[k]=arr
basis=list(itertools.combinations(range(10),5))
idx={s:i for i,s in enumerate(basis)}
s2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
orbitals=[(6,vec({0:1})),(6,vec({2:1/s2,-2:1/s2})),(-4,vec({2:1/(1j*s2),-2:-1/(1j*s2)})),
          (-4,vec({1:1/s2,-1:-1/s2})),(-4,vec({1:1/(1j*s2),-1:1/(1j*s2)}))]
def ops(Dq,B,C):
    F={0:0.0,2:441*B+63*C,4:12.6*C}
    M=np.zeros((5,5),complex)
    for e,v in orbitals: M+=Dq*e*np.outer(v,v.conj())
    h=np.zeros((10,10),complex)
    for i,(m,s) in enumerate(orbs):
        for j,(mm,ss) in enumerate(orbs):
            if s==ss: h[i,j]=M[m+2,mm+2]
    Vt=np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(10),repeat=4):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
        if sa!=sc or sb!=sd: continue
        Vt[a,b,c,d]=sum(F[k]*A[k][ma+2,mb+2,mc+2,md+2] for k in (0,2,4))
    return h,Vt
def apply_ann(st,p):
    # returns (sign, newlist) annihilate orbital p from sorted list st
    if p not in st: return None
    sgn=(-1)**sum(1 for x in st if x<p)
    return sgn,[x for x in st if x!=p]
def apply_cre(st,p):
    if p in st: return None
    sgn=(-1)**sum(1 for x in st if x<p)
    return sgn,sorted(st+[p])
def Hmat(Dq,B,C):
    h,Vt=ops(Dq,B,C)
    dim=len(basis); H=np.zeros((dim,dim),complex)
    for col,occ in enumerate(basis):
        st0=list(occ)
        for i in range(10):
          for j in range(10):
            if h[i,j]==0: continue
            r=apply_ann(st0,j)
            if r is None: continue
            s1,st1=r
            r2=apply_cre(st1,i)
            if r2 is None: continue
            s2_,st2=r2
            H[idx[tuple(st2)],col]+=s1*s2_*h[i,j]
        # two-body: 0.5 sum <ij|kl> a+_i a+_j a_l a_k  (V_ijkl = <ij|1/r|kl>)
        for k_,l_ in itertools.permutations(st0,2):
          r=apply_ann(st0,l_)  # apply a_l first? order: a_l a_k |> ; a_k acts first
          # a_l a_k |occ>: first a_k then a_l
          ra=apply_ann(st0,k_)
          s_a,st_a=ra
          rb=apply_ann(st_a,l_)
          if rb is None: continue
          s_b,st_b=rb
          for i in range(10):
            for j in range(10):
              v=Vt[i,j,k_,l_]
              if v==0: continue
              rc=apply_cre(st_b,j)
              if rc is None: continue
              s_c,st_c=rc
              rd=apply_cre(st_c,i)
              if rd is None: continue
              s_d,st_d=rd
              H[idx[tuple(st_d)],col]+=0.5*s_a*s_b*s_c*s_d*v
    return H
def S2(): 
    # S^2 = Sz^2 + (S+S- + S-S+)/2 ; build via spin-orbitals
    dim=len(basis); S=np.zeros((dim,dim))
    Sz=np.zeros(dim)
    for c,occ in enumerate(basis):
        Sz[c]=0.5*sum(1 if orbs[x][1]==0 else -1 for x in occ)
    # S+ = sum_m a+_{m,up} a_{m,down}
    Sp=np.zeros((dim,dim))
    for col,occ in enumerate(basis):
        for m in range(-2,3):
            pu=orbs.index((m,0)); pd=orbs.index((m,1))
            r=apply_ann(list(occ),pd)
            if r is None: continue
            s1,st1=r
            r2=apply_cre(st1,pu)
            if r2 is None: continue
            Sp[idx[tuple(r2[1])],col]+=s1*r2[0]
    Sm=Sp.T
    return np.diag(Sz**2)+0.5*(Sp@Sm+Sm@Sp)
S2m=S2()
np.save if False else None
# Test free ion d5 with B=1,C=4 and Dq=0
H=Hmat(0.0,1.0,4.0)
print("hermitian:", np.allclose(H,H.conj().T))
# separate by S: eigen of H + big*(S2 - 35/4)
# Confirm multiplet energies
M=H+1e4*(S2m-(35/4)*np.eye(len(basis)))
w,v=np.linalg.eigh((M+M.conj().T)/2)
Ssp=np.linalg.eigh(S2m)
ev=np.round(w,4)
import collections
print(collections.Counter(np.round(ev,3)).most_common())
