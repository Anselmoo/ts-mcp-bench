import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def c(k,m,mp):
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
C={k:np.array([[c(k,m,mp) for mp in ms] for m in ms]) for k in (0,2,4)}
so=[(m,s) for m in ms for s in (0,1)]
dets=[sum(1<<i for i in comb) for comb in itertools.combinations(range(10),7)]
idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,Cc):
    R={0:0,2:49*B+7*Cc,4:63*Cc/5}
    h=np.zeros((5,5)); 
    for m,v in zip([-1,0,1],[-4,6,-4]): h[m+2,m+2]=v*Dq
    h[0,0]=h[4,4]=Dq; h[0,4]=h[4,0]=5*Dq
    def g(a,b,cc,d): # <a b|g|c d>
        if a+b!=cc+d: return 0
        return sum(R[k]*C[k][a+2,cc+2]*C[k][d+2,b+2] for k in (2,4))
    H=np.zeros((120,120))
    def apply(d,ops): # ops list of (i,create?) applied right to left
        sign=1
        for i,cr in reversed(ops):
            if cr==(d>>i&1): return None,0
            n=bin(d&((1<<i)-1)).count('1')
            if n%2: sign=-sign
            d^=1<<i
        return d,sign
    N=10
    for d in dets:
        j=idx[d]
        for p in range(N):
            for q in range(N):
                if so[p][1]!=so[q][1]: continue
                v=h[so[p][0]+2,so[q][0]+2]
                if v==0: continue
                d2,s=apply(d,[(p,1),(q,0)])
                if s: H[idx[d2],j]+=v*s
        for k1 in range(N):
          for l1 in range(N):
            for p in range(N):
              for q in range(N):
                # 1/2 <p q|g|k l> a+p a+q a_l a_k
                if so[p][1]!=so[k1][1] or so[q][1]!=so[l1][1]: continue
                v=g(so[p][0],so[q][0],so[k1][0],so[l1][0])
                if v==0: continue
                d2,s=apply(d,[(p,1),(q,1),(l1,0),(k1,0)])
                if s: H[idx[d2],j]+=0.5*v*s
    return H
# S^2 via Sz only? use Sz and diagonalize H+small*S2 ; instead compute S2 matrix
def S2():
    M=np.zeros((120,120))
    def ap(d,i,cr):
        if cr==(d>>i&1): return None,0
        n=bin(d&((1<<i)-1)).count('1'); return d^(1<<i),(-1)**n
    for d in dets:
        j=idx[d]
        sz=sum((1 if (d>>i&1) else 0)*(0.5 if so[i][1]==0 else -0.5) for i in range(10))
        M[j,j]+=sz*sz-sz  # S-S+ = S2 - Sz^2 - Sz => S2 = S-S+ + Sz^2+Sz
        # S+ : beta->alpha ; then S-: alpha->beta
        for a in range(5):
            ia=2*a; ib=2*a+1
            d1,s1=ap(d,ib,0)
            if not s1: continue
            d1,s2=ap(d1,ia,1)
            if not s2: continue
            for b in range(5):
                ja=2*b; jb=2*b+1
                e1,t1=ap(d1,ja,0)
                if not t1: continue
                e2,t2=ap(e1,jb,1)
                if not t2: continue
                M[idx[e2],j]+=s1*s2*t1*t2
    return M
S2M=S2()
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc)
    w,v=np.linalg.eigh(H+1e-3*S2M) if False else np.linalg.eigh(H)
    # classify within degenerate groups
    out=[]
    i=0
    while i<120:
        j=i
        while j<120 and abs(w[j]-w[i])<1e-6: j+=1
        V=v[:,i:j]; s2=np.trace(V.T@S2M@V)/(j-i)
        S=(-1+np.sqrt(1+4*s2))/2
        out.append((w[i],j-i,round(2*S+1)))
        i=j
    return out
if __name__=="__main__":
    for l in levels(0,1000,4000)[:6]: print(l)
