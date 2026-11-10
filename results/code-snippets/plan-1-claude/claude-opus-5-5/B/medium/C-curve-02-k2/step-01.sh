
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
B=722.;C=3003.
F2=B+C/7;F4=C/35
# c^k(l m, l m') = sqrt(4pi/(2k+1)) * int Y*_lm Y_kq Y_lm'
import math
def ck(k,m1,m2):
    q=m1-m2
    # <2 m1|C^k_q|2 m2> = (-1)^m1 *5* (2 k 2;0 0 0)(2 k 2;-m1 q m2)
    from sympy.physics.wigner import wigner_3j
    return float((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,q,m2))
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (1,-1)]
def R(a,b,c,d): # <ab|1/r|cd>, orbitals indices
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=[orbs[i] for i in (a,b,c,d)]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    v=0.
    for k,F in ((2,F2),(4,F4)):
        v+=F*ck(k,ma,mc)*ck(k,md,mb)
    return v
n=10
U=np.zeros((n,n,n,n))
for a,b,c,d in itertools.product(range(n),repeat=4): U[a,b,c,d]=R(a,b,c,d)
def cf(Dq):
    h=np.zeros((n,n))
    for i,(m,s) in enumerate(orbs):
        for j,(m2,s2) in enumerate(orbs):
            if s!=s2: continue
            if m==m2: h[i,j]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
            if abs(m)==2 and m2==-m: h[i,j]=5*Dq
    return h
dets=[d for d in itertools.combinations(range(n),3) if sum(orbs[i][1] for i in d)==1]  # Ms=1/2
idx={d:i for i,d in enumerate(dets)}
def apply(op_pairs,det):pass
def sign_sort(l):
    l=list(l);s=1
    for i in range(len(l)):
        for j in range(len(l)-1-i):
            if l[j]>l[j+1]: l[j],l[j+1]=l[j+1],l[j]; s=-s
    return s,tuple(l)
D=len(dets)
def H(Dq):
    h1=cf(Dq);Hm=np.zeros((D,D))
    for I,d in enumerate(dets):
        # one body
        for p,i in enumerate(d):
            for j in range(n):
                if h1[j,i]==0: continue
                if j!=i and j in d: continue
                nd=list(d);nd[p]=j;s,t=sign_sort(nd)
                Hm[idx[t],I]+=s*h1[j,i]
        # two body: sum over pairs i<j in d, replace by k,l
        for p,q in itertools.combinations(range(3),2):
            i,j=d[p],d[q]
            rest=[x for r,x in enumerate(d) if r not in (p,q)]
            for k in range(n):
                for l in range(n):
                    if k==l or k in rest or l in rest: continue
                    v=U[k,l,i,j]  # <kl|ij>, antisym handled by summing all k,l ordered
                    if v==0: continue
                    nd=list(d);nd[p]=k;nd[q]=l;s,t=sign_sort(nd)
                    Hm[idx[t],I]+=s*v
    return Hm
# C4 operator diag phase; S^2
def c4(d): return np.prod([np.exp(-1j*orbs[i][0]*np.pi/2) for i in d])
C4=np.diag([c4(d) for d in dets])
# S^2 = S-S+ + Sz^2+Sz
S2=np.zeros((D,D))
for I,d in enumerate(dets):
    S2[I,I]+=0.25+0.5
    for p,i in enumerate(d):
        if orbs[i][1]!=-1: continue
        j=orbs.index((orbs[i][0],1))
        if j in d: continue
        nd=list(d);nd[p]=j  # S+ gives Ms=3/2 det
        # S- back
        for p2,i2 in enumerate(nd):
            if orbs[i2][1]!=1: continue
            j2=orbs.index((orbs[i2][0],-1))
            if j2 in nd: continue
            nd2=list(nd);nd2[p2]=j2;s,t=sign_sort(nd2)
            s0,_=sign_sort(nd)  # consistent ordering not needed since replacing in place
            S2[idx[t],I]+=s
for Dq in (1.0,2.2,3.5):
    w,v=np.linalg.eigh(H(Dq*B))
    w=w/B; groups=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-6: j+=1
        V=v[:,i:j];S=np.trace(V.T@S2@V)/(j-i);ch=np.trace(V.conj().T@C4@V).real
        mult=round(2*(-1+np.sqrt(1+4*S))/2+1)
        groups.append((w[i],j-i,mult,round(ch,3)));i=j
    g0=groups[0][0]
    print(Dq,[(round(e-g0,3),dg,m,c) for e,dg,m,c in groups[:6]])
EOF
python3 /tmp/d3.py
