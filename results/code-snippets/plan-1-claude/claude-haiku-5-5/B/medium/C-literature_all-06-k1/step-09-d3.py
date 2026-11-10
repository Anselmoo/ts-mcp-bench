import numpy as np, itertools
from scipy.special import sph_harm_y
from numpy.polynomial.legendre import leggauss
nt,nphi=30,60
x,w=leggauss(nt); th=np.arccos(x); ph=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nphi))*2*np.pi/nphi
X=np.sin(TH)*np.cos(PH); Y=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
raw={'xy':X*Y,'yz':Y*Z,'zx':Z*X,'z2':(3*Z**2-1),'x2y2':(X**2-Y**2)}
names=list(raw)
orbs=[]
for n in names:
    f=raw[n]; orbs.append(f/np.sqrt(np.sum(W*f*f)))
so=[(i,s) for i in range(5) for s in (1,-1)]; N=10
def Ylm(l,m): return sph_harm_y(l,m,TH,PH)
def angint(k,a,b,c,d):
    s=0
    for q in range(-k,k+1):
        Yk=Ylm(k,q)
        s+=np.sum(W*orbs[a]*np.conj(Yk)*orbs[c])*np.sum(W*orbs[b]*Yk*orbs[d])
    return 4*np.pi/(2*k+1)*s
A={k:np.zeros((5,5,5,5),complex) for k in (2,4)}
for k in (2,4):
  for a,b,c,d in itertools.product(range(5),repeat=4):
    A[k][a,b,c,d]=angint(k,a,b,c,d)
def Vfull(F2,F4):
    V=np.zeros((N,N,N,N),complex)
    for i,(oi,si) in enumerate(so):
     for j,(oj,sj) in enumerate(so):
      for k,(ok,sk) in enumerate(so):
       for l,(ol,sl) in enumerate(so):
        if si==sk and sj==sl:
          V[i,j,k,l]=F2*A[2][oi,oj,ok,ol]+F4*A[4][oi,oj,ok,ol]
    return V
def apply(ops,det):
    occ=list(det); sign=1
    for typ,p in reversed(ops):
        if typ=='c':
            if p not in occ: return None,None
            q=occ.index(p); sign*=(-1)**q; occ.pop(q)
        else:
            if p in occ: return None,None
            q=sum(1 for x in occ if x<p); sign*=(-1)**q; occ.insert(q,p)
    return sign,tuple(occ)
dets=list(itertools.combinations(range(N),3)); idx={d:i for i,d in enumerate(dets)}; D=len(dets)
# precompute two-body action list
TB=[]
for J,det in enumerate(dets):
    for i,j,k,l in itertools.product(range(N),repeat=4):
        s,nd=apply([('d',i),('d',j),('c',l),('c',k)],det)
        if s is not None: TB.append((i,j,k,l,J,idx[nd],s))
ONE=[]
for J,det in enumerate(dets):
    for p,(op,sp) in enumerate(so):
        s,nd=apply([('d',p),('c',p)],det)
        if s is not None: ONE.append((op,J,idx[nd],s))
def build(F2,F4,Dq):
    V=Vfull(F2,F4)
    h=[-4*Dq if n in('xy','yz','zx') else 6*Dq for n in names]
    M=np.zeros((D,D),complex)
    for op,J,I,s in ONE: M[I,J]+=h[op]*s
    for i,j,k,l,J,I,s in TB:
        v=V[i,j,k,l]
        if abs(v)>1e-12: M[I,J]+=0.5*v*s
    return M
Sp=np.zeros((D,D))
for J,det in enumerate(dets):
    for p in range(N):
        for q in range(N):
            if so[p][1]==1 and so[q][1]==-1 and so[p][0]==so[q][0]:
                s,nd=apply([('d',p),('c',q)],det)
                if s is not None: Sp[idx[nd],J]+=s
Sz=np.diag([(2*sum(1 for p in d if so[p][1]==1)-3)/2 for d in dets])
S2=Sp.T@Sp+Sz@(Sz+np.eye(D))
ev,vec=np.linalg.eigh(S2)
PQ=vec[:,np.abs(ev-3.75)<1e-6]; PD=vec[:,np.abs(ev-0.75)<1e-6]
def spectrum(B,C,Dq):
    F4=441*C/35; F2=49*B+5*F4/9
    M=build(F2,F4,Dq)
    out={}
    for lab,P in [('Q',PQ),('D',PD)]:
        e=np.sort(np.linalg.eigvalsh(P.conj().T@M@P).real)
        cl=[]
        for v in e:
            if cl and abs(v-cl[-1][0])<0.5: cl[-1][1]+=1
            else: cl.append([v,1])
        out[lab]=cl
    return out
