import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
l=2; ms=[-2,-1,0,1,2]
# spin-orbitals (m, s)
so=[(m,s) for m in ms for s in (0,1)]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * <l m1|Y_k(m1-m2)|l m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*gaunt(l,k,l,-m1,q,m2)*np.sqrt(1.0)) 
C={}
for k in (0,2,4):
    for a in ms:
        for b in ms: C[(k,a,b)]=ck(k,a,b)
def Rk(B,Cc):
    F2=49*B+7*Cc; F4=441*Cc/35
    return {0:0.0,2:F2,4:F4}
def two(i,j,k_,l_,F):  # <ij|1/r|kl>
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[i],so[j],so[k_],so[l_]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.0
    return sum(C[(k,m1,m3)]*C[(k,m4,m2)]*F[k] for k in (2,4))
def cf(m1,m2,Dq):
    # octahedral: V = Dq terms; in real basis eg=+6Dq, t2g=-4Dq; in complex basis
    if m1==m2: return {0:6,1:-4,-1:-4,2:1,-2:1}[m1]*Dq
    if abs(m1-m2)==4: return 5*Dq
    return 0.0
n=7
dets=list(itertools.combinations(range(10),n))
idx={d:i for i,d in enumerate(dets)}
def H(Dq,B,Cc):
    F=Rk(B,Cc); N=len(dets); M=np.zeros((N,N))
    for I,d in enumerate(dets):
        # one-body
        for p in d:
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=cf(so[q][0],so[p][0],Dq)
                if v==0: continue
                if q!=p and q in d: continue
                nd=list(d); pos=nd.index(p); nd[pos]=q
                sign=(-1)**sum(1 for x in nd if x<q and x!=q) * (-1)**pos
                # compute sign properly via sorting
                lst=list(d); lst.pop(pos); 
                sgn=(-1)**pos
                k=sum(1 for x in lst if x<q); sgn*=(-1)**k
                J=idx[tuple(sorted(lst+[q]))]; M[J,I]+=v*sgn
        # two-body: sum_{p<q in d, r<s} (<rs|pq>-<rs|qp>) a_r+ a_s+ a_q a_p
        for a,b in itertools.combinations(range(n),2):
            p,q=d[a],d[b]
            lst=list(d); lst.pop(b); lst.pop(a)
            sgn0=(-1)**(a+b-1)  # remove p then q  (a_q a_p acting)
            for r in range(10):
                for s in range(10):
                    if r>=s: continue
                    if r in lst or s in lst: continue
                    v=two(r,s,p,q,F)-two(r,s,q,p,F)
                    if abs(v)<1e-12: continue
                    # create s then r: a_r+ a_s+
                    l2=list(lst); k=sum(1 for x in l2 if x<s); sg=(-1)**k; l2=sorted(l2+[s])
                    k=sum(1 for x in l2 if x<r); sg*=(-1)**k; l2=sorted(l2+[r])
                    M[idx[tuple(l2)],I]+=v*sg*sgn0
    return M
def Sz(d): return sum(1 if so[x][1]==1 else -1 for x in d)/2
B,Cc=922.,4156.
# select MS=3/2 and MS=1/2 sectors
def lows(Dq):
    M=H(Dq,B,Cc)
    assert np.allclose(M,M.T)
    out={}
    for S in (1.5,0.5):
        ii=[i for i,d in enumerate(dets) if Sz(d)==S]
        out[S]=np.linalg.eigvalsh(M[np.ix_(ii,ii)])
    return out
# free ion check
o=lows(0.0); print(np.round(o[1.5][:5]-o[1.5][0],1)); print(np.round(np.unique(np.round(o[0.5]-o[1.5][0],1))[:10]))
def f(Dq):
    o=lows(Dq); return o[0.5][0]-o[1.5][0]
for Dq in [1000,1500,2000,2500,3000]: print(Dq,f(Dq))
r=brentq(f,1000,4000,xtol=1e-6); print(r)
