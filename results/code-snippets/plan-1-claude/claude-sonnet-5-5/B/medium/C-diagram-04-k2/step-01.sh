cat > /tmp/a.py <<'E'
import numpy as np, itertools, hashlib
from sympy.physics.wigner import gaunt
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
B=551.;C=2511.
F2=49*B+7*C; F4=63*C/5
ms=[-2,-1,0,1,2]
def ck(k,m1,m2): # <2m1|C^k|2m2>
    return float((-1)**m1*gaunt(2,k,2,-m1,m1-m2,m2)*5) if True else 0
# Coulomb: <ab|1/r|cd> = sum_k c^k(a,c)c^k(b,d)F^k  with c^k(m1,m2)=<m1|C^k_{m1-m2}|m2>
def c(k,a,cc): return float((-1)**a*5*gaunt(2,k,2,-a,a-cc,cc))
Fk={0:0,2:F2/49,4:F4/441}
V={}
for a in ms:
 for b in ms:
  for cc in ms:
   for d in ms:
    if a+b!=cc+d: continue
    V[a,b,cc,d]=sum(c(k,a,cc)*c(k,d,b)*Fk[k] for k in (2,4))
so=[(m,s) for s in (0,1) for m in ms]  # s=0 up
n=10
def idx(m,s): return so.index((m,s))
# CF in m basis
Dm=np.zeros((5,5),complex)
def cfm(Dq):
    # real-basis: eg(z2,x2-y2)=+6Dq, t2g=-4Dq ; eg combination: m=0, (2+-2)/sqrt2
    P=np.zeros((5,5),complex)
    v=[np.eye(5)[2]]
    e1=np.zeros(5);e1[2]=1
    e2=np.zeros(5);e2[0]=e2[4]=1/np.sqrt(2)
    H=-4*Dq*np.eye(5)
    for e in (e1,e2): H+=10*Dq*np.outer(e,e)
    return H
dets=[x for x in itertools.combinations(range(10),6) if sum(1 for i in x if i>=5)==3]
di={x:i for i,x in enumerate(dets)}
N=len(dets)
def apply_c(op,det):
    # op list of (creat/ann, orb) applied right-to-left; return (sign,newdet) or None
    l=list(det);sg=1
    for typ,o in reversed(op):
        if typ=='a':
            if o not in l: return None
            p=l.index(o); sg*=(-1)**p; l.pop(p)
        else:
            if o in l: return None
            p=sum(1 for x in l if x<o); sg*=(-1)**p; l.insert(p,o)
    return sg,tuple(l)
def build(Dq):
    H=np.zeros((N,N),complex)
    h=cfm(Dq)
    for det in dets:
        j=di[det]
        for s in (0,1):
         for a in range(5):
          for b in range(5):
            if h[a,b]==0: continue
            r=apply_c([('c',s*5+a),('a',s*5+b)],det)
            if r: H[di[r[1]],j]+=r[0]*h[a,b]
    # two-body 1/2 sum V(ab|cd) a+_a s a+_b s' a_d s' a_c s
    for (a,b,cc,d),v in V.items():
        if abs(v)<1e-12: continue
        for s in (0,1):
         for t in (0,1):
          A=idx(a,s);Bq=idx(b,t);Cq=idx(cc,s);D=idx(d,t)
          for det in dets:
            r=apply_c([('c',A),('c',Bq),('a',D),('a',Cq)],det)
            if r: H[di[r[1]],di[det]]+=0.5*v*r[0]
    return H
# S^2 and C4
S2=np.zeros((N,N))
def sp(det):pass
Sm=np.zeros((N,N));
for det in dets:
    for m in range(5):
        r=apply_c([('c',m),('a',5+m)],det)  # S+ : down->up
        if r: Sm[di[r[1]],di[det]]+=r[0]
Sz=np.diag([ (sum(1 for i in d if i<5)-sum(1 for i in d if i>=5))/2 for d in dets])
S2=Sm@Sm.T+Sz@Sz-Sz  # S-S+ + Sz^2+Sz ; S-S+ = S+^T S+ ... fix below
S2=Sm.T@Sm+Sz@Sz+Sz
C4=np.diag([np.prod([np.exp(-1j*np.pi/2*ms[i%5]) for i in d]) for d in dets])
res={}
for Dqb in np.arange(0,4.01,.5):
    Dq=Dqb*B if Dqb>0 else 1e-6*B
    H=build(Dq); H=(H+H.conj().T)/2
    w,U=np.linalg.eigh(H)
    # cluster
    out=[];i=0
    while i<N:
        j=i
        while j+1<N and w[j+1]-w[i]<1e-3*B*0+1e-4*B+ (1e-3 if Dqb==0 else 0): j+=1
        sub=U[:,i:j+1]; dim=j-i+1
        S=(-1+np.sqrt(1+4*np.trace(sub.conj().T@S2@sub).real/dim))/2
        ch=np.trace(sub.conj().T@C4@sub).real
        out.append((w[i],dim,round(S*2)/2,round(ch,2)));i=j+1
    res[Dqb]=out
    print(Dqb,[(round(o[0]/B,3),o[1],o[2],o[3]) for o in out[:10]])
E
cd /tmp && python3 a.py