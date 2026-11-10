import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt as ssqrt
B=722.;C=3003.
F={0:0.,2:49*B+7*C,4:441*C/35}
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) for l=2
    from sympy.physics.wigner import wigner_3j
    return float((-1)**(-m1)*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def g(m1,m2,m3,m4):
    if m1+m2!=m3+m4: return 0.
    return sum(CK[(k,m1,m3)]*CK[(k,m4,m2)]*F[k] for k in (0,2,4))
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
def V1(Dq):
    v=np.zeros((10,10))
    d={0:6,1:-4,-1:-4,2:1,-2:1}
    for i,(m,s) in enumerate(so):
        v[i,i]=d[m]*Dq
        for j,(m2,s2) in enumerate(so):
            if s==s2 and m==2 and m2==-2 or s==s2 and m==-2 and m2==2: v[i,j]=5*Dq
    return v
def build(one):
    N=len(dets);H=np.zeros((N,N))
    for a,d in enumerate(dets):
        # one-body
        for p in d:
            for q in range(10):
                if one[q,p]==0: continue
                if q!=p and q in d: continue
                nd=list(d);pos=nd.index(p);nd[pos]=q
                sign=1
                # sort
                perm=sorted(range(3),key=lambda i:nd[i]);srt=tuple(nd[i] for i in perm)
                sign=np.linalg.det(np.eye(3)[perm])
                H[idx[srt],a]+=sign*one[q,p]
        # two-body: sum over pairs p<q annihilate, create r,s
        for p,q in itertools.combinations(d,2):
            rest=[x for x in d if x not in (p,q)]
            for r in range(10):
                for s_ in range(10):
                    if r==s_ or r in rest or s_ in rest: continue
                    (m1,s1),(m2,s2)=so[r],so[s_];(m3,s3),(m4,s4)=so[p],so[q]
                    if s1!=s3 or s2!=s4: continue
                    val=g(m1,m2,m3,m4)
                    if val==0: continue
                    # operator 1/2 sum a+r a+s a q a p ; pairs p<q all r,s ordered -> factor handled by summing all ordered r,s with ordered p<q:
                    # a_r^+ a_s^+ a_q a_p acting on |d>
                    st=list(d);sign=1
                    for x in (p,q):
                        i=st.index(x);sign*=(-1)**i;st.pop(i)
                    for x in (s_,r):
                        i=sum(1 for y in st if y<x);sign*=(-1)**i;st.insert(i,x)
                    H[idx[tuple(st)],a]+=sign*val
    return H
# S^2 and C4
def spinops():
    N=len(dets);Sz=np.zeros(N);Sp=np.zeros((N,N));R=np.zeros((N,N),complex)
    for a,d in enumerate(dets):
        Sz[a]=sum(0.5 if so[x][1]==1 else -0.5 for x in d)
        R[a,a]=np.exp(1j*np.pi/2*sum(so[x][0] for x in d))
        for p in d:
            if so[p][1]==0:
                q=p+1
                if q in d: continue
                st=list(d);i=st.index(p);sign=(-1)**i;st.pop(i)
                j=sum(1 for y in st if y<q);sign*=(-1)**j;st.insert(j,q)
                Sp[idx[tuple(st)],a]+=sign
    S2=Sp.T@Sp+np.diag(Sz**2+Sz)
    return S2,R
Hee=build(np.zeros((10,10)))
S2,R=spinops()
names={(4,1):'A1',(4,-1):'A2',(4,0):'E'}
for Dq_B in (1.0,2.2,3.5):
    H=Hee+build(V1(Dq_B*B))-Hee*0
    H=Hee+ (build(V1(Dq_B*B)) - build(np.zeros((10,10))))
    H=H+1e-7*S2
    w,v=np.linalg.eigh(H)
    E=(w-w[0])/B
    # group
    groups=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and abs(E[j]-E[i])<1e-5: j+=1
        V=v[:,i:j];s2=np.mean(np.diag(V.T@S2@V));S=(-1+np.sqrt(1+4*s2))/2
        mult=int(round(2*S+1));dim=(j-i)//mult
        ch=np.trace(V.conj().T@R@V).real/mult
        lab={1:'A1' if ch>0 else 'A2',2:'E',3:'T1' if ch>0 else 'T2'}[dim]
        groups.append((round(E[i],3),f'{mult}{lab}'));i=j
    print(Dq_B,groups[:5])
