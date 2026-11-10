import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=828.;C=3390.
l=2
def ck(k,m,mp):
    return float((-1)**m*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m,m-mp,mp))
F={0:0.0,2:49*B+7*C,4:441*C/35}
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
def V(a,b,c,d):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[c],so[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*F[k] for k in (2,4))
N=10
Vt=np.zeros((N,)*4)
for a,b,c,d in itertools.product(range(N),repeat=4): Vt[a,b,c,d]=V(a,b,c,d)
dets=list(itertools.combinations(range(N),3)); idx={d:i for i,d in enumerate(dets)}
nd=len(dets)
def apply_ops(det,creat,annih):
    # returns sign,newdet for c^+_p c^+_q c_s c_r applied (annih list order applied first last..)
    st=list(det); sign=1
    for o in annih:
        if o not in st: return 0,None
        i=st.index(o); sign*=(-1)**i; st.pop(i)
    for o in creat:
        if o in st: return 0,None
        st.insert(0,o); sign*=1
    # sort
    perm=sorted(range(len(st)),key=lambda i:st[i])
    # parity
    p=list(perm); par=0
    seen=[False]*len(p)
    for i in range(len(p)):
        if not seen[i]:
            j=i;L=0
            while not seen[j]: seen[j]=True;j=p[j];L+=1
            par+=L-1
    return sign*(-1)**par,tuple(sorted(st))
H2=np.zeros((nd,nd))
for j,det in enumerate(dets):
    for p,q,r,s in itertools.product(range(N),repeat=4):
        v=Vt[p,q,r,s]
        if v==0: continue
        # 1/2 sum V_pqrs c+p c+q c_s c_r
        sg,nd_=apply_ops(det,[q,p],[s,r])  # apply c_s then c_r? order: c+p c+q c_s c_r acting: c_r first, then c_s, then c+q, then c+p
        if sg==0: continue
        H2[idx[nd_],j]+=0.5*v*sg
# fix ordering: annih applied list order r then s; creation insert q then p at front
