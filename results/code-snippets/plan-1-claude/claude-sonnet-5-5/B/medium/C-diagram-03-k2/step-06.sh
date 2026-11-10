cd /tmp/tsbench-run-l39pr0fd; rm x; cat > ts.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from sympy import N
l=2; ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float((-1)**m*(2*l+1)*N(wigner_3j(l,k,l,0,0,0))*N(wigner_3j(l,k,l,-m,q,mp)))
C={(k,a,b):ck(k,ms[a],ms[b]) for k in (2,4) for a in range(5) for b in range(5)}
dets=list(itertools.combinations(range(10),5))
idx={d:i for i,d in enumerate(dets)}
n=len(dets)
def apply_ops(det,ops):
    s=list(det); sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in s: return None
            p=s.index(o); sign*=(-1)**p; s.remove(o)
        else:
            if o in s: return None
            p=sum(1 for x in s if x<o); sign*=(-1)**p; s.insert(p,o)
    return sign,tuple(s)
# orbital index 2*a+s, s=0 up,1 down
Sp=np.zeros((n,n))
for j,det in enumerate(dets):
    for a in range(5):
        r=apply_ops(det,[('c',2*a),('a',2*a+1)])
        if r: Sp[idx[r[1]],j]+=r[0]
Sz=np.diag([sum(0.5 if o%2==0 else -0.5 for o in d) for d in dets])
S2=Sp.T@Sp+Sz@Sz+Sz
# note S2=S-S+ +Sz^2+Sz with S-=Sp.T
V={}
for a in range(5):
 for b in range(5):
  for c in range(5):
   for d in range(5):
    if ms[a]+ms[b]!=ms[c]+ms[d]: continue
    V[(a,b,c,d)]={k:C[(k,a,c)]*C[(k,d,b)] for k in (2,4)}
trans=[]
for j,det in enumerate(dets):
    for (a,b,c,d),vk in V.items():
        for s1 in (0,1):
          for s2 in (0,1):
            r=apply_ops(det,[('c',2*a+s1),('c',2*b+s2),('a',2*d+s2),('a',2*c+s1)])
            if r: trans.append((idx[r[1]],j,r[0]*0.5,vk[2],vk[4]))
T=np.array(trans)
H2={k:np.zeros((n,n)) for k in (2,4)}
for i,j,s,v2,v4 in trans:
    H2[2][int(i),int(j)]+=s*v2; H2[4][int(i),int(j)]+=s*v4
H1=np.zeros((n,n))
h=np.zeros((5,5))
for i,m in enumerate(ms): h[i,i]={0:6,1:-4,-1:-4,2:1,-2:1}[m]
h[0,4]=h[4,0]=5
for j,det in enumerate(dets):
    for a in range(5):
      for c in range(5):
        if h[a,c]==0: continue
        for s in (0,1):
            r=apply_ops(det,[('c',2*a+s),('a',2*c+s)])
            if r: H1[idx[r[1]],j]+=h[a,c]*r[0]
# rotations
def U5(kind):
    if kind=='C4': return np.diag([np.exp(-1j*m*np.pi/2) for m in ms])
    phi=np.pi/4
    Rz=np.diag([np.exp(-1j*m*phi) for m in ms])
    Rx=np.zeros((5,5),complex)
    for i,m in enumerate(ms): Rx[ms.index(-m),i]=1
    return Rz@Rx@Rz.conj().T
def many(U5m):
    U=np.kron(U5m,np.eye(2)); R=np.zeros((n,n),complex)
    for j,dj in enumerate(dets):
        for i,di in enumerate(dets):
            R[i,j]=np.linalg.det(U[np.ix_(di,dj)])
    return R
R4=many(U5('C4')); R2=many(U5('C2'))
def solve(B,Cc,Dq):
    H=H2[2]*(49*B+7*Cc)+H2[4]*12.6*Cc+H1*Dq*B
    w,v=np.linalg.eigh(H+1e-3*S2*0)  # plain
    return H,w,v
def levels(B,Cc,x):
    H=H2[2]*(49*B+7*Cc)+H2[4]*12.6*Cc+H1*x*B
    # add tiny perturbations? use grouping of degenerate clusters
    w,v=np.linalg.eigh(H)
    out=[];i=0
    while i<n:
        j=i
        while j<n and abs(w[j]-w[i])<1e-6*max(1,B): j+=1
        P=v[:,i:j]; deg=j-i
        s2=np.trace(P.T@S2@P).real/deg
        S=(-1+np.sqrt(1+4*s2))/2
        c4=np.trace(P.conj().T@R4@P).real; c2=np.trace(P.conj().T@R2@P).real
        out.append((w[i],deg,S,round(c4,3),round(c2,3)))
        i=j
    return out
def label(deg,S,c4,c2,deg_div):
    pass
E
cat > run.py <<'E'
from ts import *
B=806.;Cc=3570.
def lab(d,S,c4,c2):
    mult=int(round(2*S+1)); 
    # character per orbital irreps: dim from d/(mult)?? deg counts spin comps? 
    return mult
for x in [0,1,2,3,4]:
    o=levels(B,Cc,x)
    print(x)
    for w,deg,S,c4,c2 in o[:14]: print(round(w/B,3),deg,round(S,2),c4,c2)
E
python3 run.py