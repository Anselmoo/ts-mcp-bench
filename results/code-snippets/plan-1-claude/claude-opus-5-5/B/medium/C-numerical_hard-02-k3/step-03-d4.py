import numpy as np, itertools
from sympy.physics.wigner import gaunt
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (0,1)]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**(m1)*gaunt(2,k,2,-m1,q,m2)*np.sqrt(4*np.pi/(2*k+1)))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml}
def V2(i,j,k,l,F):
    (mi,si),(mj,sj),(mk,sk),(ml_,sl)=so[i],so[j],so[k],so[l]
    if si!=sk or sj!=sl or mi+mj!=mk+ml_: return 0.0
    return sum(F[kk]*CK[(kk,mi,mk)]*CK[(kk,ml_,mj)] for kk in (0,2,4))
dets=list(itertools.combinations(range(10),4))
idx={d:n for n,d in enumerate(dets)}
N=len(dets)
def sgn(l):
    s=sorted(l); perm=[l.index(x) for x in s]
    return tuple(s),round(np.linalg.det(np.eye(len(l))[perm]))
def one(h):
    M=np.zeros((N,N))
    for n,d in enumerate(dets):
        for p in d:
            for q in range(10):
                if h[q,p]==0: continue
                if q!=p and q in d: continue
                l=list(d); l[l.index(p)]=q
                s,sg=sgn(l); M[idx[s],n]+=h[q,p]*sg
    return M
def two(F):
    T=np.zeros((10,)*4)
    for i,j,k,l in itertools.product(range(10),repeat=4): T[i,j,k,l]=V2(i,j,k,l,F)
    M=np.zeros((N,N))
    for n,d in enumerate(dets):
        for a,b in itertools.combinations(d,2):
            rest=[x for x in d if x not in (a,b)]
            for c in range(10):
                for e in range(c+1,10):
                    if c in rest or e in rest: continue
                    v=T[c,e,a,b]-T[c,e,b,a]
                    if abs(v)<1e-12: continue
                    l=list(d); l[l.index(a)]=c; l[l.index(b)]=e
                    s,sg=sgn(l); M[idx[s],n]+=v*sg
    return M
dmap={-2:0,-1:1,0:2,1:3,2:4}
h=np.zeros((5,5))
for m,v in [(2,1),(-2,1),(0,6),(1,-4),(-1,-4)]: h[dmap[m],dmap[m]]=v
h[0,4]=h[4,0]=5
H1=np.kron(h,np.eye(2))
MC=one(H1); M2=two({0:0,2:1,4:0}); M4=two({0:0,2:0,4:1})
Sp=np.zeros((10,10))
for a in range(10):
    if so[a][1]==1: Sp[a-1,a]=1
SP=one(Sp)
SZ=np.diag([sum(0.5 if so[x][1]==0 else -0.5 for x in d) for d in dets])
S2=SP.T@SP+SZ@SZ+SZ
np.save('mats.npy',np.array([MC,M2,M4,S2]))
def levels(Dq,B,C):
    F2=49*(B+C/7); F4=441*C/35
    H=Dq*MC+F2*M2+F4*M4
    w,v=np.linalg.eigh(H)
    s=np.einsum('ji,jk,ki->i',v,S2,v)
    S=np.round((-1+np.sqrt(1+4*s))/2,2)
    return w,S
w,S=levels(0,1000,4300)
print(sorted(set(zip(np.round(w-w[0]),S))))
