
cat << 'EOF' > /tmp/d7.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import least_squares
l=2; ms=range(-2,3)
def ck(k,m1,m2):  # c^k(l m1, l m2)
    return float((-1)**m1*np.sqrt(5*5)*gaunt(2,k,2,-m1,m1-m2,m2)*np.sqrt(4*np.pi/(2*k+1)))
so=[(m,s) for m in ms for s in (0,1)]
n=10
dets=list(itertools.combinations(range(n),7))
idx={d:i for i,d in enumerate(dets)}
# two-electron integrals <ab|cd>
def R(a,b,c,d,F):
    ma,sa=so[a];mb,sb=so[b];mc,sc=so[c];md,sd=so[d]
    if sa!=sc or sb!=sd or ma+mb!=mc+md: return 0
    return sum(F[k]*ck(k,ma,mc)*ck(k,md,mb) for k in (0,2,4))
import functools
def build(F,Dq):
    h=np.zeros((n,n))
    V={(0,0):6,(1,1):-4,(-1,-1):-4,(2,2):1,(-2,-2):1,(2,-2):5,(-2,2):5}
    for a in range(n):
        for b in range(n):
            if so[a][1]==so[b][1]: h[a,b]=V.get((so[a][0],so[b][0]),0)*Dq
    G=np.zeros((n,n,n,n))
    for a in range(n):
     for b in range(n):
      for c in range(n):
       for d in range(n):
        G[a,b,c,d]=R(a,b,c,d,F)
    return h,G
def apply(ops,det):
    # ops list of (type,orb) applied right-to-left
    st=list(det);sign=1
    for t,o in reversed(ops):
        if t=='a':
            if o not in st: return None,0
            p=st.index(o);sign*=(-1)**p;st.pop(p)
        else:
            if o in st: return None,0
            p=sum(1 for x in st if x<o);sign*=(-1)**p;st.insert(p,o)
    return tuple(st),sign
# precompute unit matrices
N=len(dets)
def mats():
    H1=np.zeros((n,n,N,N))
    for a in range(n):
        for b in range(n):
            for j,d in enumerate(dets):
                r,s=apply([('c',a),('a',b)],d)
                if r: H1[a,b,idx[r],j]+=s
    return H1
H1=mats()
def Hmat(h,G):
    H=np.einsum('ab,abij->ij',h,H1)
    # two-body 1/2 sum G[a,b,c,d] a+ b+ d c
    H2=np.zeros((N,N))
    for a in range(n):
     for b in range(n):
      for c in range(n):
       for d in range(n):
        g=G[a,b,c,d]
        if abs(g)<1e-12: continue
        for j,dt in enumerate(dets):
            r,s=apply([('c',a),('c',b),('a',d),('a',c)],dt)
            if r: H2[idx[r],j]+=0.5*g*s
    return H,H2
# Build basis matrices for F0=0: separate F2,F4 and Dq
def comp(F2,F4,Dq):
    h,G=build({0:0,2:F2,4:F4},Dq); return Hmat(h,G)
Hd,_=comp(0,0,1)
_,HF2=comp(1,0,0)
_,HF4=comp(0,1,0)
# Sz and S^2
Sz=np.diag([sum(0.5 if so[o][1]==0 else -0.5 for o in d) for d in dets])
Sp=np.zeros((N,N))
for m in ms:
    up=so.index((m,0));dn=so.index((m,1))
    for j,d in enumerate(dets):
        r,s=apply([('c',up),('a',dn)],d)
        if r: Sp[idx[r],j]+=s
S2=Sp.T@Sp+Sz@Sz+Sz
C4=np.zeros((N,N))
# orbital rotation: m -> phase i^m ... C4 acts diagonally
C4=np.diag([np.prod([np.exp(-1j*so[o][0]*np.pi/2) for o in d]) for d in dets])
np.savez('/tmp/m.npz',Hd=Hd,HF2=HF2,HF4=HF4,S2=S2,C4=C4)
EOF
python3 /tmp/d7.py && echo ok
