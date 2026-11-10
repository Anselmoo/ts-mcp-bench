python3 - << 'EOF'
import numpy as np, itertools
from math import pi, sqrt
from scipy.linalg import expm
from sympy.physics.wigner import gaunt
B=1.0; C=3473/800.0
F2=49*B+7*C; F4=12.6*C
Fk={2:F2,4:F4}
def angC(k,ma,mc,q):
    return sqrt(4*pi/(2*k+1))*((-1)**(ma%2))*float(gaunt(2,k,2,-ma,q,mc).evalf())
Vorb=np.zeros((5,5,5,5))
for ma,mb,mc,md in itertools.product(range(-2,3),repeat=4):
    val=0.0
    for k in (2,4):
        for q in range(-k,k+1):
            if ma-mc!=q or mb-md!=-q: continue
            val+=Fk[k]*((-1)**(q%2))*angC(k,ma,mc,q)*angC(k,mb,md,-q)
    Vorb[ma+2,mb+2,mc+2,md+2]=val
Vso={}
for a,b,c,d in itertools.product(range(10),repeat=4):
    if a//5!=c//5 or b//5!=d//5: continue
    v=Vorb[a%5,b%5,c%5,d%5]
    if abs(v)>1e-12: Vso[(a,b,c,d)]=v
states=[sum(1<<i for i in comb) for comb in itertools.combinations(range(10),5)]
idx={s:i for i,s in enumerate(states)}
N=len(states)
def cann(i,occ):
    if not (occ>>i)&1: return None
    return (-1)**bin(occ & ((1<<i)-1)).count('1'), occ & ~(1<<i)
def cdag(i,occ):
    if (occ>>i)&1: return None
    return (-1)**bin(occ & ((1<<i)-1)).count('1'), occ | (1<<i)
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
Sz=np.zeros((10,10),dtype=complex); Sp=np.zeros((10,10),dtype=complex)
for o in range(5):
    Sz[o,o]=0.5; Sz[o+5,o+5]=-0.5; Sp[o,o+5]=1.0
SzM=one_body(Sz); SpM=one_body(Sp)
S2=SzM@SzM+0.5*(SpM.conj().T@SpM+SpM@SpM.conj().T)
lz=np.diag([-2.,-1,0,1,2]).astype(complex)
lp=np.zeros((5,5),dtype=complex)
for m in range(-2,2):
    lp[m+3,m+2]=sqrt(6-m*(m+1))
lm=lp.conj().T
lx=(lp+lm)/2; ly=(lp-lm)/(2j)
def lift(l):
    h=np.zeros((10,10),dtype=complex); h[:5,:5]=l; h[5:,5:]=l; return h
Lops=[lx,ly,lz]
LM=[one_body(lift(l)) for l in Lops]
L2=LM[0]@LM[0]+LM[1]@LM[1]+LM[2]@LM[2]
def Dmat(n,th):
    return expm(-1j*th*sum(n[i]*Lops[i] for i in range(3)))
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
assert len(elems)==24
classes=[]
for R,D in elems:
    tr=np.trace(R).real
    if np.allclose(R,np.eye(3)): c='E'
    elif abs(tr)<1e-8: c='C3'
    elif abs(tr+1)<1e-8: c='C2' if np.allclose(R,np.diag(np.diag(R))) else "C2'"
    else: c='C4'
    classes.append(c)
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
PG={}
for r in dims:
    P=np.zeros((N,N),dtype=complex)
    for g,c in enumerate(classes): P+=cls_char[c][r]*Us[g]
    PG[r]=dims[r]/24*P
def projector_eig(M, target, tol=1e-6):
    w,V=np.linalg.eigh((M+M.conj().T)/2)
    return V[:,np.abs(w-target)<tol]
Sspins={2.5:35/4,1.5:15/4,0.5:3/4}
Lsym={0:'S',1:'P',2:'D',3:'F',4:'G',5:'H',6:'I'}
Ssec={S:projector_eig(S2,val) for S,val in Sspins.items()}
H0=V2+one_body(hcf(0.0))
def clusters_for(S):
    Vs=Ssec[S]
    A=Vs.conj().T@(H0+0.0137*L2)@Vs
    w,U=np.linalg.eigh((A+A.conj().T)/2)
    cl=[]; i=0
    while i<len(w):
        j=i
        while j+1<len(w) and abs(w[j+1]-w[i])<1e-6: j+=1
        basis=Vs@U[:,i:j+1]
        Lval=np.real(np.vdot(basis[:,0],L2@basis[:,0]))
        Lv=round((-1+np.sqrt(1+4*Lval))/2)
        Eval=np.real(np.vdot(basis[:,0],H0@basis[:,0]))
        cl.append(dict(basis=basis,L=Lv,E=Eval)); i=j+1
    return cl
clus={S:clusters_for(S) for S in Sspins}
Qs={}
for S in Sspins:
    for r in dims:
        P=PG[r]@(Ssec[S]@Ssec[S].conj().T)
        Qs[(S,r)]=projector_eig(P,1.0)
def levels(Dq):
    H=V2+one_body(hcf(Dq))
    out=[]
    for S in Sspins:
        for r in dims:
            Q=Qs[(S,r)]
            if Q.shape[1]==0: continue
            d=dims[r]
            Hr=Q.conj().T@H@Q
            w,X=np.linalg.eigh((Hr+Hr.conj().T)/2)
            i=0
            while i<len(w):
                j=i
                while j+1<len(w) and abs(w[j+1]-w[i])<1e-7: j+=1
                mult=j-i+1
                assert mult%d==0
                wfull=Q@X[:,i]
                wts=[np.linalg.norm(c['basis'].conj().T@wfull)**2 for c in clus[S]]
                ci=int(np.argmax(wts))
                out.append(dict(S=S,G=r,E=w[i],copies=mult//d,L=clus[S][ci]['L'],pw=wts[ci],mult=2*S+1))
                i=j+1
    return out
# ground
res0=levels(0.01)
g=[x for x in res0 if x['S']==2.5 and x['G']=='A1']
E0=g[0]['E']
print('parent-check small Dq:')
for x in sorted(res0,key=lambda x:x['E']):
    print(f"{int(x['mult'])}{x['G']}({Lsym[x['L']]}) E/B={x['E']-E0:.4f} pw={x['pw']:.3f} copies={x['copies']}")
EOF