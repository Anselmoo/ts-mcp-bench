cd $TMPDIR && cat << 'EOF' > d5.py
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    l=2
    return float((-1)**m1*(2*l+1)*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m1,m1-m2,m2))
C={k:{(a,b):ck(k,a,b) for a in ms for b in ms} for k in (2,4)}
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
def two(a,b,c,d,F):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=[so[x] for x in (a,b,c,d)]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.
    return sum(F[k]*C[k][(m1,m3)]*C[k][(m4,m2)] for k in (2,4))
def ann(lst,x):
    i=lst.index(x); return (-1)**i, lst[:i]+lst[i+1:]
def cre(lst,x):
    if x in lst: return 0,None
    i=sum(1 for y in lst if y<x); return (-1)**i, sorted(lst+[x])
def build(Dq,B,Cc):
    F2=B+Cc/7; F4=Cc/35; F={2:49*F2,4:441*F4}
    V=np.zeros((5,5))
    d={-2:Dq,2:Dq,0:6*Dq,1:-4*Dq,-1:-4*Dq}
    for i,m in enumerate(ms): V[i,i]=d[m]
    V[0,4]=V[4,0]=5*Dq
    N=len(dets);H=np.zeros((N,N))
    for I,D in enumerate(dets):
        for p in D:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                val=V[ms.index(so[q][0]),ms.index(so[p][0])]
                if val==0: continue
                sg,l=ann(list(D),p); a,l=cre(l,q)
                if l is None: continue
                H[idx[tuple(l)],I]+=sg*a*val
        for p,q in itertools.combinations(D,2):
            for r,s in itertools.combinations(range(10),2):
                val=two(r,s,p,q,F)-two(r,s,q,p,F)
                if abs(val)<1e-12: continue
                sg=1;l=list(D)
                a,l=ann(l,p);sg*=a
                a,l=ann(l,q);sg*=a
                a,l=cre(l,s)
                if l is None: continue
                sg*=a
                a,l=cre(l,r)
                if l is None: continue
                sg*=a
                H[idx[tuple(l)],I]+=sg*val
    return H
def Sz(D): return sum(0.5 if so[x][1] else -0.5 for x in D)
sel=[i for i,D in enumerate(dets) if Sz(D)==1.5]
sel2=[i for i,D in enumerate(dets) if Sz(D)==2.5]
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc)
    e5=np.linalg.eigvalsh(H[np.ix_(sel2,sel2)])
    e3=list(np.linalg.eigvalsh(H[np.ix_(sel,sel)]))
    for e in e5:
        j=int(np.argmin([abs(x-e) for x in e3])); e3.pop(j)
    g=min(e5); e3=sorted(np.array(e3)-g)
    out=[]
    for x in e3:
        if out and abs(out[-1][0]-x)<1e-3: out[-1][1]+=1
        else: out.append([x,1])
    return out
print(levels(800,700,3000)[:6])
print(levels(0,700,3000)[:6], 10*700+5*3000)
EOF
python3 d5.py