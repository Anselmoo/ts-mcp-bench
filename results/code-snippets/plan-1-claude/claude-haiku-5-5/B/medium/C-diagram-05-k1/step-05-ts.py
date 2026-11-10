import numpy as np, itertools, math
from sympy.physics.wigner import wigner_3j

l = 2
ms = [-2,-1,0,1,2]
NSO = 10  # p = 2*(m+2) + s, s=0 up, s=1 down
def popc(x): return bin(x).count('1')
def ann(p,b):
    if not (b>>p)&1: return 0,None
    return (-1)**popc(b & ((1<<p)-1)), b ^ (1<<p)
def cre(p,b):
    if (b>>p)&1: return 0,None
    return (-1)**popc(b & ((1<<p)-1)), b | (1<<p)

basis = sorted([sum(1<<i for i in c) for c in itertools.combinations(range(NSO),7)])
idx = {b:i for i,b in enumerate(basis)}
N = len(basis)

def angular():
    def redC(k):
        return (-1)**l*(2*l+1)*float(wigner_3j(l,k,l,0,0,0))
    def Cme(k,m,q,mp):
        w = float(wigner_3j(l,k,l,-m,q,mp))
        return (-1)**(l-m)*w*redC(k)
    g = {}
    for k in (0,2,4):
        arr = np.zeros((5,5,5,5))
        for a,ma in enumerate(ms):
            for c,mc in enumerate(ms):
                for b,mb in enumerate(ms):
                    for d,md in enumerate(ms):
                        s=0.0
                        for q in range(-k,k+1):
                            if ma-mc!=q or mb-md!=-q: continue
                            s += (-1)**q * Cme(k,ma,q,mc)*Cme(k,mb,-q,md)
                        arr[a,b,c,d]=s
        g[k]=arr
    return g

def op_two_body(F2,F4):
    g = angular()
    Vo = F2*g[2] + F4*g[4]
    terms=[]
    for a in range(NSO):
        for b in range(NSO):
            for c in range(NSO):
                for d in range(NSO):
                    ma,sa = divmod(a,2); mb,sb = divmod(b,2)
                    mc,sc = divmod(c,2); md,sd = divmod(d,2)
                    if sa!=sc or sb!=sd: continue
                    v = Vo[ma,mb,mc,md]
                    if abs(v)<1e-12: continue
                    terms.append((a,b,c,d,v))
    H = np.zeros((N,N))
    for j,bj in enumerate(basis):
        for (a,b,c,d,v) in terms:
            s1,b1 = ann(c,bj)
            if s1==0: continue
            s2,b2 = ann(d,b1)
            if s2==0: continue
            s3,b3 = cre(b,b2)
            if s3==0: continue
            s4,b4 = cre(a,b3)
            if s4==0: continue
            H[idx[b4],j] += 0.5*v*s1*s2*s3*s4
    return H, g

def so_from_orb(h5):
    h = np.zeros((NSO,NSO),dtype=complex)
    for mi in range(5):
        for mj in range(5):
            for s in range(2):
                h[2*mi+s, 2*mj+s] = h5[mi,mj]
    return h

def op_one_body(h):
    M = np.zeros((N,N),dtype=complex)
    for j,bj in enumerate(basis):
        for p in range(NSO):
            for q in range(NSO):
                if abs(h[p,q])<1e-14: continue
                s1,b1 = ann(q,bj)
                if s1==0: continue
                s2,b2 = cre(p,b1)
                if s2==0: continue
                M[idx[b2],j] += h[p,q]*s1*s2
    return M

Peg = np.zeros((5,5),dtype=complex)
Peg[2,2]=1.0
v = np.zeros(5,dtype=complex); v[0]=1/np.sqrt(2); v[4]=1/np.sqrt(2)
Peg += np.outer(v,v.conj())
Pt2 = np.eye(5)-Peg
def Hcf_orb(Dq):
    return -4*Dq*Pt2 + 6*Dq*Peg

Jz = np.diag(ms).astype(complex)
Jp = np.zeros((5,5),dtype=complex)
for mi,m in enumerate(ms):
    if m<2: Jp[mi+1,mi]=np.sqrt(l*(l+1)-m*(m+1))
Jm = Jp.conj().T
Jx = (Jp+Jm)/2; Jy=(Jp-Jm)/(2j)
def Drot(axis,theta):
    n = np.array(axis,dtype=float); n/=np.linalg.norm(n)
    G = n[0]*Jx+n[1]*Jy+n[2]*Jz
    w,V = np.linalg.eigh(G)
    return V@np.diag(np.exp(-1j*theta*w))@V.conj().T
def Umany(D5):
    Dfull = np.kron(D5, np.eye(2))
    occ = [[p for p in range(NSO) if (b>>p)&1] for b in basis]
    U = np.zeros((N,N),dtype=complex)
    for j in range(N):
        for i in range(N):
            U[i,j] = np.linalg.det(Dfull[np.ix_(occ[i],occ[j])])
    return U

ROT = [ (1,[0,0,1],0.0), (8,[1,1,1],2*np.pi/3), (3,[0,0,1],np.pi), (6,[0,0,1],np.pi/2), (6,[1,1,0],np.pi) ]
CLS_SIZE = np.array([1,8,3,6,6])
CHAR = {'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
def decompose(chi):
    out={}
    for k,c in CHAR.items():
        n = np.sum(CLS_SIZE*np.array(chi)*np.array(c))/24.0
        n = int(round(n.real))
        if n: out[k]=n
    return out
