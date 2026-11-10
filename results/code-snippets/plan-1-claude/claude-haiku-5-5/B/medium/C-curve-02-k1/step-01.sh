
cat << 'EOF' > /tmp/d3.py
import numpy as np, itertools
from math import pi, sqrt
# quadrature on sphere
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij'); W = (np.outer(wg, np.ones(nphi))*2*pi/nphi)
st = np.sqrt(1-ct**2)
X = st*np.cos(ph); Y = st*np.sin(ph); Z = ct
P = np.stack([X.ravel(),Y.ravel(),Z.ravel()],1); w = W.ravel()
# real d orbitals (angular, normalized): order t2g: xy,yz,xz ; eg: z2, x2-y2
def dfuncs(x,y,z):
    return [sqrt(15/(4*pi))*x*y, sqrt(15/(4*pi))*y*z, sqrt(15/(4*pi))*x*z,
            sqrt(5/(16*pi))*(3*z*z-1), sqrt(15/(16*pi))*(x*x-y*y)]
D = np.array(dfuncs(P[:,0],P[:,1],P[:,2]))  # 5 x npts
# real l=4 harmonics normalized via Gram-Schmidt on monomials (sufficient: spans all l=4 harmonics)
mons=[]
for a in range(5):
    for b in range(5-a):
        for c in range(5-a-b):
            if a+b+c==4: pass
import sympy as sp
xs,ys,zs=sp.symbols('x y z')
r2=xs**2+ys**2+zs**2
# l=4 solid harmonics: generate harmonic polynomials of degree 4 by projecting monomials
monos=[xs**a*ys**b*zs**(4-a-b) for a in range(5) for b in range(5-a)]
# harmonic projection: Laplacian kernel
L=[]
Lmat=[]
def lap(p): return sp.diff(p,xs,2)+sp.diff(p,ys,2)+sp.diff(p,zs,2)
# basis of harmonic polynomials of degree 4: null space of Laplacian on degree-4 monomials
vecs=sp.Matrix([[sp.Poly(lap(m),xs,ys,zs).coeff_monomial(t) for m in monos] for t in [xs**a*ys**b*zs**(2-a-b) for a in range(3) for b in range(3-a)]])
ns=vecs.nullspace()
H4=[sum(c*m for c,m in zip(v,monos)) for v in ns]
assert len(H4)==9
Y4=[]
f4=sp.lambdify((xs,ys,zs),0)
arrs=[]
for h in H4:
    fn=sp.lambdify((xs,ys,zs),h,'numpy')
    arrs.append(np.array(fn(P[:,0],P[:,1],P[:,2]),dtype=float)*np.ones(len(P)))
A4=np.array(arrs)
# orthonormalize on sphere
G4=(A4*w)@A4.T
Lc=np.linalg.cholesky(np.linalg.inv(G4))
Y4=Lc.T@A4   # orthonormal wrt sum w
Y2=D*1.0
# check orthonormality
print(np.allclose((Y2*w)@Y2.T,np.eye(5)), np.allclose((Y4*w)@Y4.T,np.eye(9)))
# Racah: angular matrix elements
def Xk(Ykq, a, c): return np.sum(w*D[a]*D[c]*Ykq)
Ang={}
Vang=np.zeros((5,5,5,5))  # coefficient for k=2
V4=np.zeros((5,5,5,5))
for a,b,c,d in itertools.product(range(5),repeat=4):
    s2=sum(np.sum(w*D[a]*D[c]*Y2[q])*np.sum(w*D[b]*D[d]*Y2[q]) for q in range(5))
    s4=sum(np.sum(w*D[a]*D[c]*Y4[q])*np.sum(w*D[b]*D[d]*Y4[q]) for q in range(9))
    Vang[a,b,c,d]=4*pi/5*s2
    V4[a,b,c,d]=4*pi/9*s4
# Slater: F2 = 49B+7C, F4 = 63C/5
def run(x, B=1.0, C=3003/722):
    F2=49*B+7*C; F4=63*C/5
    V=F2*Vang+F4*V4   # <ab|1/r12|cd> spatial orbital indices
    # spin-orbital basis: index=2*orb+spin
    h1=np.zeros((10,10))
    diag=[-4*x,-4*x,-4*x,6*x,6*x]
    for o in range(5):
        for s in range(2): h1[2*o+s,2*o+s]=diag[o]
    n=10
    Vso=np.zeros((n,n,n,n))
    for i,j,k,l in itertools.product(range(n),repeat=4):
        if (i%2)!=(l%2) or (j%2)!=(k%2): continue
        Vso[i,j,k,l]=V[i//2,j//2,l//2,k//2]  # <ij|V|kl> with orbitals: a=i,c=l? careful
    return h1,Vso
EOF
echo ok