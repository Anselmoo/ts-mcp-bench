import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
from functools import lru_cache
l=2
orbs=[(m,s) for m in range(-2,3) for s in (1,-1)]   # spin-orbitals
n=len(orbs)
def ck(k,m,q,mp):
    # <l m|C^k_q|l mp>
    if m!=m+0 or q!=(m-mp) : pass
    if -m+q+mp!=0: return 0.0
    red=(-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    return (-1)**(l-m)*float(wigner_3j(l,k,l,-m,q,mp))*red
def angular(k,m1,m2,m3,m4):
    # <m1 m2|C^k(1).C^k(2)|m3 m4>
    s=0.0
    for q in range(-k,k+1):
        s+=(-1)**q*ck(k,m1,q,m3)*ck(k,m2,-q,m4)
    return s
# Coulomb matrix elements in spin-orbitals: V[i,j,k,l] = <i j|1/r12|k l>, spin-diag
V=np.zeros((n,n,n,n,5))  # store angular coeff for k=0,2,4
for i,(m1,s1) in enumerate(orbs):
 for j,(m2,s2) in enumerate(orbs):
  for kk,(m3,s3) in enumerate(orbs):
   for ll,(m4,s4) in enumerate(orbs):
    if s1!=s3 or s2!=s4: continue
    for k in (0,2,4):
        V[i,j,kk,ll,k]=angular(k,m1,m2,m3,m4)
# sanity: F^k multiply by (4pi/(2k+1)) normalization included in C^k convention -> e^2/r = sum_k F^k C^k.C^k
def fock_basis(N):
    return [tuple(c) for c in itertools.combinations(range(n),N)]
def build(N,Fk,dq):
    basis=fock_basis(N); idx={b:i for i,b in enumerate(basis)}
    D=len(basis); H=np.zeros((D,D))
    # one-body ligand field: -4Dq on t2g, +6Dq on eg per spin-orbital (projector form)
    h=np.zeros((n,n))
    # eg projector in m basis: |0><0| + (|2>+|-2>)(<2|+<-2|)/2
    pe=np.zeros((5,5)); ix={m:i for i,m in enumerate(range(-2,3))}
    pe[ix[0],ix[0]]=1
    v=np.zeros(5); v[ix[2]]+=1; v[ix[-2]]+=1; pe+=np.outer(v,v)/2
    one=-4*np.eye(5)+10*pe
    for i,(m1,s1) in enumerate(orbs):
     for j,(m2,s2) in enumerate(orbs):
      if s1==s2: h[i,j]=dq*one[ix[m1],ix[m2]]
    W=sum(Fk[k]*V[:,:,:,:,k] for k in (0,2,4))
    def occ_list(b): return list(b)
    for bi,b in enumerate(basis):
        # one-body
        for i in b:
            pass
        for jj in range(n):
            for ii in range(n):
                if h[ii,jj]==0: continue
                # c_i^dag c_j |b>
                if jj not in b: continue
                bl=list(b); pos=bl.index(jj); sgn=(-1)**pos; bl.pop(pos)
                if ii in bl: continue
                # insert ii
                p=sum(1 for x in bl if x<ii); sgn*=(-1)**p; bl.insert(p,ii)
                t=tuple(bl)
                H[idx[t],bi]+=h[ii,jj]*sgn
        # two-body: 1/2 sum W[i,j,k,l] c_i^+ c_j^+ c_l c_k
        for k_ in b:
          for l_ in b:
            if k_==l_: continue
            for i_ in range(n):
              for j_ in range(n):
                w=W[i_,j_,k_,l_]
                if abs(w)<1e-14: continue
                bl=list(b)
                # annihilate l_ then k_ (c_l c_k acting: first k then l)
                s=1
                pk=bl.index(k_); s*=(-1)**pk; bl.pop(pk)
                if l_ not in bl: continue
                pl=bl.index(l_); s*=(-1)**pl; bl.pop(pl)
                # create j then i
                if j_ in bl: continue
                p=sum(1 for x in bl if x<j_); s*=(-1)**p; bl.insert(p,j_)
                if i_ in bl: continue
                p=sum(1 for x in bl if x<i_); s*=(-1)**p; bl.insert(p,i_)
                t=tuple(sorted(bl)) if False else None
                # recompute sign from ordered insertion: bl is ordered? ensure canonical
                # sign of permutation to sorted order
                perm=bl[:]; sign=1
                for a in range(len(perm)):
                    for c in range(len(perm)-1-a):
                        if perm[c]>perm[c+1]:
                            perm[c],perm[c+1]=perm[c+1],perm[c]; sign=-sign
                H[idx[tuple(perm)],bi]+=0.5*w*s*sign
    return basis,H
