python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
from functools import lru_cache
l=2
@lru_cache(None)
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    g=float(gaunt(l,k,l,-m1,q,m2))*(-1)**m1
    return np.sqrt(4*np.pi/(2*k+1))*g
def U(m1,m2,m3,m4,F):
    if m1+m2!=m3+m4: return 0.0
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*F[k] for k in (2,4))
def srt(arr):
    arr=list(arr); sign=1
    for i in range(len(arr)):
        for j in range(len(arr)-1-i):
            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sign=-sign
    return tuple(arr),sign
ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),3)); idx={d:i for i,d in enumerate(dets)}
def build(Dq,B,C):
    F4p=C/35; F2p=B+5*F4p; F={2:49*F2p,4:441*F4p}
    V=np.zeros((5,5)); d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): V[i,i]=d[m]*Dq
    V[0,4]=V[4,0]=5*Dq
    H=np.zeros((120,120))
    for det in dets:
        for p,a in enumerate(det):
            for b in range(10):
                if so[b][1]!=so[a][1]: continue
                v=V[ms.index(so[b][0]),ms.index(so[a][0])]
                if v==0 or (b!=a and b in det): continue
                new=list(det); new[p]=b; nd,s=srt(new); H[idx[nd],idx[det]]+=s*v
        for (p,q) in itertools.combinations(range(3),2):
            a,b=det[p],det[q]
            for c in range(10):
                for d_ in range(10):
                    if c==d_: continue
                    if (c in det and c not in (a,b)) or (d_ in det and d_ not in (a,b)): continue
                    if so[c][1]!=so[a][1] or so[d_][1]!=so[b][1]: continue
                    v=U(so[c][0],so[d_][0],so[a][0],so[b][0],F)
                    if v==0: continue
                    new=list(det); new[p]=c; new[q]=d_; nd,s=srt(new)
                    H[idx[nd],idx[det]]+=0.5*s*v
    return H
def levels(Dq,B,C):
    e=np.linalg.eigvalsh(build(Dq,B,C)); e=e-e[0]; out=[]
    for x in e:
        if out and abs(out[-1][0]-x)<0.5: out[-1][1]+=1
        else: out.append([x,1])
    return out
print(levels(0,1000,4000)[:5])  # free ion check: 4F=0, 4P=15B, 2G=4B+3C
print(levels(1750,610.9,3574)[:6])
def f(C):
    L=levels(1750,610.9,C); return [x for x,g in L if g==4 and 1<x<17000][0]-14300
Cs=brentq(f,2500,5000); print(Cs, levels(1750,610.9,Cs)[:5])
EOF