import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
from collections import Counter
ms=[-2,-1,0,1,2]
def c(k,m1,m2):
    return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
C={k:np.array([[c(k,a,b) for b in ms] for a in ms]) for k in (2,4)}
s=1/np.sqrt(2); idx={m:i for i,m in enumerate(ms)}
U=np.zeros((5,5),complex)
def setr(r,d):
    for m,v in d.items(): U[r,idx[m]]=v
setr(0,{2:-1j*s,-2:1j*s});setr(1,{1:1j*s,-1:1j*s});setr(2,{0:1});setr(3,{1:-s,-1:s});setr(4,{2:s,-2:s})
dets_all=list(itertools.combinations(range(10),7))
def H(Dq,B,Cc,Ms2):
    F={2:49*B+7*Cc,4:63*Cc/5}
    V=sum(F[k]*np.einsum('ac,db->abcd',C[k],C[k]) for k in (2,4)).astype(complex)
    V=np.einsum('ia,jb,kc,ld,abcd->ijkl',U.conj(),U.conj(),U,U,V)
    h=np.diag([-4*Dq,-4*Dq,6*Dq,-4*Dq,6*Dq])
    dets=[d for d in dets_all if sum(1 if p%2==0 else -1 for p in d)==Ms2]
    di={d:i for i,d in enumerate(dets)}
    Hm=np.zeros((len(dets),)*2,complex)
    def ann(l,x):
        i=l.index(x);l.pop(i);return (-1)**i
    def cre(l,x):
        pos=sum(1 for y in l if y<x);l.insert(pos,x);return (-1)**pos
    for I,d in enumerate(dets):
        for p in d: Hm[I,I]+=h[p//2,p//2]
        for r,s_ in itertools.permutations(d,2):
            rest=[x for x in d if x not in(r,s_)]
            for p in range(10):
                for q in range(10):
                    if p==q or p%2!=r%2 or q%2!=s_%2 or p in rest or q in rest: continue
                    val=V[p//2,q//2,r//2,s_//2]
                    if abs(val)<1e-12: continue
                    lst=list(d);sg=ann(lst,r)*ann(lst,s_)*cre(lst,q)*cre(lst,p)
                    Hm[di[tuple(lst)],I]+=0.5*sg*val
    return Hm
def lev(Dq,B,Cc,Ms2):
    e=np.linalg.eigvalsh(H(Dq,B,Cc,Ms2)); return e-0
if __name__=="__main__":
    e=lev(900,900,3500,3); e=e-e.min()
    print(sorted(Counter(np.round(e,0)).items()))
