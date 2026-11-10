
cat << 'EOF' > /tmp/d4.py
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from fractions import Fraction
l=2
ms=list(range(-2,3))
def C(k,q,m,mp):  # <l m|C^k_q|l m'>
    if abs(m-q-mp)>0: return 0.0  # need m = q + m' convention: <m|C_q|m'> nonzero if m=m'+q
    return (-1)**(l-m)*float(wigner_3j(l,k,l,-m,q,mp))*(2*l+1)*(-1)**0
def ang(k,a,c,b,d):
    # sum_q <a|C^k_q|c><b|C^k_-q|d>
    s=0.0
    for q in range(-k,k+1):
        s+=C(k,q,a,c)*C(k,-q,b,d)
    return s
# Slater-integral coefficients: V(ab,cd)=sum_k F^k ang_k
# spin-orbitals: (m,s)
def V2(a,b,c,d):  # a,b,c,d are (m,s): <ab|V|cd> with spin delta
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=a,b,c,d
    if sa!=sc or sb!=sd: return None
    return [ang(k,ma,mc,mb,md) for k in (0,2,4)]
# Slater-Condon coefficients (Condon-Shortley radial): F0 excluded (constant for fixed n)
B=1.0; Cc=3657/821
F4=441*Cc/35; F2=441*B+5*F4
Fk={0:0.0,2:F2,4:F4}
orbs=[(m,s) for m in ms for s in (0.5,-0.5)]
def occ_states(n=4):
    return list(itertools.combinations(range(10),n))
states=occ_states()
idx={s:i for i,s in enumerate(states)}
def ham_coul(states):
    N=len(states); H=np.zeros((N,N))
    # two-body: 1/2 sum_{ijkl} <ij|V|kl> a+_i a+_j a_l a_k ; use determinant rules via brute force
    # Build via second quantization on occupation sets
    for col,st in enumerate(states):
        occ=list(st)
        # for each pair of occupied (p<q) and pair ... apply 1/2 sum V a+_i a+_j a_l a_k
        for k_ in occ:
            for l_ in occ:
                if k_==l_: continue
                # annihilate k_ and l_ then create i,j
                pass
    return H
# simpler: explicit operator via pair removal/insertion
def apply_pair(st, p, q, r, s_):
    # apply a+_p a+_q a_s a_r  (r,s_ annihilated; applied right-to-left: a_r first? define a+_p a+_q a_s a_r)
    occ=list(st)
    sign=1
    # annihilate r
    if r not in occ: return None,0
    pos=occ.index(r); sign*=(-1)**pos; occ.pop(pos)
    if s_ not in occ: return None,0
    pos=occ.index(s_); sign*=(-1)**pos; occ.pop(pos)
    if q in occ: return None,0
    # create q
    pos=sum(1 for x in occ if x<q); sign*=(-1)**pos; occ.insert(pos,q)
    if p in occ: return None,0
    pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
    return tuple(sorted(occ)),sign
import sys
def build_coul():
    N=len(states)
    Mk={k:np.zeros((N,N)) for k in (2,4)}
    # V = 1/2 sum_{pqrs} <pq|V|rs> a+_p a+_q a_s a_r  with <pq|V|rs>=sum_k F^k ang_k(m_p,m_r,m_q,m_s) delta(s_p,s_r) delta(s_q,s_s)
    for k in (2,4):
        for p in range(10):
         for q in range(10):
          for r in range(10):
           for s_ in range(10):
             mp,sp=orbs[p]; mq,sq=orbs[q]; mr,sr=orbs[r]; ms_,ss=orbs[s_]
             if sp!=sr or sq!=ss: continue
             val=ang(k,mp,mr,mq,ms_)
             if abs(val)<1e-14: continue
             for ci,st in enumerate(states):
                 new,sg=apply_pair(st,p,q,r,s_)
                 if new is None: continue
                 Mk[k][idx[new],ci]+=0.5*val*sg
    return Mk
Mk=build_coul()
Hee=Fk[2]*Mk[2]+Fk[4]*Mk[4]
# cubic field one-electron (in m basis): diag(1,-4,6,-4,1) for m=-2..2 shifted; off-diag <2|V|-2>=5 ; Dq scaling
one=np.zeros((10,10))
diag={-2:1,-1:-4,0:6,1:-4,2:1}
for i,(m,s) in enumerate(orbs):
    one[i,i]=diag[m]
for i,(m,s) in enumerate(orbs):
    for j,(m2,s2) in enumerate(orbs):
        if s==s2 and m==2 and m2==-2: one[i,j]=5
        if s==s2 and m==-2 and m2==2: one[i,j]=5
# one-body operator matrix in determinant basis
def build_one(one):
    N=len(states); H=np.zeros((N,N))
    for ci,st in enumerate(states):
        for p in range(10):
            for r in range(10):
                if one[p,r]==0: continue
                occ=list(st)
                if r not in occ: continue
                pos=occ.index(r); sg=(-1)**pos; occ.pop(pos)
                if p in occ: continue
                pos=sum(1 for x in occ if x<p); sg*=(-1)**pos; occ.insert(pos,p)
                H[idx[tuple(occ)],ci]+=one[p,r]*sg
    return H
H1=build_one(one)
np.save('/tmp/Hee.npy',Hee); np.save('/tmp/H1.npy',H1)
# check d2 test
EOF
cd /tmp && timeout 900 python3 d4.py && echo done
