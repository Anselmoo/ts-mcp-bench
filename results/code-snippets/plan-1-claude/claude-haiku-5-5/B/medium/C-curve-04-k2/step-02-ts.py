import numpy as np, itertools
from math import pi, sqrt
from scipy.linalg import expm, eigh
from sympy.physics.wigner import gaunt

B=1.0; C=3473/800.0
F2=49*B+7*C; F4=12.6*C   # B=(9F2-5F4)/441, C=35F4/441
Fk={2:F2,4:F4}
# spin-orbital index: o + 5*s, o=m+2, s=0 up,1 down
def ang(k,ma,mc,q):
    return sqrt(4*pi/(2*k+1))*(-1)**(ma+2*0)*float(gaunt(2,k,2,-ma,q,mc).evalf()) * (-1)**0
# careful: (-1)^{ma} with ma integer
def angC(k,ma,mc,q):
    return sqrt(4*pi/(2*k+1))*((-1)**(ma%2))*float(gaunt(2,k,2,-ma,q,mc).evalf())
# two-electron antisymmetrized-free matrix <ab|V|cd> (orbital indices m)
Vorb=np.zeros((5,5,5,5))
for ma,mb,mc,md in itertools.product(range(-2,3),repeat=4):
    val=0.0
    for k in (2,4):
        for q in range(-k,k+1):
            if abs(q)>2 or abs(q)>k: continue
            if ma-mc!=q or mb-md!=-q: continue
            val+=Fk[k]*((-1)**(q%2))*angC(k,ma,mc,q)*angC(k,mb,md,-q)
    Vorb[ma+2,mb+2,mc+2,md+2]=val
# spin-orbital two-body tensor
def sidx(o,s): return o+5*s
Vso={}
for a,b,c,d in itertools.product(range(10),repeat=4):
    oa,sa=a%5,a//5; ob,sb=b%5,b//5; oc,sc=c%5,c//5; od,sd=d%5,d//5
    if sa!=sc or sb!=sd: continue
    v=Vorb[oa,ob,oc,od]
    if abs(v)>1e-12: Vso[(a,b,c,d)]=v
# basis
states=[sum(1<<i for i in comb) for comb in itertools.combinations(range(10),5)]
idx={s:i for i,s in enumerate(states)}
N=len(states)
def cann(i,occ):
    if not (occ>>i)&1: return None
    sign=(-1)**bin(occ & ((1<<i)-1)).count('1')
    return sign, occ & ~(1<<i)
def cdag(i,occ):
    if (occ>>i)&1: return None
    sign=(-1)**bin(occ & ((1<<i)-1)).count('1')
    return sign, occ | (1<<i)
def one_body(h):
    M=np.zeros((N,N),dtype=complex)
    for j,occ in enumerate(states):
        for a in range(10):
            for b in range(10):
                if abs(h[a,b])<1e-14: continue
                r=cann(b,occ)
                if r is None: continue
                s1,o1=r
                r2=cdag(a,o1)
                if r2 is None: continue
                s2,o2=r2
                M[idx[o2],j]+=h[a,b]*s1*s2
    return M
def two_body(V):
    M=np.zeros((N,N),dtype=complex)
    for j,occ in enumerate(states):
        for (a,b,c,d),v in V.items():
            r=cann(c,occ)
            if r is None: continue
            s1,o1=r
            r=cann(d,o1)
            if r is None: continue
            s2,o2=r
            r=cdag(b,o2)
            if r is None: continue
            s3,o3=r
            r=cdag(a,o3)
            if r is None: continue
            s4,o4=r
            M[idx[o4],j]+=0.5*v*s1*s2*s3*s4
    return M
# one-electron CF: t2g -4Dq, eg +6Dq ; P_eg in m-basis
Peg=np.zeros((5,5),dtype=complex)
Peg[2,2]=1.0
v=np.zeros(5,dtype=complex); v[4]=1/sqrt(2); v[0]=1/sqrt(2)
Peg+=np.outer(v,v.conj())
Pt2g=np.eye(5)-Peg
def hcf(Dq):
    h5=-4*Dq*Pt2g+6*Dq*Peg
    h=np.zeros((10,10),dtype=complex)
    for s in range(2):
        h[5*s:5*s+5,5*s:5*s+5]=h5
    return h
