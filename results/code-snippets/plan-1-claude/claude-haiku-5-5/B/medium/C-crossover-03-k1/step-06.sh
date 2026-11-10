python3 - << 'EOF'
import numpy as np
from scipy.special import sph_harm_y
from scipy.optimize import brentq
B,C=803.0,3078.0
F2=49*B+7*C; F4=C*441/35
ms=[-2,-1,0,1,2]
nt,nph=60,120
x,w=np.polynomial.legendre.leggauss(nt)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*2*np.pi/nph
def Y(l,m): return sph_harm_y(l,m,TH,PH)
v=Y(4,0)+np.sqrt(5/14)*(Y(4,4)+Y(4,-4))
M=np.array([[np.sum(W*np.conj(Y(2,a))*v*Y(2,b)) for b in ms] for a in ms])
M=(M+M.conj().T)/2
H1=M*(6.0/0.241796)
print("per Dq:",np.round(np.linalg.eigvalsh(H1),6))
def ang_k(k):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q)
        f1=np.zeros((5,5),complex); f2=np.zeros((5,5),complex)
        for a,ma in enumerate(ms):
            for b,mb in enumerate(ms):
                pa=np.conj(Y(2,ma))*Y(2,mb)
                f1[a,b]=np.sum(W*pa*np.conj(Ykq))
                f2[a,b]=np.sum(W*pa*Ykq)
        A+=np.einsum('ab,cd->abcd',f1,f2)
    return 4*np.pi/(2*k+1)*A
Vorb=F2*ang_k(2)+F4*ang_k(4)
nso=10; dim=2**nso
def idx(m,s): return ms.index(m)*2+s
def cdag(p):
    op=np.zeros((dim,dim))
    for st in range(dim):
        if not (st>>p)&1:
            op[st|(1<<p),st]=(-1)**bin(st&((1<<p)-1)).count('1')
    return op
Cd=[cdag(p) for p in range(nso)]; Cs=[c.T.copy() for c in Cd]
keep=[st for st in range(dim) if bin(st).count('1')==6]
def sub(X): return X[np.ix_(keep,keep)]
Sz=sum(0.5*(Cd[idx(m,0)]@Cs[idx(m,0)]-Cd[idx(m,1)]@Cs[idx(m,1)]) for m in ms)
Sp=sum(Cd[idx(m,0)]@Cs[idx(m,1)] for m in ms)
S2=Sp.T@Sp+Sz@Sz+Sz
Hee=np.zeros((dim,dim)); h1=np.zeros((dim,dim))
for i in range(5):
 for k in range(5):
  for j in range(5):
   for l in range(5):
    val=Vorb[i,k,j,l].real
    if abs(val)<1e-9: continue
    for si in range(2):
     for sj in range(2):
      p=idx(ms[i],si); r=idx(ms[k],si); q=idx(ms[j],sj); s=idx(ms[l],sj)
      Hee+=0.5*val*(Cd[p]@Cd[q]@Cs[s]@Cs[r])
for a in range(5):
 for b in range(5):
  for s in range(2):
   h1+=H1[a,b].real*(Cd[idx(ms[a],s)]@Cs[idx(ms[b],s)])
Hee6=sub(Hee); h16=sub(h1); S26=sub(S2); Szd=np.diag(sub(Sz))
def sector(Ms2): return np.where(np.abs(Szd-Ms2/2)<1e-9)[0]
def E_quintet(Dq):
    H=Dq*h16+Hee6; ii=sector(4)
    return np.linalg.eigvalsh(H[np.ix_(ii,ii)])[0]
def E_singlet(Dq):
    H=Dq*h16+Hee6; ii=sector(0)
    return np.linalg.eigvalsh(H[np.ix_(ii,ii)]+1e6*S26[np.ix_(ii,ii)])[0]
# sanity: free ion 5D vs 1S (Dq=0), should be 1S-5D = 7B+7C ? (check)
e5=E_quintet(0); e1=E_singlet(0)
print("free: E1S-E5D =",e1-e5," 7B+7C=",7*B+7*C)
for Dq in [0,1000,2000,3000]:
    print(Dq, E_quintet(Dq)-e5, E_singlet(Dq)-e5)
r=brentq(lambda d: E_singlet(d)-E_quintet(d),500,6000)
print("crossover Dq =",r," Dq/B=",r/B)
EOF