
cat << 'EOF' > /tmp/d4.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ml=[-2,-1,0,1,2]
so=[(m,s) for m in ml for s in (0,1)]
def ck(k,m1,m2):
    # <l m1|C^k_{m1-m2}|l m2>
    q=m1-m2
    if abs(q)>k: return 0.0
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*25*0+0) if False else float((-1)**(m1)*gaunt(2,k,2,-m1,q,m2)*np.sqrt(4*np.pi/(2*k+1))*5)
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ml for b in ml}
def V2(i,j,k,l,F):
    # <ij|1/r|kl>, orbitals i,k electron1; j,l electron2
    (mi,si),(mj,sj),(mk,sk),(ml_,sl)=so[i],so[j],so[k],so[l]
    if si!=sk or sj!=sl or mi+mj!=mk+ml_: return 0.0
    return sum(F[kk]*CK[(kk,mi,mk)]*CK[(kk,ml_,mj)] for kk in (0,2,4))
dets=list(itertools.combinations(range(10),4))
idx={d:n for n,d in enumerate(dets)}
def cf(Dq):
    h=np.zeros((5,5)); d={-2:0,-1:1,0:2,1:3,2:4}
    for m,v in [(2,1),(-2,1),(0,6),(1,-4),(-1,-4)]: h[d[m],d[m]]=v*Dq
    h[d[2],d[-2]]=h[d[-2],d[2]]=5*Dq
    H=np.zeros((10,10))
    for a in range(10):
        for b in range(10):
            if so[a][1]==so[b][1]: H[a,b]=h[a//2,b//2]
    return H
# precompute two-electron tensors for unit F
def tens(F):
    T=np.zeros((10,)*4)
    for i,j,k,l in itertools.product(range(10),repeat=4): T[i,j,k,l]=V2(i,j,k,l,F)
    return T
T2=tens({0:0,2:1,4:0}); T4=tens({0:0,2:0,4:1})
def apply1(h,d):
    out=[]
    for p in d:
        for q in range(10):
            if h[q,p]==0: continue
            if q!=p and q in d: continue
            l=list(d); pos=l.index(p); l[pos]=q
            sgn=1; s=sorted(l)
            # permutation sign
            perm=[l.index(x) for x in s]
            sgn=np.linalg.det(np.eye(4)[perm])
            out.append((tuple(s),h[q,p]*sgn))
    return out
def apply2(T,d):
    out={}
    for a,b in itertools.combinations(d,2):
        for c in range(10):
            for e in range(10):
                if c==e: continue
                v=T[c,e,a,b]-T[c,e,b,a]
                if abs(v)<1e-12: continue
                rest=[x for x in d if x not in (a,b)]
                if c in rest or e in rest: continue
                # annihilate a,b create c,e : c^+ e^+ b a
                l=list(d)
                # replace a->c, b->e
                l[l.index(a)]=c; l[l.index(b)]=e
                s=sorted(l); perm=[l.index(x) for x in s]
                sg=np.linalg.det(np.eye(4)[perm])
                out[tuple(s)]=out.get(tuple(s),0)+v*sg*0.5
    return out
N=len(dets)
M2=np.zeros((N,N));M4=np.zeros((N,N))
for n,d in enumerate(dets):
    for s,v in apply2(T2,d).items(): M2[idx[s],n]+=v*2/2
    for s,v in apply2(T4,d).items(): M4[idx[s],n]+=v*2/2
# Note: pairs counted once with (c,e) ordered both ways -> factor 0.5*2... check via free ion
hc=cf(1.0); MC=np.zeros((N,N))
for n,d in enumerate(dets):
    for s,v in apply1(hc,d): MC[idx[s],n]+=v
# S^2
def Sz(d): return sum(0.5 if so[x][1]==0 else -0.5 for x in d)
Sp=np.zeros((10,10))
for a in range(10):
    if so[a][1]==1: Sp[a-1,a]=1
SP=np.zeros((N,N))
for n,d in enumerate(dets):
    for s,v in apply1(Sp,d): SP[idx[s],n]+=v
SZ=np.diag([Sz(d) for d in dets])
S2=SP.T@SP+SZ@SZ+SZ
def levels(Dq,B,C):
    F2=49*(B+C/7); F4=441*C/35
    H=Dq*MC+F2*M2+F4*M4
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,jk,ki->i',v.T,S2,v)
    S=np.round((-1+np.sqrt(1+4*s))/2,2)
    return w-w[0],S
w,S=levels(0,1000,4300)
print(sorted(set(np.round(w,0))))
np.save('/tmp/m.npy',[MC,M2,M4,S2])
EOF
python3 /tmp/d4.py