V2=two_body(Vso)
# spin operators
def spin_ops():
    Sz=np.zeros((10,10),dtype=complex); Sp=np.zeros((10,10),dtype=complex)
    for o in range(5):
        Sz[o,o]=0.5; Sz[o+5,o+5]=-0.5
        Sp[o,o+5]=1.0
    return one_body(Sz), one_body(Sp)
SzM,SpM=spin_ops()
S2=SzM@SzM+0.5*(SpM.conj().T@SpM+SpM@SpM.conj().T)
# orbital L ops (m basis)
lz=np.diag([-2.,-1,0,1,2]).astype(complex)
lp=np.zeros((5,5),dtype=complex)
for m in range(-2,2):
    lp[m+3,m+2]=sqrt(6-m*(m+1))
lm=lp.conj().T
lx=(lp+lm)/2; ly=(lp-lm)/(2j)
def lift(l): 
    h=np.zeros((10,10),dtype=complex); h[:5,:5]=l; h[5:,5:]=l; return h
L2=sum(one_body(lift(l))@one_body(lift(l)) for l in (lx,ly,lz))
Lz_M=one_body(lift(lz))
# group elements: generate SO(3) rep pairs
Lops=[lx,ly,lz]
def Dmat(n,th):
    nL=sum(n[i]*Lops[i] for i in range(3))
    return expm(-1j*th*nL)
def Rmat(n,th):
    n=np.array(n,float); n/=np.linalg.norm(n)
    K=np.array([[0,-n[2],n[1]],[n[2],0,-n[0]],[-n[1],n[0],0]])
    return np.eye(3)+np.sin(th)*K+(1-np.cos(th))*K@K
gens=[(Rmat([0,0,1],pi/2),Dmat([0,0,1],pi/2)),(Rmat([1,1,1],2*pi/3),Dmat([1,1,1],2*pi/3))]
elems=[(np.eye(3),np.eye(5,dtype=complex))]
def find(R):
    for i,(R2,_) in enumerate(elems):
        if np.allclose(R,R2,atol=1e-8): return i
    return -1
frontier=[elems[0]]
while frontier:
    new=[]
    for R,D in frontier:
        for Rg,Dg in gens:
            R2=Rg@R; D2=Dg@D
            if find(R2)<0:
                elems.append((R2,D2)); new.append((R2,D2))
    frontier=new
assert len(elems)==24, len(elems)
classes=[]
for R,D in elems:
    tr=np.trace(R).real
    if np.allclose(R,np.eye(3)): c='E'
    elif abs(tr)<1e-8: c='C3'
    elif abs(tr+1)<1e-8:
        c='C2' if np.allclose(R,np.diag(np.diag(R))) else "C2'"
    else: c='C4'
    classes.append(c)
from collections import Counter
print(Counter(classes))
# many-body unitary
def manybody(D):
    u=np.zeros((10,10),dtype=complex)
    u[:5,:5]=D; u[5:,5:]=D
    U=np.zeros((N,N),dtype=complex)
    occs=[[i for i in range(10) if (s>>i)&1] for s in states]
    for j,I in enumerate(occs):
        for i,J in enumerate(occs):
            U[i,j]=np.linalg.det(u[np.ix_(J,I)])
    return U
Us=[manybody(D) for R,D in elems]
cls_char={
 'E':{'A1':1,'A2':1,'E':2,'T1':3,'T2':3},
 'C3':{'A1':1,'A2':1,'E':-1,'T1':0,'T2':0},
 'C2':{'A1':1,'A2':1,'E':2,'T1':-1,'T2':-1},
 'C4':{'A1':1,'A2':-1,'E':0,'T1':1,'T2':-1},
 "C2'":{'A1':1,'A2':-1,'E':0,'T1':-1,'T2':1}}
dims={'A1':1,'A2':1,'E':2,'T1':3,'T2':3}
def proj(irrep):
    P=np.zeros((N,N),dtype=complex)
    for g,c in enumerate(classes):
        P+=cls_char[c][irrep]*Us[g]
    return dims[irrep]/24*P
PG={r:proj(r) for r in dims}
np.save('/work/dummy.npy',np.zeros(1))
