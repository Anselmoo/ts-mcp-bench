python3 - <<'EOF'
import numpy as np, time
from scipy.special import lpmv, factorial
from scipy.optimize import least_squares
xg,wg=np.polynomial.legendre.leggauss(30)
phis=np.linspace(0,2*np.pi,60,endpoint=False); wp=2*np.pi/60
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij'); W=(wg[:,None]*wp*np.ones_like(TH))
def Y(l,m,th,ph):
    am=abs(m); N=np.sqrt((2*l+1)/(4*np.pi)*factorial(l-am)/factorial(l+am))
    y=N*lpmv(am,l,np.cos(th))*np.exp(1j*am*ph)
    if m<0: y=(-1)**am*np.conj(y)
    return y
ms=[-2,-1,0,1,2]
Yd={m:Y(2,m,TH,PH) for m in ms}
Ang={}
for k in (0,2,4):
    for a in ms:
        for c in ms:
            for q in range(-k,k+1):
                Ang[(a,c,k,q)]=np.sum(W*np.conj(Yd[a])*Yd[c]*np.conj(Y(k,q,TH,PH)))
def Vspat(a,b,c,d,F):
    tot=0
    for k in (0,2,4):
        s=sum(Ang[(a,c,k,q)]*Ang[(b,d,k,-q)]*(-1)**q for q in range(-k,k+1))
        tot+=F[k]*4*np.pi/(2*k+1)*s
    return tot
so=[(m,s) for m in ms for s in (0,1)]
states=[x for x in range(1024) if bin(x).count('1')==8]
idx={x:i for i,x in enumerate(states)}; D=len(states)
def op(ops):
    # ops: list of (type,i) applied right-to-left: product c+/c; generic apply to basis
    M=np.zeros((D,D))
    for x in states:
        y=x; s=1; ok=True
        for typ,i in reversed(ops):
            n_before=bin(y&((1<<i)-1)).count('1')
            if typ=='c':
                if not (y>>i)&1: ok=False;break
                y^=(1<<i); s*=(-1)**n_before
            else:
                if (y>>i)&1: ok=False;break
                y|=(1<<i); s*=(-1)**n_before
        if ok and y in idx: M[idx[y],idx[x]]+=s
    return M
def spectrum(Dq,B,C):
    F={0:0.0,2:49*B+7*C,4:441*C/35}
    s2=np.sqrt(2)
    def vec(d):
        v=np.zeros(5,complex)
        for m,c in d.items(): v[m+2]=c
        return v
    eg=[vec({0:1}),vec({2:1/s2,-2:1/s2})]
    t2=[vec({1:-1/s2,-1:1/s2}),vec({1:-1j/s2,-1:-1j/s2}),vec({2:-1j/s2,-2:1j/s2})]
    P=sum(6*Dq*np.outer(v,v.conj()) for v in eg)+sum(-4*Dq*np.outer(v,v.conj()) for v in t2)
    H=np.zeros((D,D),complex)
    for i,(m1,s1) in enumerate(so):
        for j,(m2,s_2) in enumerate(so):
            if s1==s_2 and abs(P[m1+2,m2+2])>1e-14:
                H+=P[m1+2,m2+2]*op([('c',i),('a',j)])
    for a in range(10):
        for b in range(10):
            for c in range(10):
                for d in range(10):
                    ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
                    if sa!=sc or sb!=sd or a==b or c==d: continue
                    v=Vspat(ma,mb,mc,md,F)
                    if abs(v)<1e-12: continue
                    H+=0.5*v*op([('a',a),('a',b),('c',d),('c',c)])
    # S^2
    Sp=sum(op([('a',2*m),('c',2*m+1)]) for m in range(5))
    Sz=sum(0.5*(op([('a',2*m),('c',2*m)])-op([('a',2*m+1),('c',2*m+1)])) for m in range(5))
    S2=Sp.T@Sp+Sz@Sz+Sz
    return H,S2
t=time.time()
H,S2=spectrum(0.0,1000,4000)
print("build",time.time()-t, np.allclose(H,H.conj().T))
# free-ion check
w=np.linalg.eigvalsh(H)
print(np.round(np.unique(np.round(w,3)),1)[:30])
EOF