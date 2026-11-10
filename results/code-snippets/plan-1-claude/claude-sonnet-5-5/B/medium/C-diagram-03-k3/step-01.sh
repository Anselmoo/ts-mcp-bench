mkdir -p /w && cd /w && cat > t.py <<'E'
import numpy as np, itertools, sympy as sp
from sympy.physics.wigner import gaunt
from scipy.special import sph_harm
B=806.;C=3570.
F={0:0,2:B+C/7,4:C/35}
def ck(k,m,mp):
    # sqrt(4pi/(2k+1)) int Y*_{2m} Y_{k,m-mp} Y_{2mp}
    q=m-mp
    if abs(q)>k: return 0.
    g=gaunt(2,k,2,-m,q,mp)*(-1)**m  # Y*_{2m}=(-1)^m Y_{2,-m}
    return float(sp.N(g))*np.sqrt(4*np.pi/(2*k+1))
ms=[-2,-1,0,1,2]
c={k:np.array([[ck(k,a,b) for b in ms] for a in ms]) for k in (0,2,4)}
G=np.zeros((5,)*4) # <m1 m2|g|m3 m4>
for i,a in enumerate(ms):
 for j,b in enumerate(ms):
  for k_,cc in enumerate(ms):
   for l,d in enumerate(ms):
    if a+b!=cc+d: continue
    G[i,j,k_,l]=sum(F[k]*c[k][i,k_]*c[k][l,j] for k in (2,4))
# real orbitals as polynomials: z2,xz,yz,x2-y2,xy order -> t2g idx
fs=[lambda x,y,z:2*z*z-x*x-y*y,lambda x,y,z:x*z,lambda x,y,z:y*z,lambda x,y,z:x*x-y*y,lambda x,y,z:x*y]
names=['z2','xz','yz','x2-y2','xy']
rng=np.random.default_rng(1);P=rng.normal(size=(60,3));P/=np.linalg.norm(P,axis=1)[:,None]
th=np.arccos(P[:,2]);ph=np.arctan2(P[:,1],P[:,0])
Y=np.array([sph_harm(m,2,ph,th) for m in ms]).T
def coef(f):
    v=f(*P.T); s=np.linalg.lstsq(Y,v.astype(complex),rcond=None)[0]; return s
U=np.array([coef(f) for f in fs]);
U=np.array([u/np.linalg.norm(u) for u in U])
print(abs(U@U.conj().T-np.eye(5)).max())
Gr=np.einsum('am,bn,ck,dl,mnkl->abcd',U.conj(),U.conj(),U,U,G)
print(abs(Gr.imag).max()); Gr=Gr.real
def rotR(Q):
    # R_ij: f_j(Q^-1 r)= sum_i R_ij f_i(r)
    A=np.array([f(*P.T) for f in fs]).T
    Pr=P@Q  # Q^T r as rows: (Q^-1 r)=Q^T r -> row r@Q
    out=np.array([f(*Pr.T) for f in fs]).T
    return np.linalg.lstsq(A,out,rcond=None)[0]
def rot(axis,ang):
    a=np.array(axis,float);a/=np.linalg.norm(a);K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]])
    return np.eye(3)+np.sin(ang)*K+(1-np.cos(ang))*K@K
ops={'C2':rotR(rot([0,0,1],np.pi)),'C4':rotR(rot([0,0,1],np.pi/2)),'C2p':rotR(rot([1,1,0],np.pi)),'C3':rotR(rot([1,1,1],2*np.pi/3))}
# spin orbitals: index 2*a+s ; dets as sorted tuples
def dets(nu,nd):
    return [tuple(sorted([2*a for a in u]+[2*a+1 for a in d])) for u in itertools.combinations(range(5),nu) for d in itertools.combinations(range(5),nd)]
D=dets(3,2);idx={d:i for i,d in enumerate(D)}
def apply_cre(p,det):
    if p in det: return None
    n=sum(1 for q in det if q<p); return (-1)**n, tuple(sorted(det+(p,)))
def apply_ann(p,det):
    if p not in det: return None
    n=sum(1 for q in det if q<p); return (-1)**n, tuple(q for q in det if q!=p)
