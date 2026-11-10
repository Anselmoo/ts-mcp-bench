import numpy as np
from scipy.special import eval_legendre
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi; wphi = 2*np.pi/nphi
ct = np.repeat(xg, nphi); wts = np.repeat(wg, nphi)*wphi
ph = np.tile(phis, nt); st = np.sqrt(1-ct**2)
X, Y, Z = st*np.cos(ph), st*np.sin(ph), ct
funcs = [X*Y, Y*Z, X*Z, X**2-Y**2, 3*Z**2-1]
F = []
for f in funcs:
    n = np.sum(wts*f*f); F.append(f/np.sqrt(n))
F = np.array(F)
cosg = X[:,None]*X[None,:]+Y[:,None]*Y[None,:]+Z[:,None]*Z[None,:]
W = wts
Ak = {}
for k in (0,2,4):
    Pk = eval_legendre(k, cosg)
    G1 = np.einsum('p,ap,cp->pac', W, F, F)
    G2 = np.einsum('q,bq,dq->qbd', W, F, F)
    Ak[k] = np.einsum('pac,pq,qbd->acbd', G1, Pk, G2)
t2g = [0,1,2]
h = np.diag([-4.0 if i in t2g else 6.0 for i in range(5)])
dets = [(i,j) for i in range(5) for j in range(i+1,5)]
def build(Dq, B, C):
    F4 = 441*C/35.0
    F2 = (441*B + 5*F4)/9.0
    Fk = {0:0.0, 2:F2, 4:F4}
    V = sum(Fk[k]*Ak[k] for k in (0,2,4))
    n=len(dets); H=np.zeros((n,n))
    for I,(i,j) in enumerate(dets):
        for J,(k,l) in enumerate(dets):
            val = 0.0
            if j==l: val += Dq*h[i,k]
            if i==k: val += Dq*h[j,l]
            val += V[i,k,j,l] - V[i,l,j,k]
            H[I,J]=val
    return H
def levels(Dq,B,C):
    return np.linalg.eigvalsh(build(Dq,B,C))
if __name__=='__main__':
    print(np.round(levels(0,1,4),4))
    print(np.round(levels(1,0,0),4))
