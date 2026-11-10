import numpy as np, itertools
from scipy.special import eval_legendre
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = (np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)).ravel()
st = np.sqrt(1-ct**2)
X=(st*np.cos(ph)).ravel(); Y=(st*np.sin(ph)).ravel(); Z=ct.ravel()
funcs=[X*Y,Y*Z,Z*X,X**2-Y**2,3*Z**2-(X**2+Y**2)]
orbs=np.array([f/np.sqrt(np.sum(W*f*f)) for f in funcs])
cg=np.clip(np.outer(X,X)+np.outer(Y,Y)+np.outer(Z,Z),-1,1)
rho=np.einsum('ip,kp->ikp',orbs,orbs)
def ang(k):
    P=eval_legendre(k,cg)
    R=np.einsum('ikp,pq,q->ikq',rho,P,W)
    return np.einsum('ikq,jlq->ikjl',R,rho)
A0,A2,A4=ang(0),ang(2),ang(4)
print("a0 check", A0[0,0,0,0], A0[3,3,3,3], "a2 yz", A2[0,0,0,0])
n=10; dim=2**n
CR=[]
for p in range(n):
    M=np.zeros((dim,dim))
    for s in range(dim):
        if not (s>>p)&1:
            M[s|(1<<p),s]=(-1)**bin(s&((1<<p)-1)).count('1')
    CR.append(M)
AN=[m.T.copy() for m in CR]
Nop=sum(CR[p]@AN[p] for p in range(n)).diagonal()
idx=np.where(np.round(Nop)==3)[0]
def spectrum(Dq,B,C):
    F2=49*B+7*C; F4=63*C/5
    Vt=F2*A2+F4*A4
    eps=[-4*Dq]*3+[6*Dq]*2
    Hf=np.zeros((dim,dim))
    for o in range(5):
        for s in range(2):
            p=2*o+s; Hf+=eps[o]*CR[p]@AN[p]
    for i,j,k,l in itertools.product(range(5),repeat=4):
        v=Vt[i,j,k,l]
        if abs(v)<1e-13: continue
        for s1 in range(2):
            for s2 in range(2):
                p=2*i+s1; q=2*k+s2; r=2*j+s1; s=2*l+s2
                Hf+=0.5*v*CR[p]@CR[q]@AN[s]@AN[r]
    H=Hf[np.ix_(idx,idx)]
    Sp=sum(CR[2*o]@AN[2*o+1] for o in range(5))
    Sz=0.5*sum(CR[2*o]@AN[2*o]-CR[2*o+1]@AN[2*o+1] for o in range(5))
    S2=(Sp.T@Sp+Sz@Sz-Sz)  # S-S+ = S^2 - Sz^2 - Sz ; S+S- = S^2-Sz^2+Sz -> use S^2 = S-S+ + Sz^2 + Sz
    S2=(Sp.T@Sp+Sz@Sz+Sz)[np.ix_(idx,idx)]
    E,V=np.linalg.eigh(H)
    return [(round(e,1), round(float(v@S2@v),2)) for e,v in zip(E,V.T)]
if __name__=="__main__":
    sp=spectrum(1000.,600.,2400.)
    for x in sp: print(x)
