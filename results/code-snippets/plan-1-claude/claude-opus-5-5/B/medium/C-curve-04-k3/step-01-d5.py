import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N
B=800.;C=3473.
F2=49*B+7*C; F4=441*C/35
l=2; ms=range(-2,3)
def ck(k,m1,m2): # c^k(l m1, l m2)
    return float(N(((-1)**m1)*5*__import__('sympy').sqrt(1)*0))  # placeholder
from sympy.physics.wigner import wigner_3j
def cK(k,m1,m2):
    return float(N((-1)**m1*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2)))
so=[(m,s) for m in ms for s in (0.5,-0.5)]
def g(a,b,c,d): # <ab|1/r|cd>, a,c electron1
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.
    return sum(cK(k,ma,mc)*cK(k,md,mb)*F for k,F in ((2,F2),(4,F4)))
n=10
G=np.zeros((n,)*4)
for a,b,c,d in itertools.product(range(n),repeat=4): G[a,b,c,d]=g(a,b,c,d)
def cf(Dq):
    V=np.zeros((5,5)); d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): V[i,i]=d[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    h=np.zeros((n,n))
    for i in range(n):
        for j in range(n):
            if so[i][1]==so[j][1]: h[i,j]=V[so[i][0]+2,so[j][0]+2]
    return h
dets=list(itertools.combinations(range(n),5)); idx={d:i for i,d in enumerate(dets)}
D=len(dets)
def apply1(op_pairs,det):  # helper sign
    pass
def sign_rm(det,orbs):
    pass
# build matrices via second quantization
def ann(o,st):
    if o not in st: return None
    i=st.index(o); return (-1)**i, st[:i]+st[i+1:]
def cre(o,st):
    if o in st: return None
    st2=tuple(sorted(st+(o,))); i=st2.index(o); return (-1)**i, st2
H1=np.zeros((D,D,)); H2=np.zeros((D,D)); S2=np.zeros((D,D)); C4=np.zeros(D,complex)
def one(i,j,det):
    r=ann(j,det)
    if r is None: return None
    s1,st=r; r=cre(i,st)
    if r is None: return None
    return s1*r[0], r[1]
for J,det in enumerate(dets):
    C4[J]=np.prod([np.exp(1j*so[o][0]*np.pi/2) for o in det])
    for i in range(n):
        for j in range(n):
            r=one(i,j,det)
            if r: H1[idx[r[1]],J]+=0  # filled later
    for a in range(n):
     for b in range(n):
      for c in range(n):
       for d in range(n):
        v=G[a,b,c,d]
        if v==0: continue
        r=ann(c,det)
        if r is None: continue
        s,st=r; r=ann(d,st)
        if r is None: continue
        s*=r[0]; st=r[1]; r=cre(b,st)
        if r is None: continue
        s*=r[0]; st=r[1]; r=cre(a,st)
        if r is None: continue
        s*=r[0]; H2[idx[r[1]],J]+=0.5*v*s
# S^2 = S-S+ + Sz^2 + Sz
up=[2*k for k in range(5)]; dn=[2*k+1 for k in range(5)]
for J,det in enumerate(dets):
    sz=sum(so[o][1] for o in det)
    S2[J,J]+=sz*sz+sz
    for k in range(5):
        r=one(up[k],dn[k],det)  # S+
        if r is None: continue
        s1,st=r
        for k2 in range(5):
            r2=one(dn[k2],up[k2],st)
            if r2: S2[idx[r2[1]],J]+=s1*r2[0]
def h1mat(h):
    M=np.zeros((D,D))
    for J,det in enumerate(dets):
        for i in range(n):
            for j in range(n):
                if h[i,j]==0: continue
                r=one(i,j,det)
                if r: M[idx[r[1]],J]+=h[i,j]*r[0]
    return M
H1u=h1mat(cf(1.0))
names={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}
for x in (1.45,2.55,3.25):
    H=H2+H1u*x*B
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-3: j+=1
        vs=v[:,i:j]
        s2=np.trace(vs.T@S2@vs)/(j-i); S=(-1+np.sqrt(1+4*s2))/2
        mult=int(round(2*S+1)); sp=(j-i)//mult
        ch=np.real(np.trace(vs.conj().T@np.diag(C4)@vs))/mult
        out.append((round((w[i]-w[0])/B,3),f"{mult}{names.get((sp,int(round(ch))),'?')}"))
        i=j
    print(x,out[:5])
