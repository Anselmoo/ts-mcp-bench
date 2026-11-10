
D=<SANDBOX_TMP>; cat << 'EOF' > $D/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=range(-2,3)
def ck(k,m1,m2):
    return float((-1)**m1*5*gaunt(2,k,2,-m1,m1-m2,m2)*np.sqrt(4*np.pi/(2*k+1)))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
so=[(m,s) for m in ms for s in (0,1)]
n=10
dets=list(itertools.combinations(range(n),7))
idx={d:i for i,d in enumerate(dets)}
N=len(dets)
def apply(ops,det):
    st=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return None,0
            p=st.index(o);sign*=(-1)**p;st.pop(p)
        else:
            if o in st: return None,0
            p=sum(1 for x in st if x<o);sign*=(-1)**p;st.insert(p,o)
    return tuple(st),sign
V={(0,0):6,(1,1):-4,(-1,-1):-4,(2,2):1,(-2,-2):1,(2,-2):5,(-2,2):5}
Hd=np.zeros((N,N))
for a in range(n):
  for b in range(n):
    if so[a][1]!=so[b][1]: continue
    v=V.get((so[a][0],so[b][0]),0)
    if not v: continue
    for j,d in enumerate(dets):
        r,s=apply([('c',a),('a',b)],d)
        if r: Hd[idx[r],j]+=s*v
HF={2:np.zeros((N,N)),4:np.zeros((N,N))}
for a in range(n):
 for b in range(n):
  for c in range(n):
   for d in range(n):
    ma,sa=so[a];mb,sb=so[b];mc,sc=so[c];md,sd=so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: continue
    for k in (2,4):
      g=CK[(k,ma,mc)]*CK[(k,md,mb)]
      if abs(g)<1e-12: continue
      for j,dt in enumerate(dets):
        r,s=apply([('c',a),('c',b),('a',d),('a',c)],dt)
        if r: HF[k][idx[r],j]+=0.5*g*s
Sz=np.diag([sum(0.5 if so[o][1]==0 else -0.5 for o in d) for d in dets])
Sp=np.zeros((N,N))
for m in ms:
    up=so.index((m,0));dn=so.index((m,1))
    for j,d in enumerate(dets):
        r,s=apply([('c',up),('a',dn)],d)
        if r: Sp[idx[r],j]+=s
S2=Sp.T@Sp+Sz@Sz+Sz
C4=np.diag([np.prod([np.exp(-1j*so[o][0]*np.pi/2) for o in d]) for d in dets])
np.savez('<SANDBOX_TMP>/m.npz',Hd=Hd,F2=HF[2],F4=HF[4],S2=S2,C4=C4)
print(np.abs(Hd-Hd.T).max(),np.abs(HF[2]-HF[2].T).max())
EOF
python3 $D/d7.py
