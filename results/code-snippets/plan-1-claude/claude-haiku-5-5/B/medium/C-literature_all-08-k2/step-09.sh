cd /; python3 - << 'EOF'
import numpy as np, itertools, collections
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
np.set_printoptions(linewidth=200)
print("HD symmetric:", np.allclose(HD,HD.T), " H2 sym:", np.allclose(H2,H2.T))
w,v=np.linalg.eigh(S2)
Q=v[:,np.abs(w-15/4)<1e-6]
Qs=v[:,np.abs(w-35/4)<1e-6]
def levels(Dq,B,C):
    F2=49*B+7*C; F4=12.6*C
    H=F2*H2+F4*H4+Dq*HD
    ev,_=np.linalg.eigh(Q.T@H@Q)
    evs=np.linalg.eigvalsh(Qs.T@H@Qs)
    return ev, evs
for Dq in [0,500,1000]:
    ev,evs=levels(Dq,600,2800)
    print("Dq",Dq,"sextet",np.round(evs[0],2))
    cl=collections.Counter(np.round(ev-evs[0],2))
    print(sorted(cl.items()))
# trace check: trace of HD over quartet subspace
print("trace HD quartet:", np.trace(Q.T@HD@Q), " expect 0 (sum of 10Dq-weighted?)")
EOF