import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import least_squares
l=2; ms=range(-2,3)
def ck(k,m,mp):
    return float((-1)**m*5*wigner_3j(2,k,2,0,0,0)*wigner_3j(2,k,2,-m,m-mp,mp))
C={k:np.array([[ck(k,m,mp) for mp in ms] for m in ms]) for k in (0,2,4)}
# orbitals: index (m+2)*2+s
so=[(m,s) for m in ms for s in (0,1)]
def eri(a,b,c,d,F):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=so[a],so[b],so[c],so[d]
    if s1!=s3 or s2!=s4 or m1+m2!=m3+m4: return 0
    return sum(F[k]*C[k][m1+2,m3+2]*C[k][m4+2,m2+2] for k in (2,4))
dets=[d for d in itertools.combinations(range(10),6) if sum(1 if o%2==0 else -1 for o in d)==0]
idx={d:i for i,d in enumerate(dets)}
# one-electron
P=np.zeros((5,5)); v0=np.zeros(5);v0[2]=1; v1=np.zeros(5);v1[4]=v1[0]=1/np.sqrt(2)
Peg=np.outer(v0,v0)+np.outer(v1,v1); Pt=np.eye(5)-Peg
def build(Dq,B,Cc):
    F={2:49*(B+Cc/7),4:441*Cc/35}
    h1=Dq*(6*Peg-4*Pt)
    n=len(dets);H=np.zeros((n,n))
    def apply_ann(d,o):
        if o not in d: return None
        p=d.index(o); return (tuple(x for x in d if x!=o),(-1)**p)
    def cre(d,o):
        if o in d: return None
        lst=sorted(d+(o,)); p=lst.index(o); return (tuple(lst),(-1)**p)
    # precompute eri
    E={}
    for a in range(10):
     for b in range(10):
      for c in range(10):
       for dd in range(10):
        E[a,b,c,dd]=eri(a,b,c,dd,F)
    for j,d in enumerate(dets):
        # one body
        for p in range(10):
            for q in range(10):
                if so[p][1]!=so[q][1]: continue
                h=h1[so[p][0]+2,so[q][0]+2]
                if h==0: continue
                r=apply_ann(d,q)
                if r is None: continue
                r2=cre(r[0],p)
                if r2 is None: continue
                H[idx[r2[0]],j]+=h*r[1]*r2[1]
        # two body 1/2 sum <ab|cd> a+b+ d c
        for (a,b,c,dd),val in E.items():
            if val==0: continue
            r=apply_ann(d,c)
            if r is None: continue
            r2=apply_ann(r[0],dd)
            if r2 is None: continue
            r3=cre(r2[0],b)
            if r3 is None: continue
            r4=cre(r3[0],a)
            if r4 is None: continue
            H[idx[r4[0]],j]+=0.5*val*r[1]*r2[1]*r3[1]*r4[1]
    return H
# S^2
n=len(dets);S2=np.zeros((n,n))
def sp(d):
    out={}
    for o in d:
        if o%2==1 and o-1 not in d:
            nd=tuple(sorted([x for x in d if x!=o]+[o-1]));
            sg=(-1)**d.index(o)
            lst=[x for x in d if x!=o]
            # sign from reordering
            p=sorted(lst+[o-1]).index(o-1)
            out[nd]=out.get(nd,0)+(-1)**d.index(o)*(-1)**p
    return out
Sp=np.zeros((n,n))
for j,d in enumerate(dets):
    for nd,s in sp(d).items():
        if nd in idx: Sp[idx[nd],j]+=s
Sz=0
S2=Sp.T@Sp  # S-S+ ; at Ms=0 S2=S-S+ + Sz^2+Sz
def levels(Dq,B,Cc):
    H=build(Dq,B,Cc); H=(H+H.T)/2
    w,v=np.linalg.eigh(H)
    s=np.einsum('ij,ik,kj->j',v,S2,v)
    sing=[w[i] for i in range(n) if abs(s[i])<0.1]
    sing=np.array(sorted(sing)); 
    u=[sing[0]]
    for x in sing[1:]:
        if x-u[-1]>1e-6: u.append(x)
    return np.array(u)-u[0]
exp=np.array([16700,26330,35020])
def res(p):
    Dq,B=p; u=levels(Dq,B,4*B); return u[1:4]-exp
r=least_squares(res,[2000,400]);print(r.x,res(r.x))
print(levels(r.x[0],r.x[1],4*r.x[1])[:7])
