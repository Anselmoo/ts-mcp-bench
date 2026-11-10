import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import brentq
nt, nphi = 40, 80
x, w = np.polynomial.legendre.leggauss(nt)
phis = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(np.arccos(x), phis, indexing='ij')
W = np.outer(w, np.full(nphi, 2*np.pi/nphi))
def Y(l,m): return sph_harm_y(l, m, TH, PH)
ms = list(range(-2,3))
orb = [(m,s) for s in (1,-1) for m in ms]   # 0-4 spin up, 5-9 spin down
def ang(k,q,a,c): return np.sum(W*np.conj(Y(2,a))*np.conj(Y(k,q))*Y(2,c))
def ang2(k,q,b,d): return np.sum(W*np.conj(Y(2,b))*Y(k,q)*Y(2,d))
def build_V(F):
    V=np.zeros((10,10,10,10),complex)
    for i,(m1,s1) in enumerate(orb):
      for j,(m2,s2) in enumerate(orb):
        for kk,(m3,s3) in enumerate(orb):
          for l,(m4,s4) in enumerate(orb):
            if s1!=s3 or s2!=s4: continue
            val=0
            for k in (0,2,4):
                for q in range(-k,k+1):
                    val+= 4*np.pi/(2*k+1)*F[k]*ang(k,q,m1,m3)*ang2(k,q,m2,m4)
            V[i,j,kk,l]=val
    return V
def fock_states(nup,ndn):
    ups=[i for i in range(5)]; dns=[i+5 for i in range(5)]
    st=[]
    for U in itertools.combinations(ups,nup):
        for D in itertools.combinations(dns,ndn):
            st.append(tuple(sorted(U+D)))
    return st
def apply_ops(state, i,j,l,k):
    # c+_i c+_j c_l c_k acting on |state> (sorted tuple, ordered product)
    occ=list(state); sign=1
    # annihilate k
    def ann(p):
        nonlocal occ,sign
        if p not in occ: return False
        pos=occ.index(p); sign*= (-1)**pos; occ.pop(pos); return True
    def cre(p):
        nonlocal occ,sign
        if p in occ: return False
        import bisect
        pos=bisect.bisect(occ,p); sign*=(-1)**pos; occ.insert(pos,p); return True
    if not ann(k): return None
    if not ann(l): return None
    if not cre(j): return None
    if not cre(i): return None
    return tuple(occ), sign
def hamiltonian(F, Dq, Vee):
    basis=fock_states(5,2); idx={s:n for n,s in enumerate(basis)}
    N=len(basis); H=np.zeros((N,N),complex)
    # one-body cubic field: H1 = -10Dq * P_e (plus constant), P_e on m=0 and (m=2 + m=-2)/sqrt2
    e1=np.zeros(5); e1[2]=1           # m=0
    e2=np.zeros(5); e2[0]=1/np.sqrt(2); e2[4]=1/np.sqrt(2)  # m=-2,+2
    Pe=np.outer(e1,e1)+np.outer(e2,e2)
    h=np.zeros((10,10)); 
    h[:5,:5]=-10*Dq*Pe; h[5:,5:]=-10*Dq*Pe
    for n,s in enumerate(basis):
        for i in range(10):
          for j in range(10):
            if abs(h[i,j])>1e-14:
                r=apply_ops(s,i,j,j,j) if False else None
        # one-body: c+_i c_j
        for a in range(10):
          for b in range(10):
            if abs(h[a,b])<1e-14: continue
            occ=list(s); sign=1
            if b not in occ: continue
            pos=occ.index(b); sign*=(-1)**pos; occ.pop(pos)
            import bisect
            if a in occ: continue
            pos=bisect.bisect(occ,a); sign*=(-1)**pos; occ.insert(pos,a)
            H[idx[tuple(occ)],n]+= sign*h[a,b]
        for i in range(10):
          for j in range(10):
            for k in range(10):
              for l in range(10):
                if abs(Vee[i,j,k,l])<1e-14: continue
                r=apply_ops(s,i,j,l,k)
                if r is None: continue
                st,sg=r
                H[idx[st],n]+= 0.5*sg*Vee[i,j,k,l]
    return H, basis
if __name__=="__main__":
    F={0:0.0,2:1.0,4:0.625}
    Vee=build_V(F)
    for Dq in [0.0, 0.0]:
        H,b=hamiltonian(F,Dq,Vee)
        ev=np.linalg.eigvalsh(H.real)
        print(np.round(ev,4))
    np.save('Vee.npy',Vee)
