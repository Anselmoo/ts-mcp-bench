cd $TMPDIR && cat << 'EOF' > d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2; ms=[-2,-1,0,1,2]
so=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(l,k,l,-m1,q,m2))
C={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
def two(i,j,k_,l_,F):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[i],so[j],so[k_],so[l_]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.0
    return sum(C[(k,m1,m3)]*C[(k,m4,m2)]*F[k] for k in (2,4))
def cf(m1,m2,Dq):
    if m1==m2: return {0:6,1:-4,-1:-4,2:1,-2:1}[m1]*Dq
    if abs(m1-m2)==4: return 5*Dq
    return 0.0
n=7
dets=list(itertools.combinations(range(10),n)); idx={d:i for i,d in enumerate(dets)}
def build(B,Cc):
    F={2:49*B+7*Cc,4:441*Cc/35}
    N=len(dets); M=np.zeros((N,N)); V=np.zeros((N,N))
    for I,d in enumerate(dets):
        for pos,p in enumerate(d):
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=cf(so[q][0],so[p][0],1.0)
                if v==0 or (q!=p and q in d): continue
                lst=list(d); lst.pop(pos)
                sgn=(-1)**pos*(-1)**sum(1 for x in lst if x<q)
                V[idx[tuple(sorted(lst+[q]))],I]+=v*sgn
        for a,b in itertools.combinations(range(n),2):
            p,q=d[a],d[b]; lst=list(d); lst.pop(b); lst.pop(a)
            sgn0=(-1)**(a+b-1)
            for r in range(10):
                for s in range(r+1,10):
                    if r in lst or s in lst: continue
                    v=two(r,s,p,q,F)-two(r,s,q,p,F)
                    if abs(v)<1e-12: continue
                    l2=list(lst); sg=(-1)**sum(1 for x in l2 if x<s); l2=sorted(l2+[s])
                    sg*=(-1)**sum(1 for x in l2 if x<r); l2=sorted(l2+[r])
                    M[idx[tuple(l2)],I]+=v*sg*sgn0
    return M,V
def Sz(d): return sum(1 if so[x][1]==1 else -1 for x in d)/2
B,Cc=922.,4156.
M,V=build(B,Cc)
print(np.abs(M-M.T).max(),np.abs(V-V.T).max())
sec={S:[i for i,d in enumerate(dets) if Sz(d)==S] for S in (1.5,0.5)}
def lows(Dq):
    T=M+Dq*V
    return {S:np.linalg.eigvalsh(T[np.ix_(ii,ii)]) for S,ii in sec.items()}
o=lows(0.0); e0=o[1.5][0]
print(np.unique(np.round(o[1.5]-e0,1)), 15*B)
print(np.unique(np.round(o[0.5]-e0,1))[:6], "2G expected 4B+3C=",4*B+3*Cc)
o=lows(1000.); print(np.unique(np.round(o[1.5]-o[1.5][0],0)))
f=lambda Dq: lows(Dq)[0.5][0]-lows(Dq)[1.5][0]
for Dq in [1000,1500,2000,2500,3000]: print(Dq,f(Dq))
r=brentq(f,500,5000,xtol=1e-8); print(r, r/B)
EOF
python3 d7.py