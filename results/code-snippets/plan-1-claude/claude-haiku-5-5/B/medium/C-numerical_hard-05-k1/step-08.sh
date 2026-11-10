cat > /dev/null << 'EOF'
EOF
python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
nt, nphi = 24, 48
x, w = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(w, np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m): return sph_harm_y(l, m, TH, PH)
ms=list(range(-2,3)); Ylm={m:Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
def G(m1,m3,k,q): return integ(np.conj(Ylm[m1])*np.conj(Y(k,q))*Ylm[m3])
def H(m2,m4,k,q): return integ(np.conj(Ylm[m2])*Y(k,q)*Ylm[m4])
def angular(k):
    A=np.zeros((5,5,5,5),complex)
    for a,b,c,d in itertools.product(range(5),repeat=4):
        s=sum(G(ms[a],ms[c],k,q)*H(ms[b],ms[d],k,q) for q in range(-k,k+1))
        A[a,b,c,d]=4*np.pi/(2*k+1)*s
    return A
A2=angular(2); A4=angular(4)
F2=80.5; F4=0.70435*F2
Vt=F2*A2+F4*A4
def ket(m): return np.eye(5)[m+2].astype(complex)
t2g=[ket(1),ket(-1),(ket(2)-ket(-2))/(1j*np.sqrt(2))]
eg=[ket(0),(ket(2)+ket(-2))/np.sqrt(2)]
P_t=sum(np.outer(v,v.conj()) for v in t2g); P_e=sum(np.outer(v,v.conj()) for v in eg)
n=10
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(n),6)]
idx={d:k for k,d in enumerate(dets)}
def apply(state, ops):
    s=state; sign=1
    for typ,i in ops:
        occ=(s>>i)&1
        if typ=='a' and not occ: return None,0
        if typ=='c' and occ: return None,0
        sign*=(-1)**bin(s&((1<<i)-1)).count('1')
        s^=(1<<i)
    return s,sign
terms=[]
for i,j,k,l in itertools.product(range(n),repeat=4):
    oi,si=divmod(i,2); oj,sj=divmod(j,2); ok,sk=divmod(k,2); ol,sl=divmod(l,2)
    if si!=sk or sj!=sl: continue
    v=0.5*Vt[oi,oj,ok,ol]
    if abs(v)>1e-12: terms.append((i,j,k,l,v))
D=len(dets)
Hee=np.zeros((D,D),complex); Hcf=np.zeros((D,D),complex)
Mcf=(-4*P_t+6*P_e)
for col,d in enumerate(dets):
    for i,j,k,l,v in terms:
        s,sg=apply(d,[('a',k),('a',l),('c',j),('c',i)])
        if s is not None: Hee[idx[s],col]+=v*sg
    for i in range(n):
        for j in range(n):
            oi,si=divmod(i,2); oj,sj=divmod(j,2)
            if si!=sj: continue
            s,sg=apply(d,[('a',j),('c',i)])
            if s is not None: Hcf[idx[s],col]+=Mcf[oi,oj]*sg
Sp=np.zeros((D,D),complex)
for col,d in enumerate(dets):
    for o in range(5):
        s,sg=apply(d,[('a',2*o+1),('c',2*o)])
        if s is not None: Sp[idx[s],col]+=sg
Sz=np.array([sum(0.5 if i%2==0 else -0.5 for i in range(n) if (d>>i)&1) for d in dets])
S2=Sp.conj().T@Sp+np.diag(Sz*(Sz+1))
# singlet subspace basis
ev,U=np.linalg.eigh(S2)
Bs=U[:,np.abs(ev)<1e-8]
print("singlet dim",Bs.shape[1])
def levels(Dq):
    Hs=Bs.conj().T@(Hee+Dq*Hcf)@Bs
    e=np.linalg.eigvalsh(Hs)
    return e
for Dq in [0.0,1.0,2.0,3.0,4.0,5.0]:
    e=levels(Dq); e0=e[0]
    # group degeneracies
    groups=[]
    for val in e:
        if groups and abs(val-groups[-1][0])<1e-6: groups[-1][1]+=1
        else: groups.append([val,1])
    print("Dq/B=",Dq, [(round(g[0]-e0,3),g[1]) for g in groups])
EOF