mkdir -p /tmp/w && cd /tmp/w && cat > t.py <<'E'
import numpy as np, itertools, sys
from sympy.physics.wigner import gaunt
from scipy.linalg import expm
B=551.;C=2511.
F={2:49*B+7*C,4:63*C/5}   # F4 = 441C/35
F[4]=441*C/35
F[2]=49*B+5*F[4]/9
ms=[-2,-1,0,1,2]
def g(m1,m2,m3,m4): # <m1 m2|g|m3 m4>
    t=0.
    for k in (2,4):
        s=0.
        for q in range(-k,k+1):
            if m1-m3!=-q and True: pass
            a=float((-1)**m1*gaunt(2,k,2,-m1,q,m3))
            if a==0: continue
            b=float((-1)**q*(-1)**m2*gaunt(2,k,2,-m2,-q,m4))
            s+=a*b
        t+=F[k]*s*4*np.pi/(2*k+1)* (1) 
    return t
V=np.zeros((5,5,5,5))
for i,j,k,l in itertools.product(range(5),repeat=4):
    if ms[i]+ms[j]==ms[k]+ms[l]: V[i,j,k,l]=g(ms[i],ms[j],ms[k],ms[l])
# check Racah: 
def hmat(Dq):
    h=np.diag([Dq,-4*Dq,6*Dq,-4*Dq,Dq]).astype(complex); h[0,4]=h[4,0]=5*Dq
    return h
# basis Ms=0: 3 up 3 down
dets=[]
for u in itertools.combinations(range(5),3):
    for d in itertools.combinations(range(5),3):
        dets.append(sum(1<<i for i in u)|sum(1<<(5+i) for i in d))
idx={d:i for i,d in enumerate(dets)}
def ann(p,s):
    if not s>>p&1: return None
    return s&~(1<<p), (-1)**bin(s&((1<<p)-1)).count('1')
def cre(p,s):
    if s>>p&1: return None
    return s|(1<<p), (-1)**bin(s&((1<<p)-1)).count('1')
def apply(ops,s):
    sg=1
    for typ,p in reversed(ops):
        r=(ann if typ=='a' else cre)(p,s)
        if r is None: return None
        s,x=r; sg*=x
    return s,sg
N=len(dets)
H2=np.zeros((N,N))
for n,s0 in enumerate(dets):
    for sp in (0,5):
      for tp in (0,5):
        for p,q,r,s in itertools.product(range(5),repeat=4):
            v=V[p,q,r,s]
            if v==0: continue
            res=apply([('c',p+sp),('c',q+tp),('a',s+tp),('a',r+sp)],s0)
            if res is None: continue
            H2[idx[res[0]],n]+=0.5*v*res[1]
def H1(h):
    M=np.zeros((N,N),complex)
    for n,s0 in enumerate(dets):
        for sp in (0,5):
            for p,q in itertools.product(range(5),repeat=2):
                if h[p,q]==0: continue
                res=apply([('c',p+sp),('a',q+sp)],s0)
                if res is None: continue
                M[idx[res[0]],n]+=h[p,q]*res[1]
    return M
# S2 = S-S+ at Ms=0
S2=np.zeros((N,N))
def Sp(s):
    out=[]
    for i in range(5):
        r=apply([('c',i),('a',i+5)],s)
        if r: out.append(r)
    return out
def Sm(s):
    out=[]
    for i in range(5):
        r=apply([('c',i+5),('a',i)],s)
        if r: out.append(r)
    return out
for n,s0 in enumerate(dets):
    for s1,x in Sp(s0):
        for s2,y in Sm(s1):
            S2[idx[s2],n]+=x*y
# rotation operators
l=2
Lz=np.diag(ms).astype(complex)
Lp=np.zeros((5,5),complex)
for i,m in enumerate(ms):
    if m<2: Lp[i+1,i]=np.sqrt(l*(l+1)-m*(m+1))
Lx=(Lp+Lp.T.conj())/2; Ly=(Lp-Lp.T.conj())/2j
def manyU(U):
    M=np.zeros((N,N),complex)
    for n,s0 in enumerate(dets):
        uo=[i for i in range(5) if s0>>i&1]; do=[i for i in range(5) if s0>>(5+i)&1]
        for m,s1 in enumerate(dets):
            ua=[i for i in range(5) if s1>>i&1]; da=[i for i in range(5) if s1>>(5+i)&1]
            M[m,n]=np.linalg.det(U[np.ix_(ua,uo)])*np.linalg.det(U[np.ix_(da,do)])
    return M
C4=manyU(expm(-1j*np.pi/2*Lz))
nv=np.array([1,1,0])/np.sqrt(2)
C2p=manyU(expm(-1j*np.pi*(nv[0]*Lx+nv[1]*Ly)))
w,Q=np.linalg.eigh(S2)
spaces={}
for S in (0,1,2):
    spaces[S]=Q[:,abs(w-S*(S+1))<1e-6]
print({k:v.shape[1] for k,v in spaces.items()})
res={}
for Dqb in np.arange(0,4.01,0.5):
    Dq=Dqb*B
    H=H2+H1(hmat(Dq))
    lev=[]
    for S,P in spaces.items():
        Hs=P.conj().T@H@P; Hs=(Hs+Hs.conj().T)/2
        e,v=np.linalg.eigh(Hs); v=P@v
        i=0
        while i<len(e):
            j=i
            while j+1<len(e) and abs(e[j+1]-e[i])<1e-6: j+=1
            sub=v[:,i:j+1]; d=j-i+1
            c4=np.trace(sub.conj().T@C4@sub).real; c2=np.trace(sub.conj().T@C2p@sub).real
            if d==1: ir='A1' if c2>0 else 'A2'
            elif d==2: ir='E'
            elif d==3: ir='T1' if c4>0 else 'T2'
            else: ir='?%d'%d
            lev.append((e[i],'%d%s'%(2*S+1,ir),d))
            i=j+1
    lev.sort()
    res[Dqb]=lev
    print(Dqb,[(t,round((e-lev[0][0])/B,3),d) for e,t,d in lev[:9]])
import pickle;pickle.dump(res,open('res.pkl','wb'))
E
python3 t.py