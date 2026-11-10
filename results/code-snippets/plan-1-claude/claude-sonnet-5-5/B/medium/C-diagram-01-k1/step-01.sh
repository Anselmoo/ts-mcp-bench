cat > /tmp/t.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=828.;C=3390.;B1=1.0
F={2:49*B1+7*C/B,4:63*C/5/B}
ms=[2,1,0,-1,-2]
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.
    # <Y2m|C^k_q|Y2m'> = (-1)^m sqrt(4pi/(2k+1))... via gaunt(l1,l2,l3,m1,m2,m3) of Y*Y*Y
    return float((-1)**m*gaunt(2,k,2,-m,q,mp))*np.sqrt(4*np.pi/(2*k+1)) if True else 0
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
def apply(ops,d):
    # ops list of annihilate/create sequence applied right to left: list of (type,idx)
    pass
def cre(i,d):
    if i in d: return None
    s=(-1)**sum(1 for x in d if x<i); return s,tuple(sorted(d+(i,)))
def ann(i,d):
    if i not in d: return None
    s=(-1)**sum(1 for x in d if x<i); return s,tuple(x for x in d if x!=i)
H2=np.zeros((N,N))
for (a,b,c,d),v in g.items():
  for j,det in enumerate(dets):
    r=ann(c,det)   # a†b† d c ; apply c first then d
    if not r: continue
    s1,x=r; r=ann(d,x)
    if not r: continue
    s2,x=r; r=cre(b,x)
    if not r: continue
    s3,x=r; r=cre(a,x)
    if not r: continue
    s4,x=r
    H2[idx[x],j]+=0.5*v*s1*s2*s3*s4
def onebody(M):
    O=np.zeros((N,N),complex)
    for j,det in enumerate(dets):
      for p in range(10):
        for q in range(10):
          if spo[p][1]!=spo[q][1]: continue
          mp,mq=ms.index(spo[p][0]),ms.index(spo[q][0])
          v=M[mp,mq]
          if v==0: continue
          r=ann(q,det)
          if not r: continue
          s1,x=r; r=cre(p,x)
          if not r: continue
          s2,x=r
          O[idx[x],j]+=v*s1*s2
    return O
def Vm(Dq):
    M=np.diag([Dq,-4*Dq,6*Dq,-4*Dq,Dq]).astype(complex); M[0,4]=M[4,0]=5*Dq; return M
# group ops: one-body op for rotations is not additive; use compound matrices: instead build via exp of generators? use direct many-body det minors
def compound(R):
    O=np.zeros((N,N),complex)
    for j,dj in enumerate(dets):
      for i,di in enumerate(dets):
        sub=np.array([[R[p,q] for q in dj] for p in di])
        O[i,j]=np.linalg.det(sub)
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
for i,m in enumerate(ms): C2y[ms.index(-m),i]=(-1)**(m)  # l=2
C2p=Rz(np.pi/4)@C2y@Rz(-np.pi/4)
K4=compound(spin_rep(Rz(np.pi/2))); K2p=compound(spin_rep(C2p))
# spin ops
Sz=np.diag([sum(0.5 if spo[x][1]==0 else -0.5 for x in d) for d in dets])
Sp=np.zeros((N,N))
for j,d in enumerate(dets):
  for m in ms:
    p=spo.index((m,1)); q=spo.index((m,0))
    r=ann(p,d)
    if r:
      s1,x=r; r2=cre(q,x)
      if r2: Sp[idx[r2[1]],j]+=s1*r2[0]
S2=Sp@Sp.T+Sz@Sz-Sz  # S-S+ + Sz^2+Sz ; S-S+ = Sp^T Sp?? 
S2=Sp.T@Sp+Sz@Sz+Sz
V0=onebody(Vm(1.0)).real
def levels(Dq,lab=True):
    H=H2+Dq*V0
    w,U=np.linalg.eigh(H); w=w-w[0]
    out=[];i=0
    while i<N:
        j=i
        while j+1<N and w[j+1]-w[i]<1e-6: j+=1
        Uc=U[:,i:j+1]
        s2=np.trace(Uc.conj().T@S2@Uc).real/(j-i+1)
        S=(-1+np.sqrt(1+4*s2))/2; mult=int(round(2*S+1))
        out.append((w[i],mult,(j-i+1),Uc)); i=j+1
    return out
def label(Uc,mult):
    n=Uc.shape[1]//mult
    c4=np.trace(Uc.conj().T@K4@Uc).real/mult
    c2=np.trace(Uc.conj().T@K2p@Uc).real/mult
    return n,round(c4),round(c2)
names={(1,1,1):'A1',(1,1,-1):'A2',(2,0,0):'E',(3,1,-1):'T1',(3,-1,1):'T2'}
import sys
res=[]
for x in np.arange(0,4.01,.5):
    Dq=x if x>0 else 1e-4
    L=levels(Dq)
    lv=[]
    for e,mult,deg,Uc in L:
        n,a,b=label(Uc,mult)
        lv.append((e,f"{mult}{names.get((n,a,b),str((n,a,b)))}"))
        if len(lv)>=6:break
    if x==0: lv=[(round(e,3),t) for e,t in lv]
    print(x,[(round(e,3),t) for e,t in lv])
E
python3 /tmp/t.py