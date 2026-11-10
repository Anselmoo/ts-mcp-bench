import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
from functools import lru_cache
l=2
ms=list(range(-2,3))
def idx(m): return m+2
@lru_cache(None)
def ang(k,m,q,mp):
    # <l m| C^k_q |l mp> = sqrt(4pi/(2k+1)) * int conj(Y_lm) Y_kq Y_l mp
    if abs(q)>k or abs(m)>l or abs(mp)>l: return 0.0
    g=float(gaunt(l,k,l,-m,q,mp))
    return ((-1)**m)*np.sqrt(4*np.pi/(2*k+1))*g
# W[m1,m2,m3,m4] = <m1 m2|1/r12|m3 m4> in units of F^k (coefficient for each k)
Wk={k:np.zeros((5,5,5,5)) for k in (0,2,4)}
for k in (0,2,4):
    for m1,m2,m3,m4 in itertools.product(ms,ms,ms,ms):
        s=0.0
        for q in range(-k,k+1):
            # <m1|C^k_q|m3> <m2|C^k_-q|m4>
            s+=((-1)**q)*ang(k,m1,q,m3)*ang(k,m2,-q,m4)
        Wk[k][idx(m1),idx(m2),idx(m3),idx(m4)]=s
# orbital vectors in m basis (orthonormal)
r2=1/np.sqrt(2)
orb={}
v=np.zeros(5,complex); v[idx(0)]=1; orb['z2']=v
v=np.zeros(5,complex); v[idx(2)]=r2; v[idx(-2)]=r2; orb['x2y2']=v
v=np.zeros(5,complex); v[idx(2)]=r2; v[idx(-2)]=-r2; v=v/1j; orb['xy']=v
v=np.zeros(5,complex); v[idx(1)]=-r2; v[idx(-1)]=r2; orb['xz']=v
v=np.zeros(5,complex); v[idx(1)]=1j*r2; v[idx(-1)]=1j*r2; orb['yz']=v
names=['z2','x2y2','xy','xz','yz']
U=np.array([orb[n] for n in names])  # 5x5 rows = orbitals
assert np.allclose(U.conj()@U.T,np.eye(5))
eg={'z2','x2y2'}
def energy_setup(Dq,B,C):
    F4=441*C/35.0
    F2=(441*B+5*F4)/9.0
    F={0:0.0,2:F2,4:F4}
    W=sum(F[k]*Wk[k] for k in (2,4))
    # transform to orbital basis: O[a,b,c,d]=sum conj(ua_m1)conj(ub_m2) uc_m3 ud_m4 W
    O=np.einsum('ai,bj,ck,dl,ijkl->abcd',U.conj(),U.conj(),U,U,W,optimize=True)
    h=np.diag([6*Dq if n in eg else -4*Dq for n in names]).astype(complex)
    # spin orbitals: p=2*o+s
    no=10
    H1=np.zeros((no,no),complex); V=np.zeros((no,no,no,no),complex)
    for o in range(5):
        for s in range(2):
            H1[2*o+s,2*o+s]=h[o,o]
    for a,b,c,d in itertools.product(range(5),repeat=4):
        for s1 in range(2):
            for s2 in range(2):
                V[2*a+s1,2*b+s2,2*c+s1,2*d+s2]=O[a,b,c,d]
    # Fock basis
    states=list(itertools.combinations(range(no),8))
    index={s:i for i,s in enumerate(states)}
    D=len(states)
    Hm=np.zeros((D,D),complex)
    def apply_ops(ops,st):
        # ops list of (type,p) applied right-to-left: ops = [('c',p),('a',q),...] applied in order given
        occ=list(st); sign=1
        for t,p in reversed(ops):
            if t=='a':  # annihilate p
                if p not in occ: return None,0
                pos=occ.index(p); sign*=(-1)**pos; occ.pop(pos)
            else:
                if p in occ: return None,0
                pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
        return tuple(occ),sign
    for j,st in enumerate(states):
        # one-body
        for p in range(no):
            for q in range(no):
                if H1[p,q]==0: continue
                new,sg=apply_ops([('c',p),('a',q)],st)
                if new is None: continue
                Hm[index[new],j]+=H1[p,q]*sg
        # two-body: 1/2 sum V_pqrs c+p c+q c_s c_r
        for p,q,r,s in itertools.product(range(no),repeat=4):
            if V[p,q,r,s]==0: continue
            new,sg=apply_ops([('c',p),('c',q),('a',s),('a',r)],st)
            if new is None: continue
            Hm[index[new],j]+=0.5*V[p,q,r,s]*sg
    # Ms sectors: Ms=+1 triplet check: n_up=5
    up=[i for i,s in enumerate(states) if sum(1 for x in s if x%2==0)==5 and sum(1 for x in s if x%2==1)==3]
    Hup=Hm[np.ix_(up,up)]
    Et=np.sort(np.linalg.eigvalsh(Hup))
    Ef=np.sort(np.linalg.eigvalsh(Hm))
    return Et,Ef
if __name__=='__main__':
    Et,Ef=energy_setup(1000,1000,4000)
    print(np.round(Et-Et[0],1)); print(np.round(Ef-Et[0],1))
