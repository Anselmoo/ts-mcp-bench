import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=803.,3078.
F4=C/35; F2=B+5*F4; Fk={0:0.0,2:F2*49,4:F4*441}
ml=[-2,-1,0,1,2]
def ck(k,m1,m2):
    return float(gaunt(2,k,2,-m1,m1-m2,m2))*(-1)**m1*np.sqrt(4*np.pi/(2*k+1))
cache={}
def R(a,b,c,d):
    if a+b!=c+d: return 0.
    return sum(ck(k,a,c)*ck(k,d,b)*Fk[k] for k in (0,2,4))
so=[(m,s) for m in ml for s in (0,1)]
def g(i,j,k,l):
    (a,sa),(b,sb),(c,sc),(d,sd)=so[i],so[j],so[k],so[l]
    if sa!=sc or sb!=sd: return 0.
    key=(a,b,c,d)
    if key not in cache: cache[key]=R(a,b,c,d)
    return cache[key]
dets=list(itertools.combinations(range(10),6)); idx={d:n for n,d in enumerate(dets)}
N=len(dets)
def V1(Dq):
    h=np.zeros((10,10))
    cf={2:Dq,-2:Dq,1:-4*Dq,-1:-4*Dq,0:6*Dq}
    for i,(m,s) in enumerate(so):
        h[i,i]=cf[m]
        for j,(m2,s2) in enumerate(so):
            if s==s2 and abs(m-m2)==4: h[i,j]=5*Dq
    return h
def build_ops():
    Hee=np.zeros((N,N))
    for n,D in enumerate(dets):
        occ=list(D)
        for p,q in itertools.permutations(occ,2):
            for r,s in itertools.permutations(range(10),2):
                val=g(r,s,p,q)
                if val==0: continue
                st=occ[:]; sign=1
                for op,o in ((0,p),(0,q),(1,s),(1,r)):
                    if op==0:
                        if o not in st: sign=0;break
                        k=st.index(o); sign*=(-1)**k; st.pop(k)
                    else:
                        if o in st: sign=0;break
                        k=sum(1 for x in st if x<o); sign*=(-1)**k; st.insert(k,o)
                if sign==0: continue
                Hee[idx[tuple(st)],n]+=0.5*sign*val
    return Hee
def one(h):
    M=np.zeros((N,N))
    for n,D in enumerate(dets):
        occ=list(D)
        for p in occ:
            for r in range(10):
                if h[r,p]==0: continue
                st=occ[:]; k=st.index(p); sign=(-1)**k; st.pop(k)
                if r in st: continue
                k=sum(1 for x in st if x<r); sign*=(-1)**k; st.insert(k,r)
                M[idx[tuple(st)],n]+=sign*h[r,p]
    return M
Hee=build_ops(); V=one(V1(1.0))
sp=np.zeros((10,10))
for i,(m,s) in enumerate(so):
    for j,(m2,s2) in enumerate(so):
        if m==m2 and s==1 and s2==0: sp[i,j]=1
Sp=one(sp); Sz=np.diag([sum(0.5 if so[i][1]==1 else -0.5 for i in D) for D in dets])
S2=Sp.T@Sp+Sz@Sz+Sz
w=np.linalg.eigvalsh(Hee); w-=w[0]; print(np.unique(np.round(w,1))[:6], "check 5D->3H etc")
def gap(Dq):
    w,v=np.linalg.eigh(Hee+Dq*V)
    s=np.einsum('ij,ij->j',v,S2@v)
    return min(w[abs(s)<0.1])-min(w[abs(s-6)<0.1])
print(gap(1000),gap(2000))
print(brentq(gap,500,3000,xtol=1e-6))
