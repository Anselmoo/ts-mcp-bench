python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.sparse import csr_matrix, kron, identity
from scipy.optimize import least_squares
ms = [-2,-1,0,1,2]
xg, wg = np.polynomial.legendre.leggauss(30)
th = np.arccos(xg); ph = np.linspace(0,2*np.pi,64,endpoint=False)
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = np.outer(wg, np.full(64, 2*np.pi/64))
def Y(l,m,t,p): return sph_harm_y(l, m, t, p)
def Ck(k,q,t,p): return np.sqrt(4*np.pi/(2*k+1))*Y(k,q,t,p)
def mat(k,q):
    M = np.zeros((5,5),complex)
    for i,a in enumerate(ms):
        for j,c in enumerate(ms):
            M[i,j] = np.sum(W*np.conj(Y(2,a,TH,PH))*Ck(k,q,TH,PH)*Y(2,c,TH,PH))
    return M
ak = {}
for k in (2,4):
    Cm = {q: mat(k,q) for q in range(-k,k+1)}
    A = np.zeros((5,5,5,5),complex)
    for a,b,c,d in itertools.product(range(5),repeat=4):
        A[a,b,c,d] = sum((-1)**q * Cm[-q][a,c]*Cm[q][b,d] for q in range(-k,k+1))
    ak[k]=A
Peg = np.zeros((5,5),complex); Peg[2,2]=1
v = np.zeros(5,complex); v[0]=1/np.sqrt(2); v[4]=1/np.sqrt(2)
Peg += np.outer(v,v.conj())
Pt2 = np.eye(5)-Peg
nso=10
I2=identity(2,format='csr'); Z=csr_matrix(np.diag([1.,-1.])); a_=csr_matrix(np.array([[0,1.],[0,0]]))
def ann(i):
    ops=[Z]*i+[a_]+[I2]*(nso-i-1)
    out=ops[0]
    for o in ops[1:]: out=kron(out,o,format='csr')
    return out
cc=[ann(i) for i in range(nso)]
cdg=[x.T.conj().tocsr() for x in cc]
def so(orb,s): return 2*orb+s
def coul_part(k):
    H=csr_matrix((1024,1024),dtype=complex)
    for a_o,b_o,c_o,d_o in itertools.product(range(5),repeat=4):
        Vv=ak[k][a_o,b_o,c_o,d_o]
        if abs(Vv)<1e-12: continue
        for s1 in (0,1):
            for s2 in (0,1):
                i=so(a_o,s1); j=so(b_o,s2); k_=so(c_o,s1); l=so(d_o,s2)
                H=H+0.5*Vv*(cdg[i]@cdg[j]@cc[l]@cc[k_])
    return H.toarray()
P2=coul_part(2); P4=coul_part(4)
h=np.zeros((nso,nso),complex)
for o1 in range(5):
    for o2 in range(5):
        for s in (0,1): h[so(o1,s),so(o2,s)]+=6*Peg[o1,o2]-4*Pt2[o1,o2]
Hf=sum(h[i,j]*(cdg[i]@cc[j]) for i in range(nso) for j in range(nso) if abs(h[i,j])>1e-12).toarray()
Sp=sum(cdg[so(m,0)]@cc[so(m,1)] for m in range(5)).toarray()
Sm=Sp.conj().T
Nup=sum(cdg[so(m,0)]@cc[so(m,0)] for m in range(5)).toarray()
Ndn=sum(cdg[so(m,1)]@cc[so(m,1)] for m in range(5)).toarray()
Sz=0.5*(Nup-Ndn)
S2=Sm@Sp+Sz@Sz+Sz
Mocc=np.zeros(1024)
for st in range(1024):
    Mocc[st]=sum(ms[i//2] for i in range(nso) if (st>>(nso-1-i))&1)
Uc=np.exp(-1j*np.pi/2*Mocc)
def sector(nup,ndn):
    out=[]
    for ups in itertools.combinations(range(5),nup):
        for dns in itertools.combinations(range(5),ndn):
            occ=[so(o,0) for o in ups]+[so(o,1) for o in dns]
            out.append(sum(1<<(nso-1-i) for i in occ))
    return out
S32=sector(5,2); S12=sector(4,3)
def analyze(Dq,B,C):
    H=(49*B+7*C)*P2+(441*C/35)*P4+Dq*Hf
    Hq=H[np.ix_(S32,S32)]; w,V=np.linalg.eigh(Hq)
    quart=[]; i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-6: j+=1
        P=V[:,i:j+1]; U=P.conj().T@np.diag(Uc[S32])@P
        quart.append((w[i]-w[0],j-i+1,round(np.trace(U).real,2)))
        i=j+1
    mu=1e6
    Hd=H[np.ix_(S12,S12)]+mu*S2[np.ix_(S12,S12)]
    w,V=np.linalg.eigh(Hd)
    keep=[k for k in range(len(w)) if w[k]<mu*2]
    Vk=V[:,keep]; Ek=w[keep]-mu*0.75
    dub=[]; i=0
    while i<len(Ek):
        j=i
        while j+1<len(Ek) and abs(Ek[j+1]-Ek[i])<1e-6: j+=1
        P=Vk[:,i:j+1]; U=P.conj().T@np.diag(Uc[S12])@P
        dub.append((Ek[i]-w_g0(H),j-i+1,round(np.trace(U).real,2)))
        i=j+1
    return quart,dub
def w_g0(H):
    return np.linalg.eigvalsh(H[np.ix_(S32,S32)])[0]
def model(p):
    Dq,B,C=p
    q,d=analyze(Dq,B,C)
    t2=[e for e,n,c in q if n==3 and c==-1][0]
    a2=[e for e,n,c in q if n==1][0]
    t1p=[e for e,n,c in q if n==3 and c==1][1]
    t1d=[e for e,n,c in d if n==3 and c==1][1]
    return np.array([t2,a2,t1p,t1d])
target=np.array([7150,15200,19200,21130.])
def res(p): return model(p)-target
sol=least_squares(res,[715,1000,4000],x_scale=[100,100,500])
print("Dq,B,C =",sol.x); print("model",model(sol.x)); print("resid",res(sol.x))
q,d=analyze(*sol.x)
print("quartets",[(round(e,0),n,c) for e,n,c in q])
print("doublets(low)",[(round(e,0),n,c) for e,n,c in d[:8]])
EOF