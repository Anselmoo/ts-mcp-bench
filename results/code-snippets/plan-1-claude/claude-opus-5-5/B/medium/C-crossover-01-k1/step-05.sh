python3 - << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B,C=706.,2734.
F2=B+C/7; F4=C/35
Fk={2:49*F2,4:441*F4}
ms=[-2,-1,0,1,2]
cc={}
def ck(k,m,mp):
    key=(k,m,mp)
    if key not in cc: cc[key]=float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
    return cc[key]
so=[(m,s) for m in ms for s in (0,1)]
n=len(so)
G=np.zeros((n,)*4)
for a,b,c,d in itertools.product(range(n),repeat=4):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[c],so[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: continue
    G[a,b,c,d]=sum(ck(k,m1,m3)*ck(k,m4,m2)*Fk[k] for k in (2,4))
def V1(Dq):
    h=np.zeros((n,n))
    for i,(m,s) in enumerate(so):
        for j,(mp,sp) in enumerate(so):
            if s!=sp: continue
            if m==mp: h[i,j]={0:6,1:-4,-1:-4,2:1,-2:1}[m]*Dq
            if abs(m-mp)==4: h[i,j]=5*Dq
    return h
dets=list(itertools.combinations(range(n),4))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply_ops(det,ann,cre):
    l=list(det); sgn=1
    for a in ann:
        if a not in l: return 0,None
        p=l.index(a); sgn*=(-1)**p; l.pop(p)
    for c in cre:
        if c in l: return 0,None
        l.insert(0,c)
    arr=l[:]
    for i in range(len(arr)):
        for j in range(len(arr)-1-i):
            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sgn=-sgn
    return sgn,tuple(arr)
H2=np.zeros((N,N))
for i,d in enumerate(dets):
    for a,b in itertools.combinations(d,2):
        for c in range(n):
            for e in range(n):
                val=G[c,e,a,b]
                if c==e or abs(val)<1e-12: continue
                s,nd=apply_ops(d,[a,b],[e,c])
                if s: H2[idx[nd],i]+=s*val
h1=V1(1.0); M1=np.zeros((N,N))
for i,d in enumerate(dets):
    for a in d:
        for c in range(n):
            if abs(h1[c,a])<1e-12: continue
            s,nd=apply_ops(d,[a],[c])
            if s: M1[idx[nd],i]+=s*h1[c,a]
print(np.allclose(H2,H2.T))
w=np.linalg.eigvalsh(H2); print(np.unique(np.round(w-w.min(),2)))
print("expected 3H:",(21*B+4*C-(0)) )
Sz=np.array([sum(1 if so[k][1] else -1 for k in d)/2 for d in dets])
i2=np.where(Sz==2)[0]; i1=np.where(Sz==1)[0]
def gap(Dq):
    M=H2+Dq*M1
    q=np.linalg.eigvalsh(M[np.ix_(i2,i2)])
    w1=list(np.linalg.eigvalsh(M[np.ix_(i1,i1)]))
    for x in q:
        k=np.argmin(np.abs(np.array(w1)-x)); w1.pop(k)
    return min(w1)-q.min()
for Dq in [1500,2000,2500,3000]: print(Dq,gap(Dq))
lo,hi=500,5000
for _ in range(50):
    mid=(lo+hi)/2
    if gap(mid)>0: lo=mid
    else: hi=mid
print(mid)
EOF