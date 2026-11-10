import numpy as np, itertools, sympy as sp
from math import pi, sqrt
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij'); W = (np.outer(wg, np.ones(nphi))*2*pi/nphi)
st = np.sqrt(1-ct**2)
P = np.stack([(st*np.cos(ph)).ravel(),(st*np.sin(ph)).ravel(),ct.ravel()],1); w = W.ravel()
x,y,z = P[:,0],P[:,1],P[:,2]
D = np.array([sqrt(15/(4*pi))*x*y, sqrt(15/(4*pi))*y*z, sqrt(15/(4*pi))*x*z,
              sqrt(5/(16*pi))*(3*z*z-1), sqrt(15/(16*pi))*(x*x-y*y)])
xs,ys,zs=sp.symbols('x y z')
monos=[xs**a*ys**b*zs**(4-a-b) for a in range(5) for b in range(5-a)]
def lap(p): return sp.diff(p,xs,2)+sp.diff(p,ys,2)+sp.diff(p,zs,2)
rows=[]
targets=[xs**a*ys**b*zs**(2-a-b) for a in range(3) for b in range(3-a)]
M=sp.Matrix([[sp.Poly(lap(m),xs,ys,zs).coeff_monomial(t) for m in monos] for t in targets])
ns=M.nullspace()
A4=np.array([[float(sp.lambdify((xs,ys,zs),sum(c*m for c,m in zip(v,monos)),'numpy')(*P.T)) for v in ns]]).reshape(len(ns),-1) if False else None
A4=[]
for v in ns:
    h=sum(c*m for c,m in zip(v,monos))
    f=sp.lambdify((xs,ys,zs),h,'numpy')
    A4.append(np.asarray(f(x,y,z),dtype=float)*np.ones_like(x))
A4=np.array(A4)
G4=(A4*w)@A4.T
Y4=np.linalg.cholesky(np.linalg.inv(G4)).T@A4
Y2=D
assert np.allclose((Y2*w)@Y2.T,np.eye(5)) and np.allclose((Y4*w)@Y4.T,np.eye(9))
Vang=np.zeros((5,)*4); V4=np.zeros((5,)*4)
for a,b,c,d in itertools.product(range(5),repeat=4):
    Vang[a,b,c,d]=4*pi/5*sum(np.sum(w*D[a]*D[c]*Y2[q])*np.sum(w*D[b]*D[d]*Y2[q]) for q in range(5))
    V4[a,b,c,d]=4*pi/9*sum(np.sum(w*D[a]*D[c]*Y4[q])*np.sum(w*D[b]*D[d]*Y4[q]) for q in range(9))
# rotation C4 about z: (x,y,z)->(-y,x,z)
Pr = np.stack([-y,x,z],1)
Dr = np.array([sqrt(15/(4*pi))*Pr[:,0]*Pr[:,1], sqrt(15/(4*pi))*Pr[:,1]*Pr[:,2], sqrt(15/(4*pi))*Pr[:,0]*Pr[:,2],
              sqrt(5/(16*pi))*(3*Pr[:,2]**2-1), sqrt(15/(16*pi))*(Pr[:,0]**2-Pr[:,1]**2)])
Rm = (D*w)@Dr.T   # Rm[i,j] = int phi_i(x) phi_j(Rx)
R4 = np.eye(5)
def dets(n_el, nsp=10):
    return list(itertools.combinations(range(nsp), n_el))
def apply_c(det, i, dag):
    # returns (sign, newdet) or None
    if dag:
        if i in det: return None
        pos=sum(1 for d in det if d<i)
        nd=tuple(sorted(det+(i,)))
    else:
        if i not in det: return None
        pos=det.index(i)
        nd=tuple(d for d in det if d!=i)
    return (-1)**pos, nd
def build(x_dq, B=1.0, C=3003/722):
    F2=49*B+7*C; F4=63*C/5
    V=F2*Vang+F4*V4
    h1=np.zeros(10)
    diag=[-4*x_dq]*3+[6*x_dq]*2
    for o in range(5):
        for s in range(2): h1[2*o+s]=diag[o]
    # two-body list
    terms=[]
    for i,j,k,l in itertools.product(range(10),repeat=4):
        if (i%2)!=(k%2) or (j%2)!=(l%2): continue
        val=V[i//2,j//2,k//2,l//2]
        if abs(val)>1e-12: terms.append((i,j,k,l,0.5*val))
    return h1, terms
def hamiltonian(dl, terms, h1):
    out={}
    for n_up in [3,2]:
        pass
def matrix_sector(basis, h1, terms, x_dq):
    idx={d:n for n,d in enumerate(basis)}
    N=len(basis); H=np.zeros((N,N))
    for n,det in enumerate(basis):
        for i in det: H[n,n]+=h1[i]
        for (i,j,k,l,val) in terms:
            # a†_i a†_j a_l a_k |det>
            r=apply_c(det,k,False)
            if r is None: continue
            s1,d1=r
            r=apply_c(d1,l,False)
            if r is None: continue
            s2,d2=r
            r=apply_c(d2,j,True)
            if r is None: continue
            s3,d3=r
            r=apply_c(d3,i,True)
            if r is None: continue
            s4,d4=r
            if d4 in idx:
                H[idx[d4],n]+=val*s1*s2*s3*s4
    return H
def rot_matrix_so(basis, Rorb):
    # Lambda^3 of spin-diagonal single-particle matrix Rorb (10x10), restricted to basis
    idx={d:n for n,d in enumerate(basis)}
    N=len(basis); G=np.zeros((N,N))
    for n,det in enumerate(basis):   # column = input det
        for m,nd in enumerate(basis):
            G[m,n]=np.linalg.det(Rorb[np.ix_(list(nd),list(det))])
    return G
def analyze(x_dq):
    h1,terms=build(x_dq)
    Rso=np.zeros((10,10))
    for o in range(5):
        for o2 in range(5):
            for s in range(2): Rso[2*o+s,2*o2+s]=Rm[o,o2]  # placeholder
    return None
