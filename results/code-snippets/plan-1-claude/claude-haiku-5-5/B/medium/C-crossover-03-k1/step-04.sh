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
def Y(l,m,T,P): return sph_harm_y(l,m,T,P)
v = Y(4,0,TH,PH) + np.sqrt(10/7)*(Y(4,4,TH,PH)+Y(4,-4,TH,PH))
M=np.zeros((5,5),complex)
for i,mi in enumerate(ms):
    for j,mj in enumerate(ms):
        M[i,j]=np.sum(W*np.conj(Y(2,mi,TH,PH))*v*Y(2,mj,TH,PH))
M=(M+M.conj().T)/2
ev,U=np.linalg.eigh(M)
print("raw eig",np.round(ev,6))
lam_e = ev[0] if abs(ev[0]-ev[1])<1e-8 else ev[3]
H1 = M*(6.0/lam_e)
print("check per Dq:",np.round(np.linalg.eigvalsh(H1),6))
def ang_k(k):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q,TH,PH)
        f1=np.zeros((5,5),complex); f2=np.zeros((5,5),complex)
        for a,ma in enumerate(ms):
            for b,mb in enumerate(ms):
                pa=np.conj(Y(2,ma,TH,PH))*Y(2,mb,TH,PH)
                f1[a,b]=np.sum(W*pa*np.conj(Ykq))
                f2[a,b]=np.sum(W*pa*Ykq)
        A+=np.einsum('ab,cd->abcd',f1,f2)
    return 4*np.pi/(2*k+1)*A
A2=ang_k(2); A4=ang_k(4)
Vorb=F2*A2+F4*A4
nso=10; dim=2**nso
def idx(m,s): return ms.index(m)*2+s
def cdag(p):
    op=np.zeros((dim,dim))
    for st in range(dim):
        if not (st>>p)&1:
            sign=(-1)**bin(st & ((1<<p)-1)).count('1')
            op[st|(1<<p),st]=sign
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
    val=Vorb[i,k,j,l]
    if abs(val)<1e-12: continue
    for si in range(2):
     for sj in range(2):
      p=idx(ms[i],si); r=idx(ms[k],si); q=idx(ms[j],sj); s=idx(ms[l],sj)
      Hee+=0.5*val.real*(Cd[p]@Cd[q]@Cs[s]@Cs[r])
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
for Dq in [0,1000,2000,2500,3000]:
    print(Dq, E_quintet(Dq), E_singlet(Dq))
f=lambda d: E_singlet(d)-E_quintet(d)
r=brentq(f,1000,6000)
print("crossover Dq =",r, "E5=",E_quintet(r), "Dq/B=",r/B)
EOF