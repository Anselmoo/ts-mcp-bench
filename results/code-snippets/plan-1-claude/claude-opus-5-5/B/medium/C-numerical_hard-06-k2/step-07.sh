python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares, fsolve
ms=[-2,-1,0,1,2]
orbs=[(m,s) for m in ms for s in (0,1)]
cc={}
def c(k,ma,mb):
    key=(k,ma,mb)
    if key not in cc: cc[key]=float((-1)**ma*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-ma,ma-mb,mb))
    return cc[key]
def V(a,b,c_,d,F):
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c_],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*c(k,ma,mc)*c(k,md,mb) for k in (2,4))
def hcf(Dq):
    h=np.zeros((5,5)); d={-2:1,-1:-4,0:6,1:-4,2:1}
    for i,m in enumerate(ms): h[i,i]=d[m]*Dq
    h[0,4]=h[4,0]=5*Dq; return h
def Ms(D): return sum(0.5 if orbs[p][1]==0 else -0.5 for p in D)
dets=[d for d in itertools.combinations(range(10),6) if Ms(d)==0]
idx={d:i for i,d in enumerate(dets)}; N=len(dets)
def perm(new): return (-1)**sum(1 for i in range(len(new)) for j in range(i+1,len(new)) if new[i]>new[j])
def build(Dq,B,C):
    F4=C*441/35; F2=49*(B+5*F4/441); F={2:F2,4:F4}
    h1=hcf(Dq); H=np.zeros((N,N))
    for I,D in enumerate(dets):
        Ds=list(D)
        for p in Ds:
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=h1[orbs[q][0]+2,orbs[p][0]+2]
                if v==0 or (q!=p and q in Ds): continue
                new=Ds.copy(); new[new.index(p)]=q
                H[idx[tuple(sorted(new))],I]+=perm(new)*v
        for i1 in range(6):
            for i2 in range(i1+1,6):
                p,q=Ds[i1],Ds[i2]; rest=[x for x in Ds if x not in(p,q)]
                for r in range(10):
                    for s in range(r+1,10):
                        if r in rest or s in rest: continue
                        v=V(r,s,p,q,F)-V(r,s,q,p,F)
                        if abs(v)<1e-12: continue
                        new=Ds.copy(); new[i1]=r; new[i2]=s
                        H[idx[tuple(sorted(new))],I]+=perm(new)*v
    return H
HD,HB,HC=build(1,0,0),build(0,1,0),build(0,0,1)
S2=np.zeros((N,N))
for I,D in enumerate(dets):
    Ds=list(D)
    for p in Ds:
        if orbs[p][1]==1:
            q=p-1
            if q in Ds: continue
            new=Ds.copy(); new[new.index(p)]=q; sp=perm(new)
            for p2 in new:
                if orbs[p2][1]==0:
                    q2=p2+1
                    if q2 in new: continue
                    n2=new.copy(); n2[n2.index(p2)]=q2
                    S2[idx[tuple(sorted(n2))],I]+=sp*perm(n2)
def levels(Dq,B,CB=4):
    H=Dq*HD+B*HB+CB*B*HC
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,ik,kj->j',v,S2,v)
    sing=w[s<0.5]
    lv=[]
    for e in sing:
        if lv and abs(e-lv[-1][0])<0.5: lv[-1][1]+=1
        else: lv.append([e,1])
    return [(round(e-lv[0][0],1),n) for e,n in lv]
def T(x): 
    L=levels(*x); return np.array([e for e,n in L if n==3][:3])
obs=np.array([16700,26330,35020])
s=fsolve(lambda x:(T(x)-obs)[:2],(1900,600)); print("2-band",s,T(s),levels(*s)[:7])
r=least_squares(lambda x:(T(x)-obs),(1900,600),diff_step=1e-3); print("3-band",r.x,r.fun)
s=fsolve(lambda x:(T(x[:2].tolist()+[x[2]])-obs) if False else (np.array([e for e,n in levels(*x) if n==3][:3])-obs),(1900,600,4)); print("C free",s,s[2]*s[1])
EOF