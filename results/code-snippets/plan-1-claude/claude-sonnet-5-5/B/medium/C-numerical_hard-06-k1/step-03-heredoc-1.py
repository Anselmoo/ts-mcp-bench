import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
ms=range(-2,3)
def c(k,m1,m2): return float((-1)**m1*5*wigner_3j(2,k,2,-m1,m1-m2,m2)*wigner_3j(2,k,2,0,0,0))
C2={(k,a,b):c(k,a,b) for k in(2,4) for a in ms for b in ms}
N=10
mo=lambda o:(o//2)-2; so=lambda o:o%2
dets=[d for d in itertools.combinations(range(N),6) if sum(1 for o in d if so(o)==0)==3]
di={d:i for i,d in enumerate(dets)}
def ann(d,o):
    if o not in d:return None
    return tuple(x for x in d if x!=o),(-1)**d.index(o)
def cr(d,o):
    if o in d:return None
    return tuple(sorted(d+(o,))),(-1)**sum(1 for x in d if x<o)
def seq(d,ops):
    s=1
    for t,o in ops:
        r=(ann if t=='a' else cr)(d,o)
        if r is None:return None
        d,sg=r;s*=sg
    return d,s
# S2
n=len(dets);S2=np.zeros((n,n))
for d in dets:
    j=di[d]
    for m in ms:
        pass
    # S-S+ : S+ = sum a+_{m up} a_{m down}; S- = sum a+_{m down} a_{m up}
    for m1 in ms:
      for m2 in ms:
        r=seq(d,[('a',2*(m2+2)+0),('c',2*(m2+2)+1)]) if False else None
    # do with explicit: S+ then S-
    for m2 in ms:
        r=seq(d,[('a',2*(m2+2)+1),('c',2*(m2+2)+0)])
        if r is None:continue
        d1,s1=r
        for m1 in ms:
            r2=seq(d1,[('a',2*(m1+2)+0),('c',2*(m1+2)+1)])
            if r2 is None:continue
            S2[di[r2[0]],j]+=s1*r2[1]
U=np.zeros((5,5),complex);s=1/np.sqrt(2);ix=lambda m:m+2
U[ix(0),0]=1;U[ix(2),1]=s;U[ix(-2),1]=s;U[ix(2),2]=-1j*s;U[ix(-2),2]=1j*s
U[ix(1),3]=-s;U[ix(-1),3]=s;U[ix(1),4]=1j*s;U[ix(-1),4]=1j*s
# precompute structure
one=[];two=[]
for d in dets:
    pass
def Hmat(Dq,B,C_):
    F={2:49*B+7*C_,4:63*C_/5}
    h=U@np.diag([6*Dq,6*Dq,-4*Dq,-4*Dq,-4*Dq])@U.conj().T
    H=np.zeros((n,n),complex)
    for d in dets:
        j=di[d]
        for p in range(N):
          for q in range(N):
            if so(p)!=so(q):continue
            v=h[ix(mo(p)),ix(mo(q))]
            if abs(v)<1e-12:continue
            r=seq(d,[('a',q),('c',p)])
            if r:H[di[r[0]],j]+=v*r[1]
    for p in range(N):
     for q in range(N):
      for r_ in range(N):
       for s_ in range(N):
        if so(p)!=so(r_) or so(q)!=so(s_) or mo(p)+mo(q)!=mo(r_)+mo(s_):continue
        v=sum(F[k]*C2[(k,mo(p),mo(r_))]*C2[(k,mo(s_),mo(q))] for k in(2,4))
        if abs(v)<1e-12:continue
        for d in dets:
            r=seq(d,[('a',r_),('a',s_),('c',q),('c',p)])
            if r:H[di[r[0]],di[d]]+=0.5*v*r[1]
    return H
def levels(Dq,B,C_):
    H=Hmat(Dq,B,C_)
    w,v=np.linalg.eigh((H+H.conj().T)/2)
    s2=np.real(np.einsum('ij,ik,kj->j',v.conj(),S2,v))
    sing=w[abs(s2)<1e-6]
    sing=np.round(sing-sing.min(),3)
    # group degeneracies
    out=[];
    for e in sing:
        if out and abs(out[-1][0]-e)<0.5:out[-1][1]+=1
        else:out.append([e,1])
    return out
print(levels(2000,600,2400)[:8])
tri=lambda x:[e for e,dg in levels(x[0],x[1],4*x[1]) if dg==3][:3]
obs=np.array([16700,26330,35020])
for g in [(2000,500),(2500,600),(1800,400)]:
    r=least_squares(lambda x:np.array(tri(x))-obs,g,diff_step=1e-4)
    print(r.x,r.fun)
