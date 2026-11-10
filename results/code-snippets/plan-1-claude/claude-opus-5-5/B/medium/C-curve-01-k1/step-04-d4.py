import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B=821.;C=3657.
F4=C/35;F2=B+5*F4
Fk={0:0,2:F2*49,4:F4*441}
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (0,1)]
def ckf(k,m1,m2):
  return float((-1)**(-m1)*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m1,m1-m2,m2))
def g(a,b,c,d):
  (ma,sa),(mb,sb),(mc,sc),(md,sd)=so[a],so[b],so[c],so[d]
  if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
  return sum(ckf(k,ma,mc)*ckf(k,md,mb)*Fk[k] for k in (0,2,4))
def cf(m1,m2):
  if m1==m2: return {2:1,-2:1,1:-4,-1:-4,0:6}[m1]
  if abs(m1-m2)==4: return 5
  return 0
n=10
G=np.zeros((n,n,n,n))
for a,b,c,d in itertools.product(range(n),repeat=4): G[a,b,c,d]=g(a,b,c,d)
h1=np.array([[cf(so[i][0],so[j][0]) if so[i][1]==so[j][1] else 0 for j in range(n)] for i in range(n)],float)
dets=list(itertools.combinations(range(n),4))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply_ops(det,ops):
  occ=list(det);sign=1
  for t,o in reversed(ops):
    if t=='a':
      if o not in occ: return 0,None
      p=occ.index(o);sign*=(-1)**p;occ.pop(p)
    else:
      if o in occ: return 0,None
      p=sum(1 for x in occ if x<o);sign*=(-1)**p;occ.insert(p,o)
  return sign,tuple(occ)
H1=np.zeros((N,N));H2=np.zeros((N,N));S2=np.zeros((N,N))
nz=[(p,q,r,s) for p,q,r,s in itertools.product(range(n),repeat=4) if abs(G[p,q,r,s])>1e-12]
for j,d in enumerate(dets):
  for p in range(n):
    for q in range(n):
      if h1[p,q]:
        s,nd=apply_ops(d,[('c',p),('a',q)])
        if s: H1[idx[nd],j]+=s*h1[p,q]
  for p,q,r,s_ in nz:
    s,nd=apply_ops(d,[('c',p),('c',q),('a',s_),('a',r)])
    if s: H2[idx[nd],j]+=0.5*s*G[p,q,r,s_]
  sz=sum(0.5 if so[o][1]==0 else -0.5 for o in d)
  S2[j,j]+=sz*sz-sz
  for m in range(5):
    for m2 in range(5):
      s,nd=apply_ops(d,[('c',2*m2),('a',2*m2+1),('c',2*m+1),('a',2*m)])
      if s: S2[idx[nd],j]+=s
print(np.abs(S2-S2.T).max(),np.abs(H2-H2.T).max())
R=np.array([np.prod([1j**so[o][0] for o in d]) for d in dets])
for x in (0.0,0.90,2.15,3.35):
  H=H2+x*B*H1
  w,v=np.linalg.eigh(H)
  E=(w-w[0])/B
  i=0;res=[]
  while i<N and len(res)<6:
    j=i
    while j<N and abs(E[j]-E[i])<1e-6: j+=1
    V=v[:,i:j]
    s2=np.real(np.trace(V.conj().T@S2@V))/(j-i)
    S=(-1+np.sqrt(1+4*s2))/2
    mult=int(round(2*S+1));deg=(j-i)//mult
    chi=np.real(np.trace(V.conj().T@(R[:,None]*V)))/mult
    res.append((round(E[i],3),j-i,round(S,2),deg,round(chi,2)))
    i=j
  print(x,res)
