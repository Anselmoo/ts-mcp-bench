mkdir -p /dev/shm/w && cd /dev/shm/w && cat > a.py <<'E'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
l=2;ms=[-2,-1,0,1,2]
def ck(k,m,mp):
    q=m-mp
    if abs(q)>k: return 0.0
    return float((-1)**m*5*wigner_3j(l,k,l,0,0,0)*wigner_3j(l,k,l,-m,q,mp))
CK={k:np.array([[ck(k,a,b) for b in ms] for a in ms]) for k in (0,2,4)}
def V(a,b,c,d,F):
    if ms[a]+ms[b]!=ms[c]+ms[d]: return 0.0
    return sum(CK[k][a,c]*CK[k][d,b]*F[k] for k in (2,4))
s=1/np.sqrt(2)
U=np.zeros((5,5),complex)
def idx(m):return m+2
U[idx(0),0]=1
U[idx(2),1]=s;U[idx(-2),1]=s
U[idx(2),2]=-1j*s;U[idx(-2),2]=1j*s
U[idx(1),3]=s;U[idx(-1),3]=-s
U[idx(1),4]=1j*s;U[idx(-1),4]=1j*s
def h1(Dq):
    d=np.diag([6*Dq]*2+[-4*Dq]*3)
    return U@d@U.conj().T
dets=[]
for ups in itertools.combinations(range(5),4):
    for dn in range(5):
        dets.append(tuple(sorted([2*o for o in ups]+[2*dn+1])))
ix={d:i for i,d in enumerate(dets)}
def ann(p,st):
    if p not in st: return None
    i=st.index(p);return (-1)**i,tuple(x for x in st if x!=p)
def cre(p,st):
    if p in st: return None
    i=sum(1 for x in st if x<p);return (-1)**i,tuple(sorted(st+(p,)))
# precompute operator structure
one=[];two=[]
for j,st in enumerate(dets):
    for p in range(10):
        r1=ann(p,st)
        if not r1: continue
        for q in range(10):
            if p%2!=q%2: continue
            r2=cre(q,r1[1])
            if r2: one.append((ix[r2[1]],j,q//2,p//2,r1[0]*r2[0]))
    for c in range(10):
      r1=ann(c,st)
      if not r1: continue
      for d in range(10):
        if d==c: continue
        r2=ann(d,r1[1])
        if not r2: continue
        for a in range(10):
          if a%2!=c%2: continue
          for b in range(10):
            if b%2!=d%2 or a==b: continue
            r3=cre(b,r2[1])
            if not r3: continue
            r4=cre(a,r3[1])
            if not r4: continue
            two.append((ix[r4[1]],j,a//2,b//2,c//2,d//2,0.5*r1[0]*r2[0]*r3[0]*r4[0]))
def energies(Dq,B,C):
    F={2:49*B+7*C,4:63*C/5}
    h=h1(Dq);n=len(dets);H=np.zeros((n,n),complex)
    for i,j,q,p,s_ in one: H[i,j]+=s_*h[q,p]
    for i,j,a,b,c,d,s_ in two:
        v=V(a,b,c,d,F)
        if v: H[i,j]+=s_*v
    w=np.linalg.eigvalsh(H);return w-w[0]
def levels(w):
    out=[]
    for x in w:
        if out and abs(x-out[-1][0])<1e-6: out[-1][1]+=1
        else: out.append([x,1])
    return out
if __name__=="__main__":
    for L in levels(energies(0,800,3000)): print(L)
    print()
    for L in levels(energies(1000,800,3000)): print(L)
E
python3 a.py