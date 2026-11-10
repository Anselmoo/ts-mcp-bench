mkdir -p /work && cat > /work/d3.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm
from scipy.linalg import expm
from numpy.polynomial.legendre import leggauss

# ---------- parameters (units of B) ----------
B = 1.0
C = 3003/722.0
F4_over_C = 441/35.0
C_ = C
F4 = F4_over_C*C_
F2 = 49*B + 5*F4/9.0          # from B = F2/49 - 5F4/441, C = 35F4/441
F0 = 0.0                      # irrelevant (constant for fixed d3)

l=2; ms=list(range(-2,3))
# spin-orbitals: index = 2*i + s, s=0 (up), 1 (down)
def so_index(i,s): return 2*i+s
# ---------- Slater-type angular integrals via quadrature ----------
xg,wg = leggauss(30)
nphi=48
phis = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(np.arccos(xg), phis, indexing='ij')
W = (wg[:,None]*np.ones((1,nphi)))*(2*np.pi/nphi)
def Y(lm, th, ph):
    return sph_harm(lm[1], lm[0], ph, th)   # scipy: (m, n, azimuth, polar)
Ylm = {m: Y((l,m),TH,PH) for m in ms}
Ylk = {}
for k in (0,2,4):
    for q in range(-k,k+1):
        Ylk[(k,q)] = Y((k,q),TH,PH)
def integ(f): return np.sum(W*f)
# M[k][a,c,q] = ∫ Y_a* Y_c Y_kq* dΩ  for orbital m indices
M={}
for k in (0,2,4):
    arr=np.zeros((5,5,2*k+1),complex)
    for ia,ma in enumerate(ms):
        for ic,mc in enumerate(ms):
            for iq,q in enumerate(range(-k,k+1)):
                arr[ia,ic,iq]=integ(np.conj(Ylm[ma])*Ylm[mc]*np.conj(Ylk[(k,q)]))
    M[k]=arr
def angular(k,a,c,b,d):
    # <a b|P_k|c d> angular part: (4π/(2k+1)) Σ_q M[a,c,q] conj(M[d,b,q])
    s=0
    for iq in range(2*k+1):
        s+= M[k][a,c,iq]*np.conj(M[k][d,b,iq])
    return 4*np.pi/(2*k+1)*s
Fk={0:F0,2:F2,4:F4}
# two-electron integrals over orbitals (complex m basis) -> V[a,b,c,d] for orbitals (5 each)
V=np.zeros((5,5,5,5),complex)
for a in range(5):
  for b in range(5):
    for c in range(5):
      for d in range(5):
        V[a,b,c,d]=sum(Fk[k]*angular(k,a,c,b,d) for k in (0,2,4))
# spin-orbital two-body tensor
n=10
Vso=np.zeros((n,n,n,n),complex)
for i in range(5):
 for j in range(5):
  for k_ in range(5):
   for m_ in range(5):
    for s in range(2):
     for t in range(2):
      # <i_s j_t| V |k_s m_t>  with spin-diagonal
      if True:
        Vso[so_index(i,s),so_index(j,t),so_index(k_,s),so_index(m_,t)] = V[i,j,k_,m_]
# ---------- determinant basis (3 electrons in 10 spin-orbitals) ----------
dets=list(itertools.combinations(range(n),3))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(ops, det):
    """apply list of ops ('c',p) creation or ('a',p) annihilation right-to-left: ops applied in order given (rightmost first)"""
    occ=list(det); sign=1
    for typ,p in ops:
        if typ=='a':
            if p not in occ: return None,0
            pos=occ.index(p); sign*=(-1)**pos; occ.pop(pos)
        else:
            if p in occ: return None,0
            # insert sorted
            pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
    return tuple(occ),sign
def build_H_ee():
    H=np.zeros((len(dets),len(dets)),complex)
    for I,dt in enumerate(dets):
        for a in range(n):
         for b in range(n):
          for c in range(n):
           for d in range(n):
            v=Vso[a,b,c,d]
            if abs(v)<1e-14: continue
            # 1/2 Σ V a†a a†b a_d a_c : apply a_c, then a_d, then a†_b, then a†_a
            new,s=apply_ops([('a',c),('a',d),('c',b),('c',a)],dt)
            if new is None: continue
            # new must be a determinant in basis (sorted tuple)
            H[idx[new],I]+=0.5*v*s
    return H
