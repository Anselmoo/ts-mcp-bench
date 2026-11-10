import numpy as np, itertools
from scipy.special import sph_harm
from scipy.linalg import null_space
# spatial d orbitals m=-2..2 ; spin-orbital index p = 2*(m+2)+s  (s=0 up,1 down)
ms=[-2,-1,0,1,2]
th,wt=np.polynomial.legendre.leggauss(40)   # cos(theta) nodes
ph=np.linspace(0,2*np.pi,80,endpoint=False); wph=2*np.pi/80
CT,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(wt,np.ones(len(ph)))*wph
TH=np.arccos(CT)
def Y(l,m,theta,phi): return sph_harm(m,l,phi,theta)
phi_m=[Y(2,m,TH,PH) for m in ms]
# cubic point-charge potential at +-x,+-y,+-z (unit sphere), attractive
rhat=np.stack([np.sin(TH)*np.cos(PH),np.sin(TH)*np.sin(PH),CT],-1)
Ls=[np.array(v,float) for v in [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]]]
Vang=-sum(1/np.linalg.norm(rhat-L,axis=-1) for L in Ls)
h=np.zeros((5,5),complex)
for i in range(5):
  for j in range(5):
    h[i,j]=np.sum(np.conj(phi_m[i])*Vang*phi_m[j]*W)
ev=np.linalg.eigvalsh(h)
print("cubic one-electron eigen (raw):",ev)
# eg are top two, t2g bottom three
split=ev[-1]-ev[0]
# scale so that eg - t2g = 10Dq with Dq=1 unit: we return h per Dq
Dq_unit=(ev[-1]-ev[2])/10.0  # eg(=ev[3],ev[4]) minus t2g(=ev[0..2]) ~ use mean
eg_mean=(ev[3]+ev[4])/2; t2g_mean=(ev[0]+ev[1]+ev[2])/3
Dq_unit=(eg_mean-t2g_mean)/10.0
h1=h/Dq_unit  # now in units of Dq: eg-t2g=10
print("check eg-t2g in Dq units:", np.linalg.eigvalsh(h1)[3:].mean()-np.linalg.eigvalsh(h1)[:3].mean())
# multipole tensors
def Mk(k):
  M=np.zeros((5,5,2*k+1),complex); N=np.zeros((5,5,2*k+1),complex)
  for q in range(-k,k+1):
    yk=Y(k,q,TH,PH)
    for a in range(5):
      for c in range(5):
        M[a,c,q+k]=np.sum(np.conj(phi_m[a])*np.conj(yk)*phi_m[c]*W)
        N[a,c,q+k]=np.sum(np.conj(phi_m[a])*yk*phi_m[c]*W)
  return M,N
ang={}
for k in [0,2,4]:
  ang[k]=Mk(k)
# angular coefficient A_k(i,j,k_,l) for <ij|v|kl>, spatial indices
def Aint(kk,a,c,b,d):
  M,N=ang[kk]
  return (4*np.pi/(2*kk+1))*np.sum(M[a,c,:]*N[b,d,:])
Ak={kk:np.zeros((5,5,5,5),complex) for kk in [0,2,4]}
for kk in [0,2,4]:
  for a,b,c,d in itertools.product(range(5),repeat=4):
    Ak[kk][a,b,c,d]=Aint(kk,a,c,b,d)
# spin-orbital mapping
def spat(p): return p//2
def spin(p): return p%2
NSO=10
def build(F):
  # F: dict k->F^k
  # two-electron tensor in spin-orbitals
  V=np.zeros((NSO,)*4,complex)
  for p,q,r,s in itertools.product(range(NSO),repeat=4):
    if spin(p)!=spin(r) or spin(q)!=spin(s): continue
    val=0
    for kk in [0,2,4]:
      val+=F[kk]*Ak[kk][spat(p),spat(q),spat(r),spat(s)]
    V[p,q,r,s]=val
  # one-electron
  H1=np.zeros((NSO,NSO),complex)
  for p,q in itertools.product(range(NSO),repeat=2):
    if spin(p)==spin(q): H1[p,q]=h1[spat(p),spat(q)]
  return H1,V
# fock states: 5 electrons in 10 spin-orbitals
states=[sum(1<<p for p in c) for c in itertools.combinations(range(NSO),5)]
idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,st):
  # ops list of (type,p) applied right-to-left: list is applied in order given (first applied first)
  sgn=1
  for typ,p in ops:
    occ=(st>>p)&1
    if typ=='c':
      if occ: return None,0
      sgn*= (-1)**bin(st&((1<<p)-1)).count('1')
      st|=(1<<p)
    else:
      if not occ: return None,0
      sgn*= (-1)**bin(st&((1<<p)-1)).count('1')
      st&=~(1<<p)
  return st,sgn
def Hmat(F):
  H1,V=build(F)
  n=len(states); H=np.zeros((n,n),complex)
  nz=[(p,q,r,s,V[p,q,r,s]) for p,q,r,s in itertools.product(range(NSO),repeat=4) if abs(V[p,q,r,s])>1e-12]
  nz1=[(p,q,H1[p,q]) for p,q in itertools.product(range(NSO),repeat=2) if abs(H1[p,q])>1e-12]
  for i,st in enumerate(states):
    for p,q,c in nz1:
      s2,sg=apply_ops([('a',q),('c',p)],st) if True else None
      # a_q first then c_p: a†_p a_q |st>
      s2,sg=apply_ops([('a',q),('c',p)],st)
      if s2 is not None: H[idx[s2],i]+=c*sg
    for p,q,r,s,v in nz:
      # 1/2 a†_p a†_q a_s a_r
      s2,sg=apply_ops([('a',r),('a',s),('c',q),('c',p)],st)
      if s2 is not None: H[idx[s2],i]+=0.5*v*sg
  return H
# S^2 in this Fock space
def S2mat():
  n=len(states); Sp=np.zeros((n,n)); Sz=np.zeros(n)
  for i,st in enumerate(states):
    nu=sum((st>>(2*m))&1 for m in range(5)); nd=sum((st>>(2*m+1))&1 for m in range(5))
    Sz[i]=0.5*(nu-nd)
    for m in range(5):
      s2,sg=apply_ops([('a',2*m+1),('c',2*m)],st)  # S+ = a†_up a_down
      if s2 is not None: Sp[idx[s2],i]+=sg
  Sm=Sp.T
  S2=Sm@Sp+np.diag(Sz*(Sz+1))
  return S2
S2=S2mat()
# restrict to doublets: eigenvalue 3/4 of S2 subspace
Nd=null_space(S2-0.75*np.eye(len(states)))
print("doublet subspace dim (microstates count / orbital):",Nd.shape)
def doublet_levels(Dq,B,C):
  F={0:0,2:49*B+7*C,4:12.6*C}
  H=Hmat(F)
  # scale: h1 in Dq units, multiply by Dq
  return None
