
cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
ms=[-2,-1,0,1,2]
def ck(k,m1,m2):
    # c^k(l m1, l m2) = sqrt(4pi/(2k+1)) * int Y*_{m1} Y_{k,m1-m2} Y_{m2}
    q=m1-m2
    if abs(q)>k: return 0.0
    g=float(gaunt(2,k,2,-m1,q,m2))*(-1)**m1
    return np.sqrt(4*np.pi/(2*k+1))*g
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
orbs=[(m,s) for m in ms for s in (0,1)]
dets=list(itertools.combinations(range(10),6))
idx={d:i for i,d in enumerate(dets)}
def V(Dq):
    M=np.zeros((5,5))
    for i,m in enumerate(ms):
        M[i,i]={2:1,1:-4,0:6}[abs(m)]*Dq
    M[0,4]=M[4,0]=5*Dq
    return M
def g2(a,b,c,d,F):
    # <ab|cd>, spin orbitals
    (ma,sa),(mb,sb),(mc,sc),(md,sd)=orbs[a],orbs[b],orbs[c],orbs[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0.0
    return sum(CK[(k,ma,mc)]*CK[(k,md,mb)]*F[k] for k in (2,4))
def apply(ops,det):
    # ops list of (type,orb) applied right to left; returns sign, newdet
    det=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in det: return 0,None
            p=det.index(o);sign*=(-1)**p;det.pop(p)
        else:
            if o in det: return 0,None
            p=sum(1 for x in det if x<o);sign*=(-1)**p;det.insert(p,o)
    return sign,tuple(det)
# precompute
N=len(dets)
def H(Dq,B,C):
    F={2:49*(B+C/7),4:441*C/35}
    Vm=V(Dq);Hm=np.zeros((N,N))
    for j,d in enumerate(dets):
        for p in range(10):
            for q in range(10):
                if orbs[p][1]!=orbs[q][1]: continue
                v=Vm[ms.index(orbs[p][0]),ms.index(orbs[q][0])]
                if v==0: continue
                s,nd=apply([('c',p),('a',q)],d)
                if s: Hm[idx[nd],j]+=s*v
        for a in range(10):
          for b in range(10):
            for c in d:
              for e in d:
                if c==e or a==b: continue
                val=g2(a,b,c,e,F)
                if val==0: continue
                s,nd=apply([('c',a),('c',b),('a',e),('a',c)],d)
                if s: Hm[idx[nd],j]+=0.5*s*val
    return Hm
# S^2
S2=np.zeros((N,N))
for j,d in enumerate(dets):
    for p in range(10):
        for q in range(10):
            for r in range(10):
                for t in range(10):
                    pass
# simpler: compute Sz and S+S-
def op1(f):
    M=np.zeros((N,N))
    for j,d in enumerate(dets):
        for p,q,v in f:
            s,nd=apply([('c',p),('a',q)],d)
            if s: M[idx[nd],j]+=s*v
    return M
Sp=op1([(2*i+0,2*i+1,1.0) for i in range(5)])  # spin index 0 = up
Sz=np.diag([sum(0.5 if orbs[o][1]==0 else -0.5 for o in d) for d in dets])
S2m=Sp.T@Sp+Sz@Sz+Sz
import pickle
H0=H(0,0,0)
HD=H(1,0,0)-H0; HB=H(0,1,0)-H0; HC=H(0,0,1)-H0
np.save('/tmp/m.npy',np.array([HD,HB,HC,S2m,Sz]))
EOF
python3 /tmp/d6.py && echo ok
