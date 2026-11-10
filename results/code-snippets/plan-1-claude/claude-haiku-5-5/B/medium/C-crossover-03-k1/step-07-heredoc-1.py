import numpy as np
from scipy.special import sph_harm_y
B,C=1.0,0.0
ms=[-2,-1,0,1,2]
nt,nph=60,120
x,w=np.polynomial.legendre.leggauss(nt)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*2*np.pi/nph
def Y(l,m): return sph_harm_y(l,m,TH,PH)
def ang_k(k):
    A=np.zeros((5,5,5,5),complex)
    for q in range(-k,k+1):
        Ykq=Y(k,q)
        f1=np.zeros((5,5),complex); f2=np.zeros((5,5),complex)
        for a,ma in enumerate(ms):
            for b,mb in enumerate(ms):
                pa=np.conj(Y(2,ma))*Y(2,mb)
                f1[a,b]=np.sum(W*pa*np.conj(Ykq)); f2[a,b]=np.sum(W*pa*Ykq)
        A+=np.einsum('ab,cd->abcd',f1,f2)
    return 4*np.pi/(2*k+1)*A
A2=ang_k(2).real; A4=ang_k(4).real
# Slater: F2=49B+7C,F4=12.6C ; with B=1,C=0 => F2=49,F4=0 ; check
def run(N,F2,F4):
    Vorb=F2*A2+F4*A4
    nso=10; dim=2**nso
    def idx(m,s): return ms.index(m)*2+s
    def cdag(p):
        op=np.zeros((dim,dim))
        for st in range(dim):
            if not (st>>p)&1: op[st|(1<<p),st]=(-1)**bin(st&((1<<p)-1)).count('1')
        return op
    Cd=[cdag(p) for p in range(nso)]; Cs=[c.T.copy() for c in Cd]
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
    return H,S2,np.diag(Sz)
H,S2,Sz=run(2,49.0,0.0)
ev=np.linalg.eigh(H+1e4*S2)[0]
print("d2 Sz0-ish levels (B=1,C=0 form, F2=49):",np.round(np.sort(np.linalg.eigvalsh(H)),4))
