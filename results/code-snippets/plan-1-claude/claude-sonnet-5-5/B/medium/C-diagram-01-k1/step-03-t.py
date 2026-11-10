import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=828.;C=3390.
F={2:49+7*C/B,4:63*C/5/B}
ms=[2,1,0,-1,-2]
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.
    return float((-1)**m*gaunt(2,k,2,-m,q,mp))*np.sqrt(4*np.pi/(2*k+1))
spo=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3)); idx={d:i for i,d in enumerate(dets)}
N=len(dets)
g={}
for a in range(10):
 for b in range(10):
  for c in range(10):
   for d in range(10):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=spo[a],spo[b],spo[c],spo[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    v=sum(F[k]*ck(k,ma,mc)*ck(k,md,mb) for k in (2,4))
    if abs(v)>1e-12: g[(a,b,c,d)]=v
def cre(i,d):
    if i in d: return None
    return (-1)**sum(1 for x in d if x<i), tuple(sorted(d+(i,)))
def ann(i,d):
    if i not in d: return None
    return (-1)**sum(1 for x in d if x<i), tuple(x for x in d if x!=i)
H2=np.zeros((N,N))
for (a,b,c,d),v in g.items():
  for j,det in enumerate(dets):
    s=1;x=det
    for f,i in ((ann,c),(ann,d),(cre,b),(cre,a)):
        r=f(i,x)
        if not r: s=0;break
        s*=r[0];x=r[1]
    if s: H2[idx[x],j]+=0.5*v*s
def onebody(M):
    O=np.zeros((N,N))
    for j,det in enumerate(dets):
      for p in range(10):
        for q in range(10):
          if spo[p][1]!=spo[q][1]: continue
          v=M[ms.index(spo[p][0]),ms.index(spo[q][0])]
          if v==0: continue
          r=ann(q,det)
          if not r: continue
          r2=cre(p,r[1])
          if not r2: continue
          O[idx[r2[1]],j]+=(v*r[0]*r2[0]).real
    return O
M=np.diag([1,-4,6,-4,1]).astype(complex); M[0,4]=M[4,0]=5
V0=onebody(M)
def compound(R):
    O=np.zeros((N,N),complex)
    for j,dj in enumerate(dets):
      for i,di in enumerate(dets):
        O[i,j]=np.linalg.det(R[np.ix_(di,dj)])
    return O
def spin_rep(M):
    R=np.zeros((10,10),complex)
    for p in range(10):
      for q in range(10):
        if spo[p][1]==spo[q][1]: R[p,q]=M[ms.index(spo[p][0]),ms.index(spo[q][0])]
    return R
mm=np.array(ms)
Rz=lambda ph: np.diag(np.exp(-1j*mm*ph))
C2y=np.zeros((5,5),complex)
for i,m in enumerate(ms): C2y[ms.index(-m),i]=(-1)**m
C2p=Rz(np.pi/4)@C2y@Rz(-np.pi/4)
K4=compound(spin_rep(Rz(np.pi/2))); K2p=compound(spin_rep(C2p))
Sz=np.diag([sum(0.5 if spo[x][1]==0 else -0.5 for x in d) for d in dets])
Sp=np.zeros((N,N))
for j,d in enumerate(dets):
  for m in ms:
    p=spo.index((m,1)); q=spo.index((m,0))
    r=ann(p,d)
    if r:
      r2=cre(q,r[1])
      if r2: Sp[idx[r2[1]],j]+=r[0]*r2[0]
S2=Sp.T@Sp+Sz@Sz+Sz
names={(1,1,1):'A1',(1,1,-1):'A2',(2,0,0):'E',(3,1,-1):'T1',(3,-1,1):'T2'}
def run(Dq):
    w,U=np.linalg.eigh(H2+Dq*V0); w=w-w[0]
    out=[];i=0
    while i<N:
        j=i
        while j+1<N and w[j+1]-w[i]<1e-6: j+=1
        Uc=U[:,i:j+1]; h=Uc.conj().T
        s2=np.trace(h@S2@Uc).real/(j-i+1)
        mult=int(round(np.sqrt(1+4*s2)))
        n=(j-i+1)//mult
        c4=round((np.trace(h@K4@Uc)/mult).real); c2=round((np.trace(h@K2p@Uc)/mult).real)
        out.append((w[i],f"{mult}{names.get((n,c4,c2),(n,c4,c2))}"))
        i=j+1
    return out
if __name__=="__main__":
  import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
  for x in np.arange(0,4.01,.5):
    print(x,[(round(e,3),t) for e,t in run(x if x>0 else 1e-4)[:6]])
  xs=np.linspace(0.01,4,60)
  Ls=[[e for e,t in run(x)[:8]] for x in xs]
  plt.plot(xs,np.array([l[:8] for l in Ls]));plt.xlabel('Dq/B');plt.ylabel('E/B');plt.savefig('diagram.png')
