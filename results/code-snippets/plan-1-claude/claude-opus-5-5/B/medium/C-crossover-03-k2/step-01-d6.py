import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2): # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) <m1|Y_k,m1-m2|m2>
    q=m1-m2
    if abs(q)>k: return 0.
    return float(((-1)**m1)*np.sqrt(4*np.pi/(2*k+1))*5*gaunt(2,k,2,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def two(a,b,c,d,F): # <ab|1/r|cd>
    if a[1]!=c[1] or b[1]!=d[1]: return 0.
    if a[0]+b[0]!=c[0]+d[0]: return 0.
    return sum(F[k]*C[(k,a[0],c[0])]*C[(k,d[0],b[0])] for k in (0,2,4))
V=np.zeros((5,5))
for i,m in enumerate(ms):
    V[i,i]={2:1,1:-4,0:6}[abs(m)]
V[0,4]=V[4,0]=5
dets=[d for d in itertools.combinations(range(10),6)]
dets=[d for d in dets if sum(1 if orbs[i][1] else -1 for i in d)==0]  # Ms=0
idx={d:i for i,d in enumerate(dets)}
def H(Dq,B,Cc):
    F4=Cc/35; F2=B+5*F4; F={0:0,2:F2,4:F4}
    N=len(dets); M=np.zeros((N,N))
    h=np.zeros((10,10))
    for p in range(10):
        for q in range(10):
            if orbs[p][1]==orbs[q][1]: h[p,q]=Dq*V[ms.index(orbs[p][0]),ms.index(orbs[q][0])]
    g={}
    for d in dets:
        I=idx[d]
        # one-body
        for p in d:
            for q in range(10):
                if h[q,p]==0: continue
                if q!=p and q in d: continue
                new=list(d); pos=new.index(p); new[pos]=q
                sgn=1
                perm=sorted(range(6),key=lambda i:new[i]); 
                # sign of permutation
                arr=new[:]; s=1
                for i in range(6):
                    for j in range(i+1,6):
                        if arr[i]>arr[j]: s=-s
                M[idx[tuple(sorted(new))],I]+=s*h[q,p]
        # two-body: 1/2 sum a+b+ d c
        for i1 in range(6):
            for i2 in range(6):
                if i1==i2: continue
                c,dd=d[i1],d[i2]
                for a in range(10):
                    for b in range(10):
                        if a==b: continue
                        val=two(orbs[a],orbs[b],orbs[c],orbs[dd],F)
                        if val==0: continue
                        # apply a+ b+ dd c  : remove c then dd, add b then a
                        lst=list(d); s=1
                        pc=lst.index(c); s*=(-1)**pc; lst.pop(pc)
                        pd=lst.index(dd); s*=(-1)**pd; lst.pop(pd)
                        if b in lst or a in lst: continue
                        lst=[b]+lst; lst=[a]+lst
                        arr=lst[:]
                        for i in range(6):
                            for j in range(i+1,6):
                                if arr[i]>arr[j]: s=-s
                        M[idx[tuple(sorted(lst))],I]+=0.5*s*val
    return M
import functools
B,Cc=803,3078
def S2(d): pass
def gap(Dq):
    M=H(Dq,B,Cc); w,v=np.linalg.eigh(M)
    return w,v
# identify spins via S^2 cheaply: check degeneracy pattern; ground of quintet T2 is 15-fold (Ms=0 gives 3), singlet A1 is 1
for Dq in [1500,2000,2500,3000]:
    w,v=gap(Dq); print(Dq,np.round(w[:6]-w[0],1))
