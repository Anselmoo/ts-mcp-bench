import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares, brentq
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
# weak-field sanity
w=levels(50,200,1000); print("weak", np.round(w-w[0],0))
# scan: for C/B=4.5 and C/B=4 find B,Dq fitting first two ratios; report third
obs=np.array([20700,30570,42990.])
for ratio in (4.0,4.5):
  def res(x):
    B,Dq=x; w=levels(B,ratio*B,Dq)
    lv=[]
    for e in w:
        if lv and abs(e-lv[-1][0])<1e-6: lv[-1][1]+=1
        else: lv.append([e,1])
    e=[l_[0]-w[0] for l_ in lv[1:]]
    if len(e)<3: return np.ones(3)*1e3
    return (np.array(e[:3])-obs)/1000.
  best=None
  for B0 in (400,700,1000):
    for D0 in (1200,2000,2800):
      s=least_squares(res,[B0,D0],bounds=([50,100],[3000,6000]))
      if best is None or s.cost<best.cost: best=s
  print("C/B",ratio,"B=%.1f Dq=%.1f"%tuple(best.x),"resid",np.round(res(best.x)*1000,0))
