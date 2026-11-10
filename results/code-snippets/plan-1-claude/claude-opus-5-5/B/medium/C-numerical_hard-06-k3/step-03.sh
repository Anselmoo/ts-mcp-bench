cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2; ms=[-2,-1,0,1,2]
# ck(m1,m2) = sqrt(4pi/(2k+1)) * <l m1|Y_k,m1-m2|l m2>
import math
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    # <Y_l m1 | Y_kq | Y_l m2> = int conj(Y_lm1) Y_kq Y_lm2 = (-1)^m1 gaunt(l,k,l,-m1,q,m2)
    return float((-1)**m1*gaunt(l,k,l,-m1,q,m2))*math.sqrt(4*math.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
def two(i,j,k,lq,F):  # <ij|1/r|kl>
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[i],so[j],so[k],so[lq]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.0
    return sum(F[kk]*CK[(kk,m1,m3)]*CK[(kk,m4,m2)] for kk in (0,2,4))
dets=list(itertools.combinations(range(10),6))
idx={d:i for i,d in enumerate(dets)}
def cf(Dq):
    V=np.zeros((5,5))
    for m in ms:
        V[m+2,m+2]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    return V
def apply(op_pairs, det):
    pass
def H(Dq,B,C):
    F2=49*(B+5*C/35); F4=441*C/35
    F={0:0.0,2:F2,4:F4}
    V=cf(Dq)
    n=len(dets); Hm=np.zeros((n,n))
    for a,d in enumerate(dets):
        occ=list(d)
        # one-body
        for p in occ:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=V[so[q][0]+2,so[p][0]+2]
                if v==0: continue
                if q!=p and q in occ: continue
                new=[q if x==p else x for x in occ]
                sign=1
                # sort with sign
                arr=new[:]; 
                for i in range(len(arr)):
                    for j in range(len(arr)-1-i):
                        if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
                Hm[idx[tuple(arr)],a]+=sign*v
        # two-body 1/2 sum <rs|tu> c_r+ c_s+ c_u c_t
        for t,u in itertools.permutations(occ,2):
            for r in range(10):
                for s in range(10):
                    if r==s: continue
                    v=two(r,s,t,u,F)
                    if v==0: continue
                    # apply c_u then c_t then c_s+ then c_r+
                    st=list(occ); sign=1
                    for op,orb in (('a',u),('a',t),('c',s),('c',r)):
                        if op=='a':
                            if orb not in st: sign=0;break
                            i=st.index(orb); sign*=(-1)**i; st.pop(i)
                        else:
                            if orb in st: sign=0;break
                            st.insert(0,orb)
                            # sort
                            arr=st
                            for i in range(len(arr)-1):
                                if arr[i]>arr[i+1]: arr[i],arr[i+1]=arr[i+1],arr[i]; sign=-sign
                    if sign==0: continue
                    Hm[idx[tuple(st)],a]+=0.5*sign*v
    return Hm
# S^2 via Sz=0 subspace singlets: compute S^2 matrix
def S2():
    n=len(dets); M=np.zeros((n,n))
    for a,d in enumerate(dets):
        occ=list(d)
        sz=sum(0.5 if so[o][1]==0 else -0.5 for o in occ)
        M[a,a]+=sz*sz-sz  # S^2 = S+S- ... use S-S+ + Sz^2 + Sz
        M[a,a]+=0
    # S^2 = S-S+ + Sz^2 + Sz
    for a,d in enumerate(dets):
        occ=list(d); sz=sum(0.5 if so[o][1]==0 else -0.5 for o in occ)
        M[a,a]=sz*sz+sz
        for p in occ:
            if so[p][1]!=1: continue  # S+ raises down->up
            q=p-1  # up partner
            if q in occ: continue
            st=[q if x==p else x for x in occ]  # S+
            for p2 in st:
                if so[p2][1]!=0: continue
                q2=p2+1
                if q2 in st: continue
                st2=sorted(q2 if x==p2 else x for x in st)
                # signs: replacing adjacent indices preserves order since p,q adjacent -> sign +1 unless crossing
                sign=1
                M[idx[tuple(st2)],a]+=sign
    return M
EOF
echo ok