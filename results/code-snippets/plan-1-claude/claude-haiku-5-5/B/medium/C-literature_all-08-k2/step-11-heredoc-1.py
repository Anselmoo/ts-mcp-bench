import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
A={}
for k in (0,2,4):
    arr=np.zeros((5,5,5,5))
    for i1,m1 in enumerate(range(-2,3)):
     for i2,m2 in enumerate(range(-2,3)):
      for i3,m3 in enumerate(range(-2,3)):
       for i4,m4 in enumerate(range(-2,3)):
        tot=0.0
        for q in range(-k,k+1):
            if (-m1)-q+m3!=0 or (-m2)+q+m4!=0: continue
            tot+=(-1)**(m1+q+m2)*float(gaunt(2,k,2,-m1,-q,m3))*float(gaunt(2,k,2,-m2,q,m4))
        arr[i1,i2,i3,i4]=4*pi/(2*k+1)*tot
    A[k]=arr
basis=list(itertools.combinations(range(10),5))
idx={s:i for i,s in enumerate(basis)}
s2=np.sqrt(2)
def vec(d):
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
orbitals=[(6,vec({0:1})),(6,vec({2:1/s2,-2:1/s2})),(-4,vec({2:1/(1j*s2),-2:-1/(1j*s2)})),
          (-4,vec({1:1/s2,-1:-1/s2})),(-4,vec({1:1/(1j*s2),-1:1/(1j*s2)}))]
def apply_ann(st,p):
    if p not in st: return None
    return (-1)**sum(1 for x in st if x<p), [x for x in st if x!=p]
def apply_cre(st,p):
    if p in st: return None
    return (-1)**sum(1 for x in st if x<p), sorted(st+[p])
dim=len(basis)
def mats(F):
    Vt=np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(10),repeat=4):
        (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
        if sa!=sc or sb!=sd: continue
        Vt[a,b,c,d]=sum(F[k]*A[k][ma+2,mb+2,mc+2,md+2] for k in (0,2,4))
    return Vt
def onebody(h):
    H=np.zeros((dim,dim))
    for col,occ in enumerate(basis):
        st0=list(occ)
        for i in range(10):
          for j in range(10):
            if abs(h[i,j])<1e-14: continue
            r=apply_ann(st0,j)
            if r is None: continue
            r2=apply_cre(r[1],i)
            if r2 is None: continue
            H[idx[tuple(r2[1])],col]+=(r[0]*r2[0]*h[i,j]).real
    return H
def twobody(Vt):
    H=np.zeros((dim,dim))
    for col,occ in enumerate(basis):
        st0=list(occ)
        for k_,l_ in itertools.permutations(st0,2):
          sa,sta=apply_ann(st0,k_)
          sb,stb=apply_ann(sta,l_)
          for i in range(10):
            for j in range(10):
              v=Vt[i,j,k_,l_]
              if v==0: continue
              rc=apply_cre(stb,j)
              if rc is None: continue
              rd=apply_cre(rc[1],i)
              if rd is None: continue
              H[idx[tuple(rd[1])],col]+=0.5*sa*sb*rc[0]*rd[0]*v
    return H
H2=twobody(mats({0:0,2:1.0,4:0})); H4=twobody(mats({0:0,2:0,4:1.0}))
hD=np.zeros((10,10),complex)
M=np.zeros((5,5),complex)
for e,v in orbitals: M+=e*np.outer(v,v.conj())
for i,(m,s) in enumerate(orbs):
    for j,(mm,ss) in enumerate(orbs):
        if s==ss: hD[i,j]=M[m+2,mm+2]
HD=onebody(hD)
Sz=np.array([0.5*sum(1 if orbs[x][1]==0 else -1 for x in occ) for occ in basis])
Sp=np.zeros((dim,dim))
for col,occ in enumerate(basis):
    for m in range(-2,3):
        r=apply_ann(list(occ),orbs.index((m,1)))
        if r is None: continue
        r2=apply_cre(r[1],orbs.index((m,0)))
        if r2 is None: continue
        Sp[idx[tuple(r2[1])],col]+=r[0]*r2[0]
S2=np.diag(Sz**2)+0.5*(Sp@Sp.T+Sp.T@Sp)
w,v=np.linalg.eigh(S2)
Q=v[:,np.abs(w-15/4)<1e-6]
P2=Q.T@H2@Q; P4=Q.T@H4@Q; PD=Q.T@HD@Q
def rel(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    return np.linalg.eigvalsh(F2*P2+F4*P4+Dq*PD)+(5/7)*(F2+F4)
# verify free-ion-ish and horizontal
print("check rel(0,600,2800)[:1]", rel(0,600,2800)[[0,40,90]], "expect 20000 for G, 24200 for D, 32800 F")
# Now: 10B+5C = 23370 -> 4E(G) horizontal; search Dq,B for T levels 19180 and 22130
res=[]
for B in np.arange(300,1201,5.0):
    C=(23370-10*B)/5
    if C<=0: continue
    for Dq in np.arange(200,1801,5.0):
        ev=rel(Dq,B,C)
        ev=np.unique(np.round(ev,3))
        d1=np.min(np.abs(ev-19180)); d2=np.min(np.abs(ev-22130))
        res.append((d1+d2,Dq,B,C))
res.sort()
for r in res[:15]: print(np.round(r,2))
