import numpy as np, itertools
from numpy.polynomial.legendre import leggauss
from scipy.special import eval_legendre
from collections import Counter

nt, nph = 60, 120
x, w = leggauss(nt)
ph = np.arange(nph)*2*np.pi/nph
ct, PH = np.meshgrid(x, ph, indexing='ij')
st = np.sqrt(1-ct**2)
P = np.stack([st*np.cos(PH), st*np.sin(PH), ct], -1).reshape(-1,3)
W = (np.repeat(w[:,None], nph, 1)*(2*np.pi/nph)).reshape(-1)

def forb(p):
    X,Y,Z = p[:,0],p[:,1],p[:,2]
    return np.stack([X*Y, Y*Z, Z*X, X**2-Y**2, 3*Z**2-(X**2+Y**2+Z**2)],1)
F = forb(P)
F = F/np.sqrt(np.einsum('k,ki->i', W, F**2))
h1 = np.array([-4,-4,-4,6,6],float)

def Rz(t):
    c,s=np.cos(t),np.sin(t); return np.array([[c,-s,0],[s,c,0],[0,0,1]])
C4 = Rz(np.pi/2)
C3 = np.array([[0,0,1],[1,0,0],[0,1,0]],float)
def key(R): return tuple(np.round(R,8).reshape(-1))
G = {key(np.eye(3)):np.eye(3)}
frontier=[np.eye(3)]
while frontier:
    new=[]
    for A in frontier:
        for g in (C4,C3):
            B = g@A
            if key(B) not in G:
                G[key(B)]=B; new.append(B)
    frontier=new
G = list(G.values()); assert len(G)==24

def U5(R):
    Fp = forb(P@R)
    sw=np.sqrt(W)[:,None]
    Ut,_,_,_ = np.linalg.lstsq(F*sw, Fp*sw, rcond=None)
    return Ut
Us = [U5(R) for R in G]
for U in Us: assert np.allclose(U.T@U, np.eye(5), atol=1e-8)

def cls(R):
    tr = np.trace(R)
    if np.isclose(tr,3): return 'E'
    if np.isclose(tr,0): return 'C3'
    if np.isclose(tr,1): return 'C4'
    ev,evec=np.linalg.eig(R); ax=np.real(evec[:,np.argmin(abs(ev-1))]); ax=ax/np.max(abs(ax))
    return 'C2' if np.sum(np.isclose(abs(ax),0,atol=1e-6))==2 else "C2'"
classes=[cls(R) for R in G]
print(Counter(classes))
irreps = {
 'A1':{'E':1,'C3':1,'C2':1,'C4':1,"C2'":1},
 'A2':{'E':1,'C3':1,'C2':1,'C4':-1,"C2'":-1},
 'E': {'E':2,'C3':-1,'C2':2,'C4':0,"C2'":0},
 'T1':{'E':3,'C3':0,'C2':-1,'C4':1,"C2'":-1},
 'T2':{'E':3,'C3':0,'C2':-1,'C4':-1,"C2'":1}}

NS=10; N=5
states=[sum(1<<i for i in c) for c in itertools.combinations(range(NS),N)]
idx={s:i for i,s in enumerate(states)}; D=len(states)
def sgn(s,i): return (-1)**bin(s & ((1<<i)-1)).count('1')
def ann(i,s):
    if not (s>>i)&1: return None
    return sgn(s,i), s ^ (1<<i)
def cre(i,s):
    if (s>>i)&1: return None
    return sgn(s,i), s | (1<<i)

def onebody(h):
    M=np.zeros((D,D))
    for s in states:
        for a in range(NS):
            for b in range(NS):
                if h[a,b]==0: continue
                r=ann(b,s)
                if r is None: continue
                s1,s1s=r
                r2=cre(a,s1s)
                if r2 is None: continue
                s2,s2s=r2
                M[idx[s2s],idx[s]] += h[a,b]*s1*s2
    return M

cosg = P@P.T
ak={}
for k in (2,4):
    Kk = eval_legendre(k,cosg)
    A=np.zeros((5,5,5,5))
    for a in range(5):
        for c in range(5):
            v1 = F[:,a]*F[:,c]*W
            for b in range(5):
                for d in range(5):
                    A[a,c,b,d]= v1@Kk@(F[:,b]*F[:,d])
    ak[k]=A

Bv=1.0; Cv=3473/800
F4=441*Cv/35*Bv; F2=(441*Bv+5*F4)/9
print("F2,F4 (B units):",F2,F4, "C/B", Cv)
Vso = np.zeros((NS,NS,NS,NS))
for a in range(NS):
  for b in range(NS):
    for c in range(NS):
      for d in range(NS):
        if (a%2)!=(c%2) or (b%2)!=(d%2): continue
        Vso[a,b,c,d]=sum(Fk*ak[k][a//2,c//2,b//2,d//2] for k,Fk in ((2,F2),(4,F4)))
terms=[(a,b,c,d,Vso[a,b,c,d]) for a in range(NS) for b in range(NS) for c in range(NS) for d in range(NS) if abs(Vso[a,b,c,d])>1e-12]
H2=np.zeros((D,D))
for s in states:
    for a,b,c,d,v in terms:
        r=ann(c,s)
        if r is None: continue
        s1,s1s=r
        r=ann(d,s1s)
        if r is None: continue
        s2,s2s=r
        r=cre(b,s2s)
        if r is None: continue
        s3,s3s=r
        r=cre(a,s3s)
        if r is None: continue
        s4,s4s=r
        H2[idx[s4s],idx[s]] += 0.5*v*s1*s2*s3*s4

Sp=np.zeros((NS,NS))
for i in range(5): Sp[2*i,2*i+1]=1
Spop=onebody(Sp); Smop=Spop.T
Szop=onebody(np.diag(np.array([0.5,-0.5]*5)))
S2=Smop@Spop+Szop@Szop+Szop

def fock(U):
    M=np.kron(U,np.eye(2))
    Out=np.zeros((D,D))
    for s in states:
        occ=[i for i in range(NS) if (s>>i)&1]
        for T in states:
            tocc=[i for i in range(NS) if (T>>i)&1]
            Out[idx[T],idx[s]] = np.linalg.det(M[np.ix_(tocc,occ)])
    return Out
Gs=[fock(U) for U in Us]

def hd_op(Dq):
    return onebody(np.diag(np.repeat(h1*Dq,2)))

def levels(Dq):
    H = hd_op(Dq)+H2
    assert np.allclose(H@S2,S2@H,atol=1e-8)
    ev2,vec2=np.linalg.eigh(S2)
    res=[]
    for S in [5/2,3/2,1/2]:
        sel=np.isclose(ev2,S*(S+1))
        PS = vec2[:,sel]@vec2[:,sel].T
        for name,ir in irreps.items():
            Pg=sum(ir[cl]*Gm for cl,Gm in zip(classes,Gs))*(ir['E']/24)
            M=PS@Pg; M=(M+M.T)/2
            ev,vec=np.linalg.eigh(M)
            V=vec[:,ev>0.5]
            if V.shape[1]==0: continue
            Hs=V.T@H@V; Hs=(Hs+Hs.T)/2
            for val in sorted(set(np.round(np.linalg.eigvalsh(Hs),6))):
                res.append((S,name,val))
    return res
