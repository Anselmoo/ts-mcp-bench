
cd <SANDBOX_TMP>/tmp.y4sON0ia4r
cat << 'EOF' > d5.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (1,-1)]
def ck(k,m1,m2):
    return float((-1)**m1*5*np.sqrt(4*np.pi/(2*k+1))*gaunt(2,k,2,-m1,m1-m2,m2)) if abs(m1-m2)<=k else 0.
C={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml}
def R(a,b,c,d,F):
    if a[1]!=c[1] or b[1]!=d[1] or a[0]+b[0]!=c[0]+d[0]: return 0
    return sum(F[k]*C[(k,a[0],c[0])]*C[(k,d[0],b[0])] for k in (0,2,4))
def hcf(Dq):
    h=np.zeros((5,5));i={m:j for j,m in enumerate(ml)}
    h[i[0],i[0]]=6*Dq;h[i[1],i[1]]=h[i[-1],i[-1]]=-4*Dq;h[i[2],i[2]]=h[i[-2],i[-2]]=Dq
    h[i[2],i[-2]]=h[i[-2],i[2]]=5*Dq;return h
dets=list(itertools.combinations(range(10),5))
idx={d:n for n,d in enumerate(dets)}
def par(l):
    l2=sorted(l);perm=[l.index(x) for x in l2];return tuple(l2),np.linalg.det(np.eye(5)[perm])
def build(Dq,B,Cc):
    F={0:0,2:49*B+7*Cc,4:441*Cc/35}
    N=len(dets);H=np.zeros((N,N));h=hcf(Dq)
    for n,d in enumerate(dets):
        for k,p in enumerate(d):
            for q in range(10):
                if so[q][1]!=so[p][1]: continue
                v=h[ml.index(so[q][0]),ml.index(so[p][0])]
                if v==0 or (q!=p and q in d): continue
                l=list(d);l[k]=q;t,sg=par(l);H[idx[t],n]+=v*sg
        for i1,j1 in itertools.combinations(range(5),2):
            p,q=d[i1],d[j1]
            for r in range(10):
                for s in range(10):
                    if r==s: continue
                    if (r in d and r not in (p,q)) or (s in d and s not in (p,q)): continue
                    v=R(so[r],so[s],so[p],so[q],F)-R(so[s],so[r],so[p],so[q],F)
                    if abs(v)<1e-12: continue
                    l=list(d);l[i1]=r;l[j1]=s;t,sg=par(l);H[idx[t],n]+=0.5*v*sg
    return H
def S2():
    N=len(dets);Sz=np.zeros(N);Sp=np.zeros((N,N))
    for n,d in enumerate(dets):
        Sz[n]=sum(so[p][1] for p in d)/2
        for k,p in enumerate(d):
            if so[p][1]==-1:
                q=p-1
                if q in d: continue
                l=list(d);l[k]=q;t,sg=par(l);Sp[idx[t],n]+=sg
    return Sp.T@Sp+np.diag(Sz**2+Sz)
SS=S2()
sel=[n for n,d in enumerate(dets) if sum(so[p][1] for p in d)==3]
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc)[np.ix_(sel,sel)];s=SS[np.ix_(sel,sel)]
    w,v=np.linalg.eigh(H);ss=np.einsum('ij,ik,kj->j',v,s,v)
    gs=w[np.argmin(abs(ss-8.75))]
    return sorted(set(np.round(w[abs(ss-3.75)<0.1]-gs,2)))
print(levels(0,1000,4000)[:6])
def res(x):
    q=levels(*x);return [q[0]-19240,q[1]-21890,q[2]-23000]
r=least_squares(res,[800,700,3200]);print(r.x,levels(*r.x)[:5],res(r.x))
EOF
python3 d5.py
