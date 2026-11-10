cd ~ 2>/dev/null; python3 - << 'EOF'
import numpy as np
from scipy.special import eval_legendre
from scipy.optimize import least_squares
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
def levels(p):
    Dq,B,C=p
    e=np.linalg.eigvalsh(build(Dq,B,C)); e=e-e[0]
    g=[]
    for x in e:
        if g and abs(x-g[-1][-1])<1e-3: g[-1].append(x)
        else: g.append([x])
    return [(len(a), np.mean(a)) for a in g]
obs=np.array([15490,24500,32330.])
# assignment A: T2=nu1, T1P=nu2, A2=nu3
def resA(p):
    lv=levels(p)[1:]
    return np.array([lv[0][1],lv[1][1],lv[2][1]])-obs
# assignment B: T2=nu1, A2=nu2, T1P=nu3
def resB(p):
    lv=levels(p)[1:]
    return np.array([lv[0][1],lv[2][1],lv[1][1]])-obs
for name,fn in [('A',resA),('B',resB)]:
    for x0 in [(1549,800,3500),(1549,1000,4000),(1600,600,3000),(1500,900,4000)]:
        try:
            s=least_squares(lambda q: fn([q[0],q[1],q[2]]) , x0, bounds=([500,100,300],[5000,2000,8000]), xtol=1e-12, ftol=1e-12)
            print(name, np.round(s.x,1), np.round(s.fun,2), 'C/B=%.3f'%(s.x[2]/s.x[1]))
        except Exception as ex: print(name, ex)
EOF