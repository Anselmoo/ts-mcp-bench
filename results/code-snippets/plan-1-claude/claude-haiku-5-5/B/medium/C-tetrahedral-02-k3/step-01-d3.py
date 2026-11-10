import numpy as np, itertools
from scipy.optimize import least_squares
# angular grid
nt, npz = 24, 48
x, w = np.polynomial.legendre.leggauss(nt)
phi = np.arange(npz)*2*np.pi/npz
ct, ph = np.meshgrid(x, phi, indexing='ij'); W = np.outer(w, np.ones(npz))*2*np.pi/npz
st = np.sqrt(1-ct**2)
n = np.stack([st*np.cos(ph), st*np.sin(ph), ct], -1).reshape(-1,3)
Wf = W.reshape(-1)
from scipy.special import sph_harm
def Y2(m):
    # scipy sph_harm(m, l, azimuth, polar)
    return sph_harm(m, 2, ph.reshape(-1), np.arccos(ct.reshape(-1)))
ms = [-2,-1,0,1,2]
Ys = np.array([Y2(m) for m in ms])  # 5 x Npts
# P_k(n1.n2)
G = n @ n.T
from scipy.special import eval_legendre
P = {k: eval_legendre(k, np.clip(G,-1,1)) for k in (0,2,4)}
# angular integrals c_k[a,b,c,d] = ∫∫ conj(Ya(1)) Yc(1) conj(Yb(2)) Yd(2) P_k
# Use weights
A = Ys.conj()*Wf  # 5 x N (weighted conj for point1)
Bm = Ys*Wf
def Ck(k):
    # result[a,c,b,d]
    T = P[k]*Wf[None,:]  # N1 x N2 ... weight on point2
    # sum over p1,p2: conj(Ya(p1)) Yc(p1) W1 * P(p1,p2) * conj(Yb(p2)) Yd(p2) W2
    # first: M[a,c,p2]= sum_p1 conj(Ya)Yc W1 P[p1,p2]
    Mac = np.einsum('ap,cq,pq->acq', Ys.conj()*Wf, Ys, P[k])
    return np.einsum('acq,bq,dq->acbd', Mac, Ys.conj()*Wf, Ys)
C0,C2,C4 = Ck(0),Ck(2),Ck(4)
# <ab|1/r|cd> = sum_k F^k C_k[a,c,b,d] where a,c on electron1 ; b,d electron2
def V2(F0,F2,F4):
    return F0*C0+F2*C2+F4*C4
# Fock space for 3 electrons in 5 spin-orbitals
states = [s for s in itertools.combinations(range(5),3)]
idx = {s:i for i,s in enumerate(states)}
def apply_cdag_c(p,q,st_):  # a_p^dag a_q on occupation tuple -> (sign, newstate) or None
    occ=list(st_)
    if q not in occ: return None
    sign=1
    pos=occ.index(q); sign*=(-1)**pos; occ.remove(q)
    if p in occ: return None
    # insert p
    pos2=sum(1 for o in occ if o<p); sign*=(-1)**pos2; occ.insert(pos2,p)
    return sign, tuple(sorted(occ))
def build(F2,F4,D):
    # one-electron: h = 6D P_eg - 4D P_t2g ; in m basis (index m+2)
    Peg=np.zeros((5,5))
    Peg[2,2]=1
    v=np.zeros(5); v[0]=v[4]=1/np.sqrt(2)
    Peg+=np.outer(v,v)
    h=6*D*Peg+(-4*D)*(np.eye(5)-Peg)
    V=V2(0,F2,F4)  # 2-body V[a,c,b,d] with a,c electron1... <ab|V|cd> = V[a,c,b,d]
    N=len(states); H=np.zeros((N,N))
    for j,s in enumerate(states):
        for i,t in enumerate(states):
            pass
    # build operator via second quantization: H = sum h_pq a_p^+ a_q + 1/2 sum <pq|V|rs> a_p^+ a_q^+ a_s a_r
    def apply_op(ops, vec):
        out=np.zeros(N)
        for k,amp in enumerate(vec):
            if abs(amp)<1e-14: continue
            st_=states[k]
            res=(st_,1.0)
            # apply sequentially
            cur=[(st_,1.0)]
            for (kind,p,q,c) in ops:
                new=[]
                for s,a in cur:
                    if kind=='1':
                        r=apply_cdag_c(p,q,s)
                        if r: new.append((r[1],a*r[0]*c))
                    else:
                        # two-body: a_p^+ a_q^+ a_s a_r  given as (p,q,s,r) with coefficient c
                        pass
                cur=new
            for s,a in cur: out[idx[s]]+=a*amp
        return out
    # simpler: direct determinant construction
    def apply_1(p,q,vec):
        out=np.zeros(N)
        for k,amp in enumerate(vec):
            if abs(amp)<1e-14: continue
            r=apply_cdag_c(p,q,states[k])
            if r: out[idx[r[1]]]+=r[0]*amp
        return out
    def apply_2(p,q,r_,s,vec):  # a_p^+ a_q^+ a_s a_r ; here use args (p,q,s,r)
        out=np.zeros(N)
        for k,amp in enumerate(vec):
            if abs(amp)<1e-14: continue
            st_=states[k]
            # a_r first
            x1=apply_cdag_c(s_,r_,st_) if False else None
            occ=list(st_); sign=1
            # annihilate r_
            if r_ not in occ: continue
            pos=occ.index(r_); sign*=(-1)**pos; occ.remove(r_)
            if s not in occ: continue
            pos=occ.index(s); sign*=(-1)**pos; occ.remove(s)
            if q not in occ and q!=q: pass
            if q in occ: continue
            pos=sum(1 for o in occ if o<q); sign*=(-1)**pos; occ.insert(pos,q)
            if p in occ: continue
            pos=sum(1 for o in occ if o<p); sign*=(-1)**pos; occ.insert(pos,p)
            out[idx[tuple(sorted(occ))]]+=sign*amp
        return out
    # build matrix columns
    for k in range(N):
        e=np.zeros(N); e[k]=1
        col=np.zeros(N)
        for p in range(5):
            for q in range(5):
                if abs(h[p,q])>1e-14: col+=h[p,q]*apply_1(p,q,e)
        for p in range(5):
            for q in range(5):
                for r_ in range(5):
                    for s in range(5):
                        # <pq|V|rs> = V[p,r,q,s]
                        val=0.5*V[p,r_,q,s]
                        if abs(val)>1e-14:
                            col+=val*apply_2(p,q,r_,s,e)
        H[:,k]=col
    return H
