import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
B,C=706.,2734.
F2=B+C/7; F4=C/35
Fk={0:0.0,2:49*F2,4:441*F4}
ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
# spin orbitals (m,s)
so=[(m,s) for m in ms for s in (0,1)]
n=len(so)
def g(a,b,c,d): # <ab|1/r|cd>
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[c],so[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0.
    return sum(ck(k,m1,m3)*ck(k,m4,m2)*Fk[k] for k in (2,4))
G=np.zeros((n,)*4)
for a,b,c,d in itertools.product(range(n),repeat=4): G[a,b,c,d]=g(a,b,c,d)
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
    # returns sign,newdet for c^+_cre... a_ann...  ops applied: annihilate list then create list
    l=list(det); sgn=1
    for a in ann:
        if a not in l: return 0,None
        p=l.index(a); sgn*=(-1)**p; l.pop(p)
    for c in cre:
        if c in l: return 0,None
        l.insert(0,c)
    # sort with sign
    arr=l[:]; 
    for i in range(len(arr)):
        for j in range(len(arr)-1-i):
            if arr[j]>arr[j+1]: arr[j],arr[j+1]=arr[j+1],arr[j]; sgn=-sgn
    return sgn,tuple(arr)
H2=np.zeros((N,N))
for i,d in enumerate(dets):
    for a,b in itertools.combinations(range(n),2):
        if a not in d or b not in d: continue
        for c in range(n):
            for e in range(n):
                if c==e: continue
                val=G[c,e,a,b]
                if abs(val)<1e-12: continue
                # 1/2 sum c+ e+ b a  over ordered pairs a,b -> pairs both orders gives factor; use unordered a<b with (G[c,e,a,b]-...)?
                s,nd=apply_ops(d,[a,b],[e,c])  # a_a then a_b... sequence: a_b a_a? careful
                if s: H2[idx[nd],i]+=s*val
H1=lambda Dq: None
def H1m(Dq):
    h=V1(Dq); M=np.zeros((N,N))
    for i,d in enumerate(dets):
        for a in d:
            for c in range(n):
                if abs(h[c,a])<1e-12: continue
                s,nd=apply_ops(d,[a],[c])
                if s: M[idx[nd],i]+=s*h[c,a]
    return M
print(np.allclose(H2,H2.T))
Sz=np.array([sum(1 if so[k][1] else -1 for k in d)/2 for d in dets])
np.save('/tmp/H2.npy',H2)
# Free ion check
w=np.linalg.eigvalsh(H2); u=np.unique(np.round(w-w.min(),3)); print(u[:10]/B)
def gap(Dq):
    M=H2+H1m(Dq)
    # Sz=2 block -> quintet lowest; Sz=1 block lowest triplet (excluding quintets)
    i2=np.where(Sz==2)[0]; e5=np.linalg.eigvalsh(M[np.ix_(i2,i2)]).min()
    i1=np.where(Sz==1)[0]; w1=np.linalg.eigvalsh(M[np.ix_(i1,i1)])
    # remove quintet values: quintet energies from Sz=2 block
    q=np.linalg.eigvalsh(M[np.ix_(i2,i2)])
    w1=list(w1)
    for x in q:
        k=np.argmin(np.abs(np.array(w1)-x)); w1.pop(k)
    return min(w1)-e5
for Dq in [1500,2000,2500,3000]: print(Dq,gap(Dq))
lo,hi=1000,4000
for _ in range(50):
    mid=(lo+hi)/2
    if gap(mid)>0: lo=mid
    else: hi=mid
print(mid)
