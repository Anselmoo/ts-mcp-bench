cat << 'EOF' | python3 -
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from scipy.optimize import brentq
from functools import lru_cache
l=2; ms=list(range(-2,3))
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def tensor(k,q,m1,m3):
    if m1-m3!=q: return 0.0
    red=(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
    return (-1)**(l-m1)*w3(l,k,l,-m1,q,m3)*red
def cmat(k,q): return np.array([[tensor(k,q,m1,m3) for m3 in ms] for m1 in ms])
Vcf = cmat(4,0)+np.sqrt(5/14)*(cmat(4,4)+cmat(4,-4))
Mcf = 21.0*Vcf
SO=[(i,s) for i in range(5) for s in (0,1)]
def ang(k,m1,m2,m3,m4):
    return sum((-1)**q*tensor(k,q,m1,m3)*tensor(k,-q,m2,m4) for q in range(-k,k+1))
basis=list(itertools.combinations(range(10),8)); idx={o:i for i,o in enumerate(basis)}; N=len(basis)
def apply(occ,ops):
    occ=list(occ); sign=1
    for typ,p in reversed(ops):
        if typ=='a':
            if p not in occ: return None
            pos=occ.index(p); sign*=(-1)**pos; occ.pop(pos)
        else:
            if p in occ: return None
            pos=sum(1 for x in occ if x<p); sign*=(-1)**pos; occ.insert(pos,p)
    return sign,tuple(occ)
def Hparts(F):
    Hcf=np.zeros((N,N)); Hee=np.zeros((N,N))
    # precompute V
    Vt={}
    for a,b,c,d in itertools.product(range(10),repeat=4):
        (ia,sa),(ib,sb),(ic,sc),(id_,sd)=SO[a],SO[b],SO[c],SO[d]
        if sa!=sc or sb!=sd or a==b or c==d: continue
        v=sum(F[k]*ang(k,ms[ia],ms[ib],ms[ic],ms[id_]) for k in F)
        if abs(v)>1e-14: Vt[(a,b,c,d)]=v
    for j,occ in enumerate(basis):
        for a in range(10):
            for b in range(10):
                ia,sa=SO[a]; ib,sb=SO[b]
                if sa!=sb: continue
                h=Mcf[ia,ib]
                if abs(h)<1e-14: continue
                r=apply(occ,[('c',a),('a',b)])
                if r: Hcf[idx[r[1]],j]+=h*r[0]
        for (a,b,c,d),v in Vt.items():
            r=apply(occ,[('c',a),('c',b),('a',d),('a',c)])
            if r: Hee[idx[r[1]],j]+=0.5*v*r[0]
    # S^2
    Sz=np.zeros(N); Sp=np.zeros((N,N))
    for j,occ in enumerate(basis):
        nup=sum(1 for p in occ if p%2==0); Sz[j]=0.5*(2*nup-8)
        for i in range(5):
            r=apply(occ,[('c',2*i),('a',2*i+1)])
            if r: Sp[idx[r[1]],j]+=r[0]
    Szm=np.diag(Sz); S2=Sp.T@Sp+Szm@Szm+Szm
    return Hcf,Hee,S2
def FromBC(B,C):
    F4=441*C/35.0; F2=(441*B+5*F4)/9.0
    return {2:F2,4:F4}
# check hermiticity and free-ion gap
F=FromBC(1.0,4.5)
Hcf,Hee,S2=Hparts(F)
print("herm",np.abs(Hee-Hee.T).max(), np.abs(Hcf-Hcf.T).max())
w,U=np.linalg.eigh(S2); print("S2 eig",np.unique(np.round(w,6)))
# free-ion levels: Hee eigen restricted to triplets
def levels(Dq,B,C):
    F=FromBC(B,C); Hcf,Hee,S2=Hparts(F)
    H=Dq*Hcf+Hee+1e4*S2
    e,U=np.linalg.eigh(H)
    out=[]
    for k in range(N):
        s2=U[:,k]@S2@U[:,k]
        if abs(s2-2)<1e-3: out.append(e[k]-1e4*2)
    return np.array(sorted(out))
# free ion (Dq=0) triplet levels with B=1,C=4.5
lv=levels(0.0,1.0,4.5)
print("free triplets (units B):", np.round(lv-lv[0],4))
EOF