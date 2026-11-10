import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2; MS=list(range(-2,3))
def w3(*a): return float(wigner_3j(*a))
spo=[(m,s) for m in MS for s in (0,1)]
N=10
A={k:np.zeros((N,N,N,N)) for k in (0,2,4)}
for k in (0,2,4):
  g=(2*l+1)**2*w3(l,k,l,0,0,0)**2
  for p,(mp,sp) in enumerate(spo):
   for q,(mq,sq) in enumerate(spo):
    for r,(mr,sr) in enumerate(spo):
     for s_,(ms_,ss) in enumerate(spo):
      if sp==sr and sq==ss:
        t=sum((-1)**qq*w3(l,k,l,-mp,qq,mr)*w3(l,k,l,-mq,-qq,ms_) for qq in range(-k,k+1))
        A[k][p,q,r,s_]=g*t*((-1)**(mp+mq))
st=[(i,j) for i,j in itertools.combinations(range(N),2) if spo[i][1]==0 and spo[j][1]==0]
Peg=np.zeros((5,5)); Peg[2,2]=1.0; Peg[0,0]=Peg[4,4]=0.5; Peg[0,4]=Peg[4,0]=0.5
def levels(B,C,Dq):
    F={0:0.0,2:49*B+7*C,4:441*C/35}
    V=sum(F[k]*A[k] for k in (0,2,4))
    hm=-4*Dq*np.eye(5)+10*Dq*Peg
    h=np.zeros((N,N))
    for p in range(5):
      for q in range(5):
        for s in (0,1): h[2*p+s,2*q+s]=hm[p,q]
    D=len(st); Hm=np.zeros((D,D))
    for a,(i,j) in enumerate(st):
      for b,(k,m) in enumerate(st):
        Hm[a,b]=V[i,j,k,m]-V[i,j,m,k] + h[i,k]*(j==m) - h[i,m]*(j==k) + h[j,m]*(i==k) - h[j,k]*(i==m)
    return np.sort(np.linalg.eigvalsh(Hm))
def levs(x):
    w=levels(*x)
    lv=[]
    for e in w:
        if lv and abs(e-lv[-1][0])<1e-6: lv[-1][1]+=1
        else: lv.append([e,1])
    g=lv[0][0]
    return [e-g for e,_ in lv[1:]], [d for _,d in lv]
obs=np.array([20700,30570,42990.])
# the three nonground distinct levels: list in energy order; assign observed values
for perm in itertools.permutations(range(3)):
    def res(x):
        e,_=levs(x)
        if len(e)<3: return np.ones(3)*1e3
        return (np.array(e[:3])-obs[list(perm)])/1000.0
    best=None
    for B0 in (300,600,900):
      for r0 in (3,4.5):
        for Dq0 in (800,1200,2000):
          s=least_squares(res,[B0,r0*B0,Dq0],bounds=([50,0,100],[3000,30000,5000]),xtol=1e-12,ftol=1e-12,gtol=1e-12)
          if best is None or s.cost<best.cost: best=s
    x=best.x; e,d=levs(x)
    print(perm,"cost=%.2e"%best.cost,"B=%.1f C=%.1f Dq=%.1f C/B=%.2f"%(x[0],x[1],x[2],x[1]/x[0]),"lev",np.round(e,0),d)