# one-electron cubic field and check
def l2_Lops():
    Lz=np.diag(ms).astype(complex)
    Lp=np.zeros((5,5),complex)
    for i,m in enumerate(ms):
        if m<2: Lp[i+1,i]=np.sqrt(l*(l+1)-m*(m+1))
    Lm=Lp.conj().T
    Lx=(Lp+Lm)/2; Ly=(Lp-Lm)/(2j)
    return Lx,Ly,Lz
Lx,Ly,Lz=l2_Lops()
def Drot(axis,theta):
    ax=np.array(axis,float); ax/=np.linalg.norm(ax)
    G=ax[0]*Lx+ax[1]*Ly+ax[2]*Lz
    return expm(-1j*theta*G)
def so_big(D5):
    return np.kron(D5,np.eye(2))   # ordering index = 2*i+s matches kron(orb, spin)
def lambda3(g):
    G=np.zeros((len(dets),len(dets)),complex)
    for J,dj in enumerate(dets):
        for I,di in enumerate(dets):
            # <di| Λ3 g |dj>: det of g[di rows, dj cols]
            G[I,J]=np.linalg.det(g[np.ix_(di,dj)])
    return G
# group elements (class representatives)
ops={}
ops['E']=np.eye(5,dtype=complex)
ops['C3']=Drot([1,1,1],2*np.pi/3)
ops['C2z']=Drot([0,0,1],np.pi)
ops['C4z']=Drot([0,0,1],np.pi/2)
ops['C2p']=Drot([1,1,0],np.pi)
classes={'E':[ 'E'],'8C3':['C3'],'3C2':['C2z'],'6C4':['C4z'],'6C2p':['C2p']}
csize={'E':1,'8C3':8,'3C2':3,'6C4':6,'6C2p':6}
chartab={ 'A1':[1,1,1,1,1],'A2':[1,1,1,-1,-1],'E':[2,-1,2,0,0],'T1':[3,0,-1,1,-1],'T2':[3,0,-1,-1,1]}
cls=['E','8C3','3C2','6C4','6C2p']
ref={'E':'E','8C3':'C3','3C2':'C2z','6C4':'C4z','6C2p':'C2p'}
Lam={c:lambda3(so_big(ops[ref[c]])) for c in cls}
# Ms=3/2 & 1/2 index sets
def nup(det): return sum(1 for p in det if p%2==0)
sec32=[i for i,d in enumerate(dets) if nup(d)==3]
sec12=[i for i,d in enumerate(dets) if nup(d)==2]
def decompose(chi):
    out={}
    for name,row in chartab.items():
        s=sum(csize[c]*chi[c]*row[j] for j,c in enumerate(cls))/120.0
        s=np.real_if_close(s)
        out[name]=round(float(np.real(s)),3)
    return {k:v for k,v in out.items() if abs(v)>1e-6}
def char_on(Vecs,c):
    # Vecs: columns orthonormal basis of eigenspace (within full det space)
    return np.trace(Vecs.conj().T @ Lam[c] @ Vecs)

def spectrum(Dq):
    Hcf1=np.zeros((10,10),complex)
    # eg: Y20, (Y22+Y2-2)/√2 ; t2g: others
    P_eg=np.zeros((5,5),complex)
    eg_vecs=[np.eye(5)[ms.index(0)], (np.eye(5)[ms.index(2)]+np.eye(5)[ms.index(-2)])/np.sqrt(2)]
    Peg=sum(np.outer(v,v.conj()) for v in eg_vecs)
    Pt2=np.eye(5)-Peg
    h5=6*Dq*Peg-4*Dq*Pt2
    h10=np.kron(h5,np.eye(2))
    # one-body in determinant basis
    H1=np.zeros((len(dets),len(dets)),complex)
    for I,dt in enumerate(dets):
        for a in range(n):
            for b in range(n):
                v=h10[a,b]
                if abs(v)<1e-14: continue
                new,s=apply_ops([('a',b),('c',a)],dt)
                if new is None: continue
                H1[idx[new],I]+=v*s
    H=build_H_ee()+H1
    return H
Hee=None
EOF
cd /work && python3 -c "
import d3
print('F2,F4',d3.F2,d3.F4)
"