import numpy as np, itertools
from scipy.optimize import least_squares
from scipy.special import sph_harm
# real d orbitals as functions of direction
def realY(l,m,th,ph):
    # real spherical harmonics l=2 (m index -2..2) and general k
    pass
# Build real d orbital angular functions on quadrature grid
xg,wg=np.polynomial.legendre.leggauss(40)
nphi=80
th=np.arccos(xg); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=(np.outer(wg,np.ones(nphi))*2*np.pi/nphi)
x=np.sin(TH)*np.cos(PH); y=np.sin(TH)*np.sin(PH); z=np.cos(TH)
# real d orbitals (unnormalized shapes, normalize numerically)
orbs={'xy':x*y,'xz':x*z,'yz':y*z,'z2':(3*z**2-1)/2,'x2y2':(x**2-y**2)*np.sqrt(3)/2}
names=list(orbs)
for n in names:
    f=orbs[n]; norm=np.sum(W*f*f); orbs[n]=f/np.sqrt(norm)
# real-harmonic Ykq for k=0,2,4 : build from sph_harm combos
def Rkq(k):
    out=[]
    for m in range(-k,k+1):
        if m==0: out.append(sph_harm(0,k,PH,TH).real)
        elif m>0:
            out.append(np.sqrt(2)*(-1)**m*sph_harm(m,k,PH,TH).real)
        else:
            out.append(np.sqrt(2)*(-1)**m*sph_harm(-m,k,PH,TH).imag)
    return out
# angular integrals a_k(a,b;c,d)= 4pi/(2k+1) sum_q G(a,c,q) G(b,d,q)
def ak(k):
    R=Rkq(k); n=len(names)
    G=np.zeros((n,n,len(R)))
    for i,a in enumerate(names):
        for j,c in enumerate(names):
            for q,Rq in enumerate(R):
                G[i,j,q]=np.sum(W*orbs[a]*orbs[c]*Rq)
    A=np.einsum('acq,bdq->abcd',G,G)*4*np.pi/(2*k+1)
    return A
A={k:ak(k) for k in (0,2,4)}
# spin-orbitals: index = orb*2+spin
so=[(o,s) for o in range(5) for s in (0,1)]
N=len(so)
# one-electron cubic field: t2g = xy,xz,yz (idx 0,1,2) -> -4Dq ; eg = z2,x2y2 (3,4) -> +6Dq
def build(Dq,B,C):
    F4=441*C/35.0; F2=441*B+5*F4
    F={0:0.0,2:F2,4:F4}
    # two-electron: <ij|1/r|kl> = sum_k F^k a_k  ; H = 1/2 sum <ij|kl> a+_i a+_j a_l a_k
    V=np.zeros((N,N,N,N))
    for i,(oi,si) in enumerate(so):
        for j,(oj,sj) in enumerate(so):
            for k_,(ok,sk) in enumerate(so):
                for l,(ol,sl) in enumerate(so):
                    # spin: <i j| k l> requires s_i=s_k, s_j=s_l
                    if si!=sk or sj!=sl: continue
                    val=0
                    for kk in (0,2,4):
                        val+=F[kk]*A[kk][oi,ok,oj,ol]
                    V[i,j,k_,l]=val
    h=np.zeros((N,N))
    for i,(o,s) in enumerate(so):
        h[i,i]= -4*Dq if o<3 else 6*Dq
    return h,V
# determinants of 7 electrons in 10 spin orbitals
dets=list(itertools.combinations(range(N),7))
idx={d:i for i,d in enumerate(dets)}
def apply_ops(det,ops):
    # ops list of (type,index) applied right-to-left: ops = [(op,i),...] operator product, apply last first
    occ=list(det); sign=1
    for typ,i in reversed(ops):
        if typ=='a':  # annihilate
            if i not in occ: return None,0
            p=occ.index(i); sign*= (-1)**p; occ.pop(p)
        else:
            if i in occ: return None,0
            # insert sorted
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return tuple(occ),sign
def hamiltonian(Dq,B,C):
    h,V=build(Dq,B,C)
    M=len(dets); H=np.zeros((M,M))
    nzV=[(i,j,k,l,V[i,j,k,l]) for i,j,k,l in itertools.product(range(N),repeat=4) if abs(V[i,j,k,l])>1e-12]
    for m,d in enumerate(dets):
        # one-body
        for i in range(N):
            for j in range(N):
                if abs(h[i,j])>1e-12:
                    r,s=apply_ops(d,[('c',i),('a',j)])
                    if r is not None: H[idx[r],m]+=h[i,j]*s
        for (i,j,k,l,v) in nzV:
            r,s=apply_ops(d,[('c',i),('c',j),('a',l),('a',k)])
            if r is not None: H[idx[r],m]+=0.5*v*s
    return H
# S^2 operator for spin: S^2 = Sz^2 + S+S- ... use penalty approach: build Sz and S+ ops
def S2mat():
    Sz=np.zeros((len(dets),)*2); Sp=np.zeros((len(dets),)*2)
    for m,d in enumerate(dets):
        sz=0
        for i in d: sz+= 0.5 if so[i][1]==0 else -0.5
        Sz[m,m]=sz
        for o in range(5):
            # S+ = sum c_{o,up} c_{o,down}^dag
            up=2*o; dn=2*o+1
            r,s=apply_ops(d,[('c',up),('a',dn)])
            if r is not None: Sp[idx[r],m]+=s
    Sm=Sp.T
    return Sz@Sz+0.5*(Sp@Sm+Sm@Sp)
S2=S2mat()
def levels(Dq,B,C):
    H=hamiltonian(Dq,B,C)
    H2=H+100000*S2
    w,v=np.linalg.eigh(H2)
    # spin of each eigvec
    out=[]
    for e,vec in zip(w,v.T):
        s2=vec@S2@vec
        S=(-1+np.sqrt(1+4*s2))/2
        out.append((round(S*2),e))
    return out
if __name__=='__main__':
    lv=levels(1000,1000,4000)
    qs=sorted(set(round(e,3) for s,e in lv if s==3))
    print('quartets', [ (round(e,1)) for s,e in lv if s==3][:4])
    print('doublets', [ (round(e,1)) for s,e in lv if s==1][:8])
