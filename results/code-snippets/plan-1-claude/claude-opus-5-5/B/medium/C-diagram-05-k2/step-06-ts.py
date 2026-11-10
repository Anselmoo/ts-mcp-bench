import numpy as np, itertools
from sympy.physics.wigner import gaunt
B=859.;C=3660.
F2=49*B+7*C; F4=441*C/35
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    q=m1-m2
    if abs(q)>k: return 0.
    return float((-1)**m1*np.sqrt(4*np.pi/(2*k+1))*5*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (2,4) for a in ms for b in ms}
Fk={2:F2,4:F4}
def U(a,b,c,d):
    if a+b!=c+d: return 0.
    return sum(Fk[k]*CK[(k,a,c)]*CK[(k,d,b)] for k in (2,4))
so=[(m,s) for m in ms for s in (1,-1)]
dets=list(itertools.combinations(range(10),7)); idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def ann(st,o):
    if o not in st: return None
    i=st.index(o); st.pop(i); return (-1)**i
def cre(st,o):
    if o in st: return None
    k=sum(1 for x in st if x<o); st.insert(k,o); return (-1)**k
def op(d,seq):  # seq list of ('a'|'c',orb) applied right to left as given order (first applied first)
    st=list(d); sg=1
    for t,o in seq:
        r=ann(st,o) if t=='a' else cre(st,o)
        if r is None: return None,0
        sg*=r
    return tuple(st),sg
Hee=np.zeros((N,N))
for j,d in enumerate(dets):
  for p in range(10):
    for q in range(10):
      for r in range(10):
        for s in range(10):
          if so[p][1]!=so[r][1] or so[q][1]!=so[s][1]: continue
          v=U(so[p][0],so[q][0],so[r][0],so[s][0])
          if v==0: continue
          nd,sg=op(d,[('a',r),('a',s),('c',q),('c',p)])
          if nd is None: continue
          Hee[idx[nd],j]+=0.5*v*sg
Vm=np.zeros((5,5))
for m,v in zip(ms,[1,-4,6,-4,1]): Vm[m+2,m+2]=v
Vm[0,4]=Vm[4,0]=5
def one(mat):  # mat[(r,p)] over spin-orbitals
    H=np.zeros((N,N))
    for j,d in enumerate(dets):
        for (r,p),v in mat.items():
            nd,sg=op(d,[('a',p),('c',r)])
            if nd is None: continue
            H[idx[nd],j]+=v*sg
    return H
Hcf=one({(r,p):Vm[so[r][0]+2,so[p][0]+2] for r in range(10) for p in range(10) if so[r][1]==so[p][1] and Vm[so[r][0]+2,so[p][0]+2]!=0})
Sp=one({(so.index((m,1)),so.index((m,-1))):1. for m in ms})
Sz=np.diag([sum(so[p][1] for p in d)/2 for d in dets])
S2=Sp.T@Sp+Sz@Sz+Sz
lp=lambda m: np.sqrt(6-m*(m+1))
Lp=one({(so.index((m+1,s)),so.index((m,s))):lp(m) for m in ms[:-1] for s in (1,-1)})
ML=np.array([sum(so[p][0] for p in d) for d in dets]); Lz=np.diag(ML)
L2=Lp.T@Lp+Lz@Lz+Lz
np.savez('<SANDBOX_TMP>/H.npz',Hee=Hee,Hcf=Hcf,S2=S2,L2=L2,ML=ML)
