
cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from scipy.optimize import brentq
B,C=803.,3078.
F4=441*C/35; F2=49*B+7*C; F={0:0.0,2:F2,4:F4}
ms=[-2,-1,0,1,2]
# ck(l=2,m;2,m') = sqrt(4pi/(2k+1)) * gaunt
def ck(k,m1,m2):
    q=m1-m2
    return float(np.sqrt(4*np.pi/(2*k+1))*(-1)**m1*gaunt(2,k,2,-m1,q,m2))
CK={(k,a,b):ck(k,a,b) for k in (0,2,4) for a in ms for b in ms}
def U(m1,m2,m3,m4): # <m1 m2|1/r|m3 m4>
    if m1+m2!=m3+m4: return 0.
    return sum(F[k]*CK[(k,m1,m3)]*CK[(k,m4,m2)] for k in (0,2,4))
so=[(m,s) for m in ms for s in (0,1)]
states=list(itertools.combinations(range(10),6)); idx={s:i for i,s in enumerate(states)}
N=len(states)
def hcf():
    h=np.zeros((10,10))
    d={0:6,1:-4,-1:-4,2:1,-2:1}
    for i,(m,s) in enumerate(so):
        h[i,i]=d[m]
        for j,(m2,s2) in enumerate(so):
            if s==s2 and abs(m-m2)==4: h[i,j]=5
    return h
h1=hcf()
def apply_one(st,h):
    out={}
    for p in st:
        for q in range(10):
            if h[q,p]==0: continue
            if q!=p and q in st: continue
            l=list(st); pos=l.index(p); l[pos]=q
            sign=1
            # sort with sign
            arr=l[:]
            for a in range(len(arr)):
                for b in range(len(arr)-1-a):
                    if arr[b]>arr[b+1]: arr[b],arr[b+1]=arr[b+1],arr[b]; sign=-sign
            out[tuple(arr)]=out.get(tuple(arr),0)+sign*h[q,p]
    return out
H1=np.zeros((N,N))
for i,st in enumerate(states):
    for k,v in apply_one(st,h1).items(): H1[idx[k],i]+=v
# two-body: a+_i a+_j a_l a_k with 1/2 sum <ij|kl>
H2=np.zeros((N,N))
def ann(st,p):
    if p not in st: return None,0
    l=list(st); s=(-1)**l.index(p); l.remove(p); return l,s
def cre(l,p):
    if p in l: return None,0
    n=sum(1 for x in l if x<p); l2=sorted(l+[p]); return l2,(-1)**n
for i,st in enumerate(states):
    for k in st:
        for l_ in st:
            if k==l_: continue
            a,s1=ann(st,k); a,s2=ann(a,l_)
            for ii in range(10):
                for jj in range(10):
                    if so[ii][1]!=so[k][1] or so[jj][1]!=so[l_][1]: continue
                    v=U(so[ii][0],so[jj][0],so[k][0],so[l_][0])
                    if v==0: continue
                    b,s3=cre(a,jj)
                    if b is None: continue
                    c,s4=cre(b,ii)
                    if c is None: continue
                    H2[idx[tuple(c)],i]+=0.5*v*s1*s2*s3*s4
# S^2 to classify
def Ms(st): return sum(0.5 if so[p][1]==0 else -0.5 for p in st)
def gaps(Dq):
    E,V=np.linalg.eigh(H2+Dq*H1)
    # spin via S+S- ; simpler: quintets have Ms=2 components
    Msv=np.array([Ms(s) for s in states])
    res=[]
    for e,v in zip(E,V.T):
        w=v**2
        res.append((e,np.dot(w,Msv**2)))
    return E,res
# lowest quintet = lowest state in Ms=2 subspace; lowest singlet: need S. use S^2
Splus=np.zeros((N,N))
for i,st in enumerate(states):
    for p in st:
        if so[p][1]==1:
            q=p-1
            if q in st: continue
            l=list(st); l.remove(p); n=sum(1 for x in l if x<q); s1=(-1)**list(st).index(p)
            c=sorted(l+[q]); Splus[idx[tuple(c)],i]+=s1*(-1)**n
Msv=np.array([Ms(s) for s in states])
S2=Splus.T@Splus+np.diag(Msv**2+Msv)
def f(Dq):
    E,V=np.linalg.eigh(H2+Dq*H1+1e-3*S2)
    s=np.array([v@S2@v for v in V.T])
    eq=min(E[np.abs(s-6)<0.1]); es=min(E[np.abs(s)<0.1])
    return eq-es
for d in [1500,2000,2500,3000]: print(d,f(d))
print(brentq(f,1000,4000,xtol=1e-6))
EOF
python3 /tmp/d6.py
