cat > t.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from math import pi,sqrt
B=859.;C=3660.
F4=C/35;F2=B+5*F4;Fk={2:49*F2,4:441*F4}
def a(k,m1,m3):
    if abs(m1-m3)>k: return 0.
    return float(sqrt(4*pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,m1-m3,m3))
A={k:np.array([[a(k,i,j) for j in range(-2,3)] for i in range(-2,3)]) for k in (2,4)}
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
def g(p,q,r,s_):
    (m1,s1),(m2,s2),(m3,s3),(m4,s4)=orbs[p],orbs[q],orbs[r],orbs[s_]
    if s1!=s3 or s2!=s4: return 0.
    return sum(Fk[k]*A[k][m1+2,m3+2]*A[k][m4+2,m2+2] for k in (2,4))
dets=list(itertools.combinations(range(10),7));idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def ann(d,i):
    if i not in d: return None
    return (-1)**d.index(i),tuple(x for x in d if x!=i)
def cre(d,i):
    if i in d: return None
    return (-1)**sum(1 for x in d if x<i),tuple(sorted(d+(i,)))
G={}
for p in range(10):
 for q in range(10):
  for r in range(10):
   for s in range(10):
    if p!=q and r!=s:
      v=g(p,q,r,s)
      if abs(v)>1e-9: G[(p,q,r,s)]=v
def build(Dq):
    H=np.zeros((N,N))
    P=np.zeros((5,5));P[2,2]=1
    v=np.zeros(5);v[0]=v[4]=1;P+=np.outer(v,v)/2
    h1=-4*Dq*np.eye(5)+10*Dq*P
    for d in dets:
        j=idx[d]
        for p in range(10):
          for r in range(10):
            if orbs[p][1]!=orbs[r][1]: continue
            h=h1[orbs[p][0]+2,orbs[r][0]+2]
            if h==0: continue
            x=ann(d,r)
            if not x: continue
            y=cre(x[1],p)
            if not y: continue
            H[idx[y[1]],j]+=h*x[0]*y[0]
        for (p,q,r,s),val in G.items():
            x=ann(d,r)
            if not x: continue
            x2=ann(x[1],s)
            if not x2: continue
            y=cre(x2[1],q)
            if not y: continue
            y2=cre(y[1],p)
            if not y2: continue
            H[idx[y2[1]],j]+=0.5*val*x[0]*x2[0]*y[0]*y2[0]
    return H
Sm=np.zeros((N,N))
for d in dets:
    for m in range(-2,3):
        x=ann(d,orbs.index((m,0)))
        if not x: continue
        y=cre(x[1],orbs.index((m,1)))
        if not y: continue
        Sm[idx[y[1]],idx[d]]+=x[0]*y[0]
Sz=np.diag([sum(0.5 if orbs[i][1]==0 else -0.5 for i in d) for d in dets])
S2=Sm@Sm.T+Sz@Sz+Sz
ph=np.array([np.exp(-1j*m*pi/2) for m,s in orbs])
C4=np.diag([np.prod([ph[i] for i in d]) for d in dets])
names={(1,1):'A1',(1,-1):'A2',(2,0):'E',(3,1):'T1',(3,-1):'T2'}
def levels(Dq):
    H=build(Dq*B)
    w,V=np.linalg.eigh(H+1e-2*S2)
    out=[];i=0
    while i<N:
        j=i
        while j<N and abs(w[j]-w[i])<0.3: j+=1
        Vs=V[:,i:j];deg=j-i
        s2=np.trace(Vs.conj().T@S2@Vs).real/deg
        S=(-1+sqrt(1+4*s2))/2;mult=round(2*S+1)
        ch=np.trace(Vs.conj().T@C4@Vs).real/mult
        e=np.trace(Vs.conj().T@H@Vs).real/deg
        out.append([e,mult,round(deg/mult),round(ch)])
        i=j
    return out
if __name__=="__main__":
  import json
  allr={}
  for Dq in np.arange(0,4.01,.5):
    out=levels(Dq);e0=out[0][0]
    allr[Dq]=[(f"{m}{names.get((o,c),(o,c))}",(e-e0)/B) for e,m,o,c in out]
    print(Dq,[(n,round(e,3)) for n,e in allr[Dq][:9]])
E
python3 t.py