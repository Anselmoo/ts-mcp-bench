
cd /tmp/tsbench-run-s2tzcfyu && cat << 'EOF' > d3.py
import numpy as np, itertools, sympy as sp
from math import pi, sqrt
nt, nphi = 30, 60
xg, wg = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij'); W = (np.outer(wg, np.ones(nphi))*2*pi/nphi)
st = np.sqrt(1-ct**2)
P = np.stack([(st*np.cos(ph)).ravel(),(st*np.sin(ph)).ravel(),ct.ravel()],1); w = W.ravel()
x,y,z = P[:,0],P[:,1],P[:,2]
def dorb(x,y,z):
    return np.array([sqrt(15/(4*pi))*x*y, sqrt(15/(4*pi))*y*z, sqrt(15/(4*pi))*x*z,
              sqrt(5/(16*pi))*(3*z*z-1), sqrt(15/(16*pi))*(x*x-y*y)])
D = dorb(x,y,z)
xs,ys,zs=sp.symbols('x y z')
monos=[xs**a*ys**b*zs**(4-a-b) for a in range(5) for b in range(5-a)]
def lap(p): return sp.diff(p,xs,2)+sp.diff(p,ys,2)+sp.diff(p,zs,2)
targets=[xs**a*ys**b*zs**(2-a-b) for a in range(3) for b in range(3-a)]
M=sp.Matrix([[sp.Poly(lap(m),xs,ys,zs).coeff_monomial(t) for m in monos] for t in targets])
ns=M.nullspace()
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
# C4 about z: (x,y,z)->(-y,x,z)
Dr=dorb(-y,x,z)
Rorb=(D*w)@Dr.T   # Rorb[i,j]=int phi_i(x) phi_j(Rx)
assert np.allclose(Rorb@Rorb.T,np.eye(5))
def apply_c(det, i, dag):
    if dag:
        if i in det: return None
        pos=sum(1 for d in det if d<i); nd=tuple(sorted(det+(i,)))
    else:
        if i not in det: return None
        pos=det.index(i); nd=tuple(d for d in det if d!=i)
    return (-1)**pos, nd
def sector_basis(nup, ndn):
    ups=[2*o for o in range(5)]; dns=[2*o+1 for o in range(5)]
    B=[]
    for a in itertools.combinations(ups,nup):
        for b in itertools.combinations(dns,ndn):
            B.append(tuple(sorted(a+b)))
    return B
def run(x_dq, B=1.0, C=3003/722):
    F2=49*B+7*C; F4=63*C/5
    V=F2*Vang+F4*V4
    h1=np.zeros(10)
    diag=[-4*x_dq]*3+[6*x_dq]*2
    for o in range(5):
        for s in range(2): h1[2*o+s]=diag[o]
    terms=[]
    for i,j,k,l in itertools.product(range(10),repeat=4):
        if (i%2)!=(k%2) or (j%2)!=(l%2): continue
        val=V[i//2,j//2,k//2,l//2]
        if abs(val)>1e-12: terms.append((i,j,k,l,0.5*val))
    def mat(basis):
        idx={d:n for n,d in enumerate(basis)}
        N=len(basis); H=np.zeros((N,N))
        for n,det in enumerate(basis):
            for i in det: H[n,n]+=h1[i]
            for (i,j,k,l,val) in terms:
                r=apply_c(det,k,False)
                if r is None: continue
                s1,d1=r; r=apply_c(d1,l,False)
                if r is None: continue
                s2,d2=r; r=apply_c(d2,j,True)
                if r is None: continue
                s3,d3=r; r=apply_c(d3,i,True)
                if r is None: continue
                s4,d4=r
                if d4 in idx: H[idx[d4],n]+=val*s1*s2*s3*s4
        return H
    def rot(basis):
        N=len(basis); G=np.zeros((N,N))
        Rso=np.zeros((10,10))
        for o in range(5):
            for o2 in range(5):
                for s in range(2): Rso[2*o+s,2*o2+s]=Rorb[o,o2]
        for n,det in enumerate(basis):
            for m,nd in enumerate(basis):
                G[m,n]=np.linalg.det(Rso[np.ix_(list(nd),list(det))])
        return G
    out={}
    # quartets M_S=3/2
    bq=sector_basis(3,0); Hq=mat(bq); Gq=rot(bq)
    eq,vq=np.linalg.eigh(Hq)
    # doublets M_S=1/2 : nup=2, ndn=1
    bd=sector_basis(2,1); Hd=mat(bd); Gd=rot(bd)
    ed,vd=np.linalg.eigh(Hd)
    # check commuting
    assert np.allclose(Hd@Gd,Gd@Hd,atol=1e-8)
    terms_out=[]
    # quartets: group by energy, character of C4 in each cluster
    def clusters(e):
        groups=[]; 
        for k,val in enumerate(e):
            if groups and abs(val-groups[-1][0][1])<1e-7: groups[-1].append((k,val))
            else: groups.append([(k,val)])
        return groups
    qres=[]
    for g in clusters(eq):
        ks=[k for k,_ in g]; V_=vq[:,ks]
        chi=np.trace(V_.T@Gq@V_)
        qres.append((g[0][1], len(ks), round(chi.real,3)))
    # doublets: remove quartet eigenvalues from M_S=1/2 spectrum
    # C4 on full M_S=1/2 space, decompose by eigenvalue; quartet components inside M_S=1/2 space also present
    dres=[]
    for g in clusters(ed):
        ks=[k for k,_ in g]; V_=vd[:,ks]
        chi=np.trace(V_.T@Gd@V_)
        dres.append((g[0][1], len(ks), round(chi.real,3)))
    # remove quartet energies (multiplicity from quartets' M_S=1/2 components)
    return qres, dres
if __name__=='__main__':
    import sys
    for xd in [1.0,2.2,3.5]:
        q,dd=run(xd)
        print('Dq/B',xd)
        print(' quartets:',[(round(e,4),n,c) for e,n,c in q])
        print(' M_S=1/2 :',[(round(e,4),n,c) for e,n,c in dd])
EOF
python3 d3.py