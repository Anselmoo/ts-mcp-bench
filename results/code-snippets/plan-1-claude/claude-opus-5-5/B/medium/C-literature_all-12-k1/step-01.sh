
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2; ml=[-2,-1,0,1,2]
orbs=[(m,s) for m in ml for s in (0,1)]
# ck coefficients
def ck(k,m1,m2):
    return float((-1)**m1*np.sqrt(5*5)*0+0)
from sympy.physics.wigner import wigner_3j
def c(k,m1,m2):
    return float((-1)**(-m1)*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
# two-electron integral <m1 m2|1/r|m3 m4> = sum_k c^k(m1,m3) c^k(m4,m2) F^k delta(m1+m2,m3+m4)
def V(m1,m2,m3,m4,F):
    if m1+m2!=m3+m4: return 0
    return sum(c(k,m1,m3)*c(k,m4,m2)*F[k] for k in (0,2,4))
# crystal field octahedral in real d basis: Dq*(6 for eg, -4 for t2g) in complex basis
Hcf=np.zeros((5,5))
idx={m:i for i,m in enumerate(ml)}
Hcf[idx[0],idx[0]]=6; Hcf[idx[1],idx[1]]=Hcf[idx[-1],idx[-1]]=-4
Hcf[idx[2],idx[2]]=Hcf[idx[-2],idx[-2]]=1
Hcf[idx[2],idx[-2]]=Hcf[idx[-2],idx[2]]=5
states=list(itertools.combinations(range(10),7))
sidx={s:i for i,s in enumerate(states)}
N=len(states)
# precompute operators
import functools
def apply_one(st):
    pass
def build(Dq,B,C):
    F={0:0,2:49*B+7*C,4:441*C/35}
    H=np.zeros((N,N))
    for a,st in enumerate(states):
        occ=list(st)
        # one-body
        for i in occ:
            for j in range(10):
                if orbs[j][1]!=orbs[i][1]: continue
                h=Hcf[idx[orbs[j][0]],idx[orbs[i][0]]]*Dq
                if h==0: continue
                if j!=i and j in occ: continue
                new=[x if x!=i else j for x in occ]
                sign=1
                # sort sign
                arr=new[:]; 
                for p in range(len(arr)):
                    for q in range(len(arr)-1-p):
                        if arr[q]>arr[q+1]: arr[q],arr[q+1]=arr[q+1],arr[q]; sign=-sign
                H[sidx[tuple(arr)],a]+=sign*h
        # two-body: sum_{i<j occ} sum_{k<l} <kl||ij>
        for i,j in itertools.combinations(occ,2):
            rest=[x for x in occ if x not in (i,j)]
            for k,l in itertools.combinations(range(10),2):
                if k in rest or l in rest: continue
                (mi,si),(mj,sj),(mk,sk),(ml_,sl)=orbs[i],orbs[j],orbs[k],orbs[l]
                v=0
                if sk==si and sl==sj: v+=V(mk,ml_,mi,mj,F)
                if sl==si and sk==sj: v-=V(ml_,mk,mi,mj,F)
                if v==0: continue
                # a_k^+ a_l^+ a_j a_i |st>  ... build by sign
                def ann(lst,o):
                    p=lst.index(o); return (-1)**p, lst[:p]+lst[p+1:]
                def cre(lst,o):
                    p=sum(1 for x in lst if x<o); return (-1)**p, sorted(lst+[o])
                s1,L=ann(occ,i); s2,L=ann(L,j); s3,L=cre(L,l); s4,L=cre(L,k)
                H[sidx[tuple(L)],a]+=s1*s2*s3*s4*v
    return H
# S^2
def S2():
    M=np.zeros((N,N))
    for a,st in enumerate(states):
        occ=list(st)
        Sz=sum(0.5 if orbs[o][1]==0 else -0.5 for o in occ)
        M[a,a]+=Sz*Sz
        # S-S+ : count
        for i in occ:
            if orbs[i][1]!=1: continue
            j=i-1  # same m, spin up
            if j in occ: continue
            # S+ moves i->j; then S- moves back some up->down
            p=occ.index(i); s1=(-1)**p; L=occ[:p]+occ[p+1:]
            q=sum(1 for x in L if x<j); s2=(-1)**q; L2=sorted(L+[j])
            for k in L2:
                if orbs[k][1]!=0: continue
                kk=k+1
                if kk in L2 and kk!=k: 
                    continue
                p=L2.index(k); t1=(-1)**p; L3=L2[:p]+L2[p+1:]
                q=sum(1 for x in L3 if x<kk); t2=(-1)**q; L4=tuple(sorted(L3+[kk]))
                M[sidx[L4],a]+=s1*s2*t1*t2
        M[a,a]+=0  
    return M
S2M=S2()
# S^2 = S-S+ + Sz^2 + Sz
for a,st in enumerate(states):
    S2M[a,a]+=sum(0.5 if orbs[o][1]==0 else -0.5 for o in st)
def levels(Dq,B,C):
    H=build(Dq,B,C)
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,jk,ki->i',v.T,S2M,v)
    S=np.round((-1+np.sqrt(1+4*s))/2*2)/2
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(w[j]-w[i])<1e-3: j+=1
        out.append((w[i]-w[0],S[i],j-i)); i=j
    return out
import sys
for e in levels(625,800,3200)[:14]: print(e)
EOF
python3 /tmp/d7.py
