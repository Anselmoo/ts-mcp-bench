import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import sqrt as ssqrt
B,C=828.,3390.
F2=B+5*C/35; F4=C/35  # CS-normalized
Fk={0:0.0,2:49*F2,4:441*F4}
ms=range(-2,3)
def ck(k,m1,m2):  # c^k(l m1, l m2)
    from sympy.physics.wigner import gaunt
    import math
    if abs(m1-m2)>k: return 0.0
    g=gaunt(2,k,2,-m1,m1-m2,m2)*(-1)**m1
    return float(g*ssqrt(4*np.pi/(2*k+1)).evalf()) if False else float(g)*np.sqrt(4*np.pi/(2*k+1))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def coul(m1,m2,m3,m4): # <m1(1) m2(2)|1/r12|m3(1) m4(2)>
    if m1+m2!=m3+m4: return 0.0
    return sum(CK[(k,m1,m3)]*CK[(k,m4,m2)]*Fk[k] for k in (2,4))
so=[(m,s) for m in ms for s in (1,-1)]
dets=list(itertools.combinations(range(10),3))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def V1(Dq):
    v=np.zeros((5,5))
    for m in ms:
        v[m+2,m+2]={2:1,-2:1,1:-4,-1:-4,0:6}[m]*Dq
    v[4,0]=v[0,4]=5*Dq
    return v
# build Coulomb
def apply2(d):
    # returns dict of det->amp for sum_{i<j} pairs
    out={}
    occ=list(d)
    for a,b in itertools.combinations(occ,2):
        for c,e in itertools.permutations(range(10),2):
            (ma,sa),(mb,sb)=so[a],so[b];(mc,sc),(me,se)=so[c],so[e]
            if sa!=sc or sb!=se: continue
            val=coul(mc,me,ma,mb)
            if abs(val)<1e-12: continue
            # a^+_c a^+_e a_b a_a acting on det
            st=list(occ);sign=1
            for op in (a,b):
                i=st.index(op);sign*=(-1)**i;st.pop(i)
            ok=True
            for cr in (e,c):
                if cr in st: ok=False;break
                st.insert(0,cr)
            if not ok: continue
            perm=sorted(range(3),key=lambda i:st[i])
            # sign of sorting
            p=np.argsort(st);s2=np.linalg.det(np.eye(3)[p])
            nd=tuple(sorted(st))
            out[nd]=out.get(nd,0)+sign*s2*val
    return out
H0=np.zeros((N,N))
for d in dets:
    for nd,v in apply2(d).items(): H0[idx[nd],idx[d]]+=v
# convention: matrix element sum over pairs <ce|ab> antisym handled by permutations of (c,e) both orders -> factor 1/2? check below
def apply1(d,v):
    out={}
    for a in d:
        for c in range(10):
            (ma,sa),(mc,sc)=so[a],so[c]
            if sa!=sc or abs(v[mc+2,ma+2])<1e-14: continue
            st=list(d);i=st.index(a);sign=(-1)**i;st.pop(i)
            if c in st: continue
            st.insert(0,c);p=np.argsort(st);s2=np.linalg.det(np.eye(3)[p])
            nd=tuple(sorted(st));out[nd]=out.get(nd,0)+sign*s2*v[mc+2,ma+2]
    return out
Hv=np.zeros((N,N))
for d in dets:
    for nd,v in apply1(d,V1(1.0)).items(): Hv[idx[nd],idx[d]]+=v
H0=(H0+H0.T)/2
e=np.linalg.eigvalsh(H0); 
u=np.unique(np.round(e-e.min(),3)); print("free ion /B", u/B)
np.save('H0.npy',H0);np.save('Hv.npy',Hv)
Ms=np.array([sum(so[a][1] for a in d)/2 for d in dets])
Ml=np.array([sum(so[a][0] for a in d) for d in dets])
np.save('Ms.npy',Ms);np.save('Ml.npy',Ml)
