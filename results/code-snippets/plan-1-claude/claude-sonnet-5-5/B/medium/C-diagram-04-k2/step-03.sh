cat > a.py <<'E'
import numpy as np, itertools, hashlib, json
from sympy.physics.wigner import gaunt
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
B=551.;C=2511.
F2=49*B+7*C; F4=63*C/5
ms=[-2,-1,0,1,2]
def c(k,a,cc): return float((-1)**a*5*gaunt(2,k,2,-a,a-cc,cc))
Fk={2:F2/49,4:F4/441}
V={}
for a in ms:
 for b in ms:
  for cc in ms:
   for d in ms:
    if a+b!=cc+d: continue
    V[a,b,cc,d]=sum(c(k,a,cc)*c(k,d,b)*Fk[k] for k in (2,4))
def cfm(Dq):
    e1=np.zeros(5);e1[2]=1
    e2=np.zeros(5);e2[0]=e2[4]=1/np.sqrt(2)
    H=-4*Dq*np.eye(5)
    for e in (e1,e2): H+=10*Dq*np.outer(e,e)
    return H
dets=[x for x in itertools.combinations(range(10),6) if sum(1 for i in x if i>=5)==3]
di={x:i for i,x in enumerate(dets)}
N=len(dets)
def app(op,det):
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
            if abs(h[a,b])<1e-14: continue
            r=app([('c',s*5+a),('a',s*5+b)],det)
            if r: H[di[r[1]],j]+=r[0]*h[a,b]
    for (a,b,cc,d),v in V.items():
        if abs(v)<1e-12: continue
        for s in (0,1):
         for t in (0,1):
          A=s*5+a+2;Bq=t*5+b+2;Cq=s*5+cc+2;D=t*5+d+2
          for det in dets:
            r=app([('c',A),('c',Bq),('a',D),('a',Cq)],det)
            if r: H[di[r[1]],di[det]]+=0.5*v*r[0]
    return H
Sm=np.zeros((N,N))
for det in dets:
    for m in range(5):
        r=app([('c',m),('a',5+m)],det)
        if r: Sm[di[r[1]],di[det]]+=r[0]
Sz=np.diag([0.0]*N)
S2=Sm.T@Sm
C4=np.diag([np.prod([np.exp(-1j*np.pi/2*ms[i%5]) for i in d]) for d in dets])
lab={(1,1.0):'A1',(1,-1.0):'A2',(2,0.0):'E',(3,1.0):'T1',(3,-1.0):'T2'}
res={}
for Dqb in np.arange(0,4.01,.5):
    Dq=Dqb*B if Dqb>0 else 1e-4*B
    H=build(Dq); H=(H+H.conj().T)/2
    w,U=np.linalg.eigh(H)
    out=[];i=0
    while i<N:
        j=i
        while j+1<N and w[j+1]-w[i]<1e-3: j+=1
        sub=U[:,i:j+1]; dim=j-i+1
        s2=np.trace(sub.conj().T@S2@sub).real/dim
        S=(-1+np.sqrt(1+4*s2))/2
        ch=np.trace(sub.conj().T@C4@sub).real/1
        term='^%d%s'%(round(2*S+1),lab.get((dim,round(ch))," ?%d %.2f"%(dim,ch)))
        out.append((w[i],term));i=j+1
    e0=out[0][0]
    res[Dqb]=[(t,(e-e0)/B) for e,t in out]
    print(Dqb,[(t,round(e,3)) for t,e in res[Dqb][:8]])
E
python3 a.py