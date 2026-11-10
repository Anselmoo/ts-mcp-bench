python3 - << 'EOF'
import numpy as np
from scipy.special import sph_harm_y
ms=[-2,-1,0,1,2]
nt,nph=60,120
x,w=np.polynomial.legendre.leggauss(nt)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*2*np.pi/nph
def Y(l,m): return sph_harm_y(l,m,TH,PH)
def ang_k(k):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q); f1=np.zeros((5,5),complex); f2=np.zeros((5,5),complex)
        for a,ma in enumerate(ms):
            for b,mb in enumerate(ms):
                pa=np.conj(Y(2,ma))*Y(2,mb)
                f1[a,b]=np.sum(W*pa*np.conj(Ykq)); f2[a,b]=np.sum(W*pa*Ykq)
        A+=np.einsum('ab,cd->abcd',f1,f2)
    return 4*np.pi/(2*k+1)*A
A2=ang_k(2).real; A4=ang_k(4).real
def run(N,F2,F4):
    Vorb=F2*A2+F4*A4
    dim=1024
    def idx(m,s): return ms.index(m)*2+s
    def cdag(p):
        op=np.zeros((dim,dim))
        for st in range(dim):
            if not (st>>p)&1: op[st|(1<<p),st]=(-1)**bin(st&((1<<p)-1)).count('1')
        return op
    Cd=[cdag(p) for p in range(10)]; Cs=[c.T.copy() for c in Cd]
    keep=[st for st in range(dim) if bin(st).count('1')==N]
    Hee=np.zeros((dim,dim))
    for i in range(5):
     for k in range(5):
      for j in range(5):
       for l in range(5):
        val=Vorb[i,k,j,l]
        if abs(val)<1e-9: continue
        for si in range(2):
         for sj in range(2):
          p=idx(ms[i],si); r=idx(ms[k],si); q=idx(ms[j],sj); s=idx(ms[l],sj)
          Hee+=0.5*val*(Cd[p]@Cd[q]@Cs[s]@Cs[r])
    H=Hee[np.ix_(keep,keep)]
    Sz=sum(0.5*(Cd[idx(m,0)]@Cs[idx(m,0)]-Cd[idx(m,1)]@Cs[idx(m,1)]) for m in ms)[np.ix_(keep,keep)]
    Sp=sum(Cd[idx(m,0)]@Cs[idx(m,1)] for m in ms)[np.ix_(keep,keep)]
    S2=Sp.T@Sp+Sz@Sz+Sz
    return H,S2
B,C=1.0,1.0
F2=49*B+7*C; F4=12.6*C
H,S2=run(2,F2,F4)
Ev=np.linalg.eigvalsh(H+1e4*S2)
print("d2 levels with B=C=1 (sum over states):", np.round(np.unique(np.round(np.linalg.eigvalsh(H),3)),3))
H6,S6=run(6,F2,F4)
print("d6 pair check: lowest with 5D-like?", np.round(np.unique(np.round(np.linalg.eigvalsh(H6),3)),3)[:5])
EOF