import numpy as np
from scipy.optimize import fsolve
from scipy.special import eval_legendre
# quadrature
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi; wphi = 2*np.pi/nphi
ct = np.repeat(xg, nphi); wts = np.repeat(wg, nphi)*wphi
ph = np.tile(phis, nt); st = np.sqrt(1-ct**2)
X, Y, Z = st*np.cos(ph), st*np.sin(ph), ct
funcs = [X*Y, Y*Z, X*Z, X**2-Y**2, 3*Z**2-1]  # xy,yz,xz,x2-y2,z2
F = []
for f in funcs:
    n = np.sum(wts*f*f); F.append(f/np.sqrt(n))
F = np.array(F)  # 5 x N
cosg = X[:,None]*X[None,:]+Y[:,None]*Y[None,:]+Z[:,None]*Z[None,:]
W = wts
# A^k[a,c,b,d] = int int f_a(1) f_c(1) f_b(2) f_d(2) P_k(12)
Ak = {}
for k in (0,2,4):
    Pk = eval_legendre(k, cosg)
    G1 = np.einsum('p,ap,cp->pac', W, F, F)  # weight*f_a*f_c at point 1
    G2 = np.einsum('q,bq,dq->qbd', W, F, F)
    Ak[k] = np.einsum('pac,pq,qbd->acbd', G1, Pk, G2)
names = ['xy','yz','xz','x2y2','z2']
t2g = [0,1,2]; eg=[3,4]
h = np.diag([-4.0 if i in t2g else 6.0 for i in range(5)])  # in units of Dq
# determinants: pairs of orbitals (both alpha)
dets = [(i,j) for i in range(5) for j in range(i+1,5)]
def build(Dq, B, C):
    F4 = 441*C/35.0
    F2 = (441*B + 5*F4)/9.0
    Fk = {0:0.0, 2:F2, 4:F4}
    V = sum(Fk[k]*Ak[k] for k in (0,2,4))  # V[a,c,b,d] = <ab|1/r|cd>
    n=len(dets); H=np.zeros((n,n))
    for I,(i,j) in enumerate(dets):
        for J,(k,l) in enumerate(dets):
            val = 0.0
            # one-body
            if j==l: val += Dq*h[i,k]
            if i==k: val += Dq*h[j,l]
            # two-body: <ij|V|kl> - <ij|V|lk>
            val += V[i,k,j,l] - V[i,l,j,k]
            H[I,J]=val
    return H
def levels(Dq,B,C):
    return np.linalg.eigvalsh(build(Dq,B,C))
if __name__=='__main__':
    print(np.round(levels(0,1,4),4))
    print(np.round(levels(1,0,0),4))
