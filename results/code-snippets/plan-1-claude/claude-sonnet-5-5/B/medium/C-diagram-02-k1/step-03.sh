cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.linalg import expm
B=814.;C=3902.
F={2:49*(B+C/7),4:441*C/35}
l=2;ms=[-2,-1,0,1,2]
def c(k,m,mp):
    q=m-mp
    if abs(q)>k:return 0.
    return float((-1)**m*5*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m,q,mp))
ck={k:np.array([[c(k,m,mp) for mp in ms] for m in ms]) for k in (2,4)}
so=[(m,s) for s in (0,1) for m in ms]
dets=[sum(1<<i for i in comb) for comb in itertools.combinations(range(10),4)]
idx={d:i for i,d in enumerate(dets)}
def ap(op,d,create):
    if create==bool(d>>op&1):return 0,0
    return (-1)**bin(d&((1<<op)-1)).count('1'),d^(1<<op)
g=[]
for a,(ma,sa) in enumerate(so):
 for b,(mb,sb) in enumerate(so):
  for cc,(mc,sc) in enumerate(so):
   for d,(md,sd) in enumerate(so):
    if sa!=sc or sb!=sd or ma+mb!=mc+md:continue
    v=sum(ck[k][ma+2,mc+2]*ck[k][md+2,mb+2]*F[k] for k in (2,4))
    if abs(v)>1e-9:g.append((a,b,cc,d,v))
Hee=np.zeros((210,210))
for j,d0 in enumerate(dets):
  for a,b,cc,d,v in g:
    x=d0;sg=1
    for op,cr in ((d,False),(cc,False),(b,True),(a,True)):
      s,x=ap(op,x,cr)
      if not s:sg=0;break
      sg*=s
    if sg:Hee[idx[x],j]+=0.5*v*sg
def one(h):
    M=np.zeros((210,210));H10=np.kron(np.eye(2),h)
    for j,d0 in enumerate(dets):
      for p in range(10):
        for q in range(10):
          if H10[p,q]==0:continue
          s1,x=ap(q,d0,False)
          if not s1:continue
          s2,x=ap(p,x,True)
          if not s2:continue
          M[idx[x],j]+=H10[p,q]*s1*s2
    return M
def minors(U):
    U10=np.kron(np.eye(2),U);M=np.zeros((210,210),complex)
    rs=[[k for k in range(10) if d>>k&1] for d in dets]
    for i in range(210):
      for j in range(210):
        M[i,j]=np.linalg.det(U10[np.ix_(rs[i],rs[j])])
    return M
Lp=np.array([[ (np.sqrt(6-m*(m+1)) if mm==m+1 else 0) for m in ms] for mm in ms],float)
Lz=np.diag(ms).astype(float);Lx=(Lp+Lp.T)/2;Ly=(Lp-Lp.T)/(2j)
C4=minors(expm(-1j*np.pi/2*Lz)); C2p=minors(expm(-1j*np.pi*(Lx+Ly)/np.sqrt(2)))
Sp=np.zeros((210,210))
for j,d0 in enumerate(dets):
  for i in range(5):
    s1,x=ap(i,d0,False)
    if not s1:continue
    s2,x=ap(5+i,x,True)
    if not s2:continue
    Sp[idx[x],j]+=s1*s2
Sz=np.diag([(sum(1 for k in range(5,10) if d>>k&1)-sum(1 for k in range(5) if d>>k&1))/2 for d in dets])
S2=Sp@Sp.T+Sz@Sz-Sz
def hcf(Dq):
    h=np.diag([Dq,-4*Dq,6*Dq,-4*Dq,Dq]).astype(float);h[0,4]=h[4,0]=5*Dq;return h
pts=[]
rr=list(np.arange(0,4.01,.5))
for r in rr:
    Dq=max(r,1e-3)*B
    w,v=np.linalg.eigh(Hee+one(hcf(Dq)))
    lv=[];i=0
    while i<210:
        j=i
        while j<210 and w[j]-w[i]<1e-5*B:j+=1
        V=v[:,i:j];dim=j-i
        s2=np.trace(V.T@S2@V)/dim;S=(-1+np.sqrt(1+4*s2))/2;mult=round(2*S+1)
        od=dim//mult
        x4=np.trace(V.conj().T@C4@V).real/mult;x2=np.trace(V.conj().T@C2p@V).real/mult
        nm=('T2' if x4<-.5 else 'T1') if od==3 else 'E' if od==2 else ('A1' if x2>0 else 'A2')
        lv.append((w[i],f"{mult}{nm}g"));i=j
    e0=lv[0][0]
    pts.append([(t,(e-e0)/B) for e,t in lv[:8]])
    print(r,[(t,round(e,3)) for t,e in pts[-1]])
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
E
python3 a.py