
mkdir -p ~/w && cd ~/w && cat << 'EOF' > d3.py
import numpy as np, itertools
from scipy.special import sph_harm
from numpy.polynomial.legendre import leggauss
nt,nphi=30,60
x,w=leggauss(nt); th=np.arccos(x); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nphi))*2*np.pi/nphi
X=np.sin(TH)*np.cos(PH); Y=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
# real d orbitals (angular), normalized on sphere
raw={'xy':X*Y,'yz':Y*Z,'zx':Z*X,'z2':(3*Z**2-1),'x2y2':(X**2-Y**2)}
names=list(raw)
orbs=[]
for n in names:
    f=raw[n]; nrm=np.sqrt(np.sum(W*f*f)); orbs.append(f/nrm)
# spin-orbitals
so=[(i,s) for i in range(5) for s in (1,-1)]
N=10
def Ylm(l,m): return sph_harm(m,l,PH,TH)
def ang(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Yk=Ylm(k,q)
        s+= np.sum(W*orbs[a]*np.conj(Yk)*orbs[c]) * np.sum(W*orbs[b]*Yk*np.conj(np.conj(Yk))*0+ W*0) if False else 0
    return 0
# do properly: P_k(cos g) = 4pi/(2k+1) sum_q Y*_kq(1) Y_kq(2)
def angint(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Yk=Ylm(k,q)
        t1=np.sum(W*orbs[a]*np.conj(Yk)*orbs[c])
        t2=np.sum(W*orbs[b]*Yk*orbs[d])   # Y_kq(2) with b* d; real orbitals
        s+=t1*t2
    return 4*np.pi/(2*k+1)*s
A={k:np.zeros((5,5,5,5),complex) for k in (2,4)}
for k in (2,4):
    for a in range(5):
     for b in range(5):
      for c in range(5):
       for d in range(5):
        A[k][a,b,c,d]=angint(k,a,b,c,d)
def Vfull(F2,F4):
    V=np.zeros((N,N,N,N),complex)
    for i,(oi,si) in enumerate(so):
     for j,(oj,sj) in enumerate(so):
      for k,(ok,sk) in enumerate(so):
       for l,(ol,sl) in enumerate(so):
        if si!=sk or sj!=sl: continue
        V[i,j,k,l]=F2*A[2][oi,oj,ok,ol]+F4*A[4][oi,oj,ok,ol]
    return V
dets=list(itertools.combinations(range(N),3)); idx={d:i for i,d in enumerate(dets)}
def cdag_c(ops, det):
    # ops: list of ('c',p) or ('d',p) applied right-to-left as given in product order
    pass
def apply(op_list,det):
    # op_list applied right-to-left: op_list = [(type,p),...], last applied first
    occ=list(det); sign=1
    for typ,p in reversed(op_list):
        if typ=='c':   # annihilate
            if p not in occ: return None,None
            q=occ.index(p); sign*=(-1)**q; occ.pop(q)
        else:
            if p in occ: return None,None
            q=sum(1 for x in occ if x<p); sign*=(-1)**q; occ.insert(q,p)
    return sign,tuple(occ)
def build(F2,F4,Dq):
    V=Vfull(F2,F4)
    M=np.zeros((len(dets),len(dets)),complex)
    # one-body: -4Dq for t2g (xy,yz,zx), +6Dq for eg (z2,x2y2)
    h=[-4*Dq if n in('xy','yz','zx') else 6*Dq for n in names]
    for J,det in enumerate(dets):
        for a in range(N):
            for b in range(N):
                if so[a][1]!=so[b][1] or so[a][0]!=so[b][0]: continue
                pass
        # one-body
        for p in range(N):
            if so[p][0]==-1: pass
        for p in range(N):
            s,nd=apply([('d',p),('c',p)],det)
            if s is None: continue
        for p,(op,sp) in enumerate(so):
            s,nd=apply([('d',p),('c',p)],det)
            if s is not None: M[idx[nd],J]+=h[op]*s
        for i in range(N):
         for j in range(N):
          for k in range(N):
           for l in range(N):
            v=V[i,j,k,l]
            if abs(v)<1e-12: continue
            s,nd=apply([('d',i),('d',j),('c',l),('c',k)],det)
            if s is not None: M[idx[nd],J]+=0.5*v*s
    return M
# S^2 operator in det basis
def S2(M=None):
    Sz=np.zeros((len(dets),)*2)
    S2m=np.zeros((len(dets),len(dets)),complex)
    # S^2 = S- S+ + Sz(Sz+1)
    for J,det in enumerate(dets):
        nup=sum(1 for p in det if so[p][1]==1)
        szv=(2*nup-3)/2
        S2m[J,J]+=szv*(szv+1)
        for a in range(N):
            for b in range(N):
                # S+ S- : c†_{a up} c_{a dn} ... use S-=sum c†_dn c_up, S+=sum c†_up c_dn
                pass
    # S- S+ built explicitly
    Sp=np.zeros_like(S2m); Sm=np.zeros_like(S2m)
    for J,det in enumerate(dets):
        for p in range(N):
            for q in range(N):
                if so[p][1]==1 and so[q][1]==-1 and so[p][0]==so[q][0]:
                    s,nd=apply([('d',p),('c',q)],det)
                    if s is not None: Sp[idx[nd],J]+=s
    Sm=Sp.T
    return Sm@Sp+ np.diag([ ( (2*sum(1 for p in d if so[p][1]==1)-3)/2 ) for d in dets])*0 + 0
EOF
python3 -c "import sys;sys.path.insert(0,'.');import d3;print('ok')"