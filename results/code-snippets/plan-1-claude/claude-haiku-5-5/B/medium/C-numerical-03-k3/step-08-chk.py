import numpy as np
from scipy.special import eval_legendre
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi; wphi = 2*np.pi/nphi
ct = np.repeat(xg, nphi); wts = np.repeat(wg, nphi)*wphi
ph = np.tile(phis, nt); st = np.sqrt(1-ct**2)
X, Y, Z = st*np.cos(ph), st*np.sin(ph), ct
funcs = [X*Y, Y*Z, X*Z, X**2-Y**2, 3*Z**2-1]
F = np.array([f/np.sqrt(np.sum(wts*f*f)) for f in funcs])
cosg = X[:,None]*X[None,:]+Y[:,None]*Y[None,:]+Z[:,None]*Z[None,:]
W = wts
Ak = {}
for k in (2,4):
    Pk = eval_legendre(k, cosg)
    G1 = np.einsum('p,ap,cp->pac', W, F, F)
    G2 = np.einsum('q,bq,dq->qbd', W, F, F)
    Ak[k] = np.einsum('pac,pq,qbd->acbd', G1, Pk, G2)
h = np.diag([-4.0,-4.0,-4.0,6.0,6.0])
dets = [(i,j) for i in range(5) for j in range(i+1,5)]
def build(Dq, B, C):
    F4 = 441*C/35.0; F2 = (441*B + 5*F4)/9.0
    V = F2*Ak[2] + F4*Ak[4]
    H=np.zeros((10,10))
    for I,(i,j) in enumerate(dets):
        for J,(k,l) in enumerate(dets):
            val = 0.0
            if j==l: val += Dq*h[i,k]
            if i==k: val += Dq*h[j,l]
            val += V[i,k,j,l] - V[i,l,j,k]
            H[I,J]=val
    return H
def bands(Dq,B,C):
    e=np.linalg.eigvalsh(build(Dq,B,C))
    g=e[0]
    # identify classes: ground triplet (3), T2 (3), A2 (1), T1P (3)
    out={}
    vals=sorted(set(np.round(e,6)))
    return e-g
