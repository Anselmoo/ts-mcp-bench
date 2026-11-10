cd /tmp && python3 - << 'EOF'
import numpy as np
# Using level energies (units of B) computed at x=3.10 and nearby; refine with finer grid via parameter recomputation
import itertools
from scipy.special import sph_harm_y
from scipy.linalg import null_space
from scipy.optimize import minimize_scalar
ms=[-2,-1,0,1,2]
x,wt=np.polynomial.legendre.leggauss(60)
ph=np.linspace(0,2*np.pi,120,endpoint=False); wph=2*np.pi/120
CT,PH=np.meshgrid(x,ph,indexing='ij'); W=np.outer(wt,np.ones(len(ph)))*wph
TH=np.arccos(CT)
phi_m=[sph_harm_y(2,m,TH,PH) for m in ms]
rhat=np.stack([np.sin(TH)*np.cos(PH),np.sin(TH)*np.sin(PH),CT],-1)
Ls=[3*np.array(v,float) for v in [[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]]]
Vang=sum(1/np.linalg.norm(rhat-L,axis=-1) for L in Ls)
h=np.array([[np.sum(np.conj(phi_m[i])*Vang*phi_m[j]*W) for j in range(5)] for i in range(5)])
ev=np.linalg.eigvalsh(h); h1=h/(((ev[3]+ev[4])/2-(ev[0]+ev[1]+ev[2])/3)/10)
ang={}
for k in [0,2,4]:
  M=np.zeros((5,5,2*k+1),complex); N=np.zeros((5,5,2*k+1),complex)
  for q in range(-k,k+1):
    yk=sph_harm_y(k,q,TH,PH)
    for a in range(5):
      for c in range(5):
        M[a,c,q+k]=np.sum(np.conj(phi_m[a])*np.conj(yk)*phi_m[c]*W)
        N[a,c,q+k]=np.sum(np.conj(phi_m[a])*yk*phi_m[c]*W)
  ang[k]=(M,N)
Ak={k:(4*np.pi/(2*k+1))*np.einsum('acq,bdq->abcd',ang[k][0],ang[k][1]) for k in [0,2,4]}
NSO=10; spat=lambda p:p//2; spin=lambda p:p%2
Vk={}
for k in [2,4]:
  T=np.zeros((NSO,)*4,complex)
  for p,q,r,s in itertools.product(range(NSO),repeat=4):
    if spin(p)==spin(r) and spin(q)==spin(s): T[p,q,r,s]=Ak[k][spat(p),spat(q),spat(r),spat(s)]
  Vk[k]=T
states=[sum(1<<p for p in c) for c in itertools.combinations(range(NSO),5)]
idx={s:i for i,s in enumerate(states)}
def apply(ops,st):
  sgn=1
  for typ,p in ops:
    occ=(st>>p)&1
    if typ=='c':
      if occ: return None,0
      sgn*=(-1)**bin(st&((1<<p)-1)).count('1'); st|=(1<<p)
    else:
      if not occ: return None,0
      sgn*=(-1)**bin(st&((1<<p)-1)).count('1'); st&=~(1<<p)
  return st,sgn
n=len(states)
def opmat(terms):
  H=np.zeros((n,n),complex)
  for i,st in enumerate(states):
    for c,ops in terms:
      s2,sg=apply(ops,st)
      if s2 is not None: H[idx[s2],i]+=c*sg
  return H
HLF=opmat([(h1[spat(p),spat(q)],[('a',q),('c',p)]) for p in range(NSO) for q in range(NSO) if spin(p)==spin(q) and abs(h1[spat(p),spat(q)])>1e-10])
def ee_terms(k):
  t=[]; T=Vk[k]
  for p,q,r,s in itertools.product(range(NSO),repeat=4):
    if abs(T[p,q,r,s])>1e-10: t.append((0.5*T[p,q,r,s],[('a',r),('a',s),('c',q),('c',p)]))
  return t
HE={k:opmat(ee_terms(k)) for k in [2,4]}
Sp=opmat([(1.0,[('a',2*m+1),('c',2*m)]) for m in range(5)])
Sz=np.array([0.5*(sum((st>>(2*m))&1 for m in range(5))-sum((st>>(2*m+1))&1 for m in range(5))) for st in states])
S2=(Sp.T@Sp+np.diag(Sz*(Sz+1))).real
Nd=null_space(S2-0.75*np.eye(n))
def levels(Dq,B,C=None):
  if C is None: C=4.6*B
  F={2:49*B+7*C,4:12.6*C}
  H=Dq*HLF+sum(F[k]*HE[k] for k in [2,4])
  Hd=Nd.conj().T@H@Nd
  return np.sort(np.linalg.eigvalsh((Hd+Hd.conj().T)/2).real)
obs=np.array([22640.,22930.,25080.])
# Find unique levels: energies of states 0 (ground), A1g-type (deg2), T1g (deg6), T1g' (deg6)
def cl(L,tol=1e-3):
  out=[]
  for v in L:
    if not out or abs(v-out[-1][0])>tol: out.append([v,1])
    else: out[-1][1]+=1
  return out
def triple(xv):
  L=levels(xv,1.0); L=L-L[0]; c=cl(L)
  return c[0][0], c[1][0], c[2][0], c[1][1], c[2][1]
def resid(xv):
  g,a,b,da,db=triple(xv)
  # pick ν1=a,ν2=b,ν3=next cluster: check identities
  return None
for xv in np.arange(3.08,3.125,0.005):
  c=cl(levels(xv,1.0)-levels(xv,1.0)[0])
  E=[v for v,_ in c[:4]]; D=[d for _,d in c[:4]]
  print(round(xv,3), [round(e,4) for e in E], D)
EOF