def op2(ops_list,det):
    # apply sequence right-to-left list given as [(type,p)...] applied in order
    s=1
    for t,p in ops_list:
        r=(apply_cre if t=='c' else apply_ann)(p,det)
        if r is None: return None
        s*=r[0];det=r[1]
    return s,det
def build(Dq):
    n=len(D);H=np.zeros((n,n));h=np.array([6*Dq,-4*Dq,-4*Dq,6*Dq,-4*Dq])
    for j,d in enumerate(D):
        for p in d: H[j,j]+=h[p//2]
        for a,b,cc,dd in itertools.product(range(5),repeat=4):
            g=Gr[a,b,cc,dd]
            if abs(g)<1e-12: continue
            for s in (0,1):
              for t in (0,1):
                # 1/2 g a+_{a s} a+_{b t} a_{d t} a_{c s}
                r=op2([('a',2*cc+s),('a',2*dd+t),('c',2*b+t),('c',2*a+s)],d)
                if r: H[idx[r[1]],j]+=0.5*g*r[0]
    return H
# S^2 in sector
def S2():
    n=len(D);M=np.zeros((n,n));D2=dets(4,1);i2={d:i for i,d in enumerate(D2)}
    Sp=np.zeros((len(D2),n))
    for j,d in enumerate(D):
        for a in range(5):
            r=op2([('a',2*a+1),('c',2*a)],d)
            if r: Sp[i2[r[1]],j]+=r[0]
    return Sp.T@Sp+0.5*1.5*np.eye(n)*0 + (0.5*1.5)*np.eye(n)  # S-S+ = S^2 - Sz(Sz+1)... 
def opmat(R):
    n=len(D);M=np.zeros((n,n))
    for j,d in enumerate(D):
        for new in D:
            # amplitude = det of R sub (up) * det of R sub (dn)
            u=[p//2 for p in d if p%2==0];dn=[p//2 for p in d if p%2==1]
            nu=[p//2 for p in new if p%2==0];nd=[p//2 for p in new if p%2==1]
            M[idx[new],j]=np.linalg.det(R[np.ix_(nu,u)])*np.linalg.det(R[np.ix_(nd,dn)])
    return M
S2m=S2();OP={k:opmat(R) for k,R in ops.items()}
chars={'A1':(1,1,1,1,1),'A2':(1,1,-1,-1,1),'E':(2,2,0,0,-1),'T1':(3,-1,1,-1,0),'T2':(3,-1,-1,1,0)}
mult={'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
cls=[None,'C2','C4','C2p','C3'];sz=[1,3,6,6,8]
import sys
res=[]
for Dq in np.arange(0,4.01,0.5):
    H=build(Dq*B);
    w,v=np.linalg.eigh(H)
    # check commute
    for k,M in OP.items(): assert abs(M@H-H@M).max()<1e-6*max(1,abs(H).max()),k
    out=[];i=0
    while i<len(w):
        j=i
        while j<len(w) and w[j]-w[i]<1e-6*B*10: j+=1
        V=v[:,i:j];dim=j-i
        S=np.trace(V.T@S2m@V)/dim; Sq=round((-1+np.sqrt(1+4*S))/2*2)/2*1
        S_=(-1+np.sqrt(1+4*S))/2
        ch=[dim]+[np.trace(V.T@OP[k]@V) for k in cls[1:]]
        mu={}
        for ir,x in chars.items():
            m=sum(sz[q]*ch[q]*x[q] for q in range(5))/24
            if abs(m)>0.5: mu[ir]=round(m)
        out.append((w[i],S_,dim,mu)); i=j
    base=out[0][0]
    lv=[]
    for e,S_,dim,mu in out:
        for ir,m in mu.items():
            for _ in range(m): lv.append(((e-base)/B,f"{int(round(2*S_+1))}{ir}"))
    lv.sort(key=lambda x:x[0]); res.append((Dq,lv[:8])); print(Dq,[(round(e,3),t) for e,t in lv[:8]])
import pickle;pickle.dump(res,open('res.pkl','wb'))
E
python3 t.py