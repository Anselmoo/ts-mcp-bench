mkdir -p /tmp/w && cd /tmp/w && cat > d6.py <<'EOF'
import numpy as np, itertools
from sympy.physics.wigner import wigner_3j
from functools import lru_cache
l=2
ms=list(range(-2,3))
def orb(m,s): return 2*(m+2)+s
@lru_cache(None)
def w3(a,b,c,d,e,f): return float(wigner_3j(a,b,c,d,e,f))
def ck(m,k,q,mp):
    if m!=mp+q: return 0.0
    return (-1)**(l-m)*w3(l,k,l,-m,q,mp)*(-1)**l*(2*l+1)*w3(l,k,l,0,0,0)
def Vint(a,b,c,d,F):
    tot=0.0
    for k in (0,2,4):
        s=sum((-1)**q*ck(a,k,-q,c)*ck(b,k,q,d) for q in range(-k,k+1))
        tot+=F[k]*s
    return tot
def build(B,C,Dq):
    F4=441*C/35; F2=(441*B+5*F4)/9; F={0:0.0,2:F2,4:F4}
    z=np.zeros(5); z[ms.index(0)]=1
    x=np.zeros(5); x[ms.index(2)]=1/np.sqrt(2); x[ms.index(-2)]=1/np.sqrt(2)
    Peg=np.outer(z,z)+np.outer(x,x)
    M=Dq*(-4*np.eye(5)+10*Peg)
    h=np.zeros((10,10))
    for i,m1 in enumerate(ms):
        for j,m2 in enumerate(ms):
            for s in (0,1): h[orb(m1,s),orb(m2,s)]=M[i,j]
    V=np.zeros((10,10,10,10))
    for a,b,c,d in itertools.product(range(10),repeat=4):
        ma,sa=divmod(a,2); mb,sb=divmod(b,2); mc,sc=divmod(c,2); md,sd=divmod(d,2)
        if sa!=sc or sb!=sd: continue
        V[a,b,c,d]=Vint(ma-2,mb-2,mc-2,md-2,F)
    return h,V
def cc(state,p,q):  # a+_p a_q
    if not (state>>q)&1: return None,0
    sg=(-1)**bin(state&((1<<q)-1)).count('1'); st=state^(1<<q)
    if (st>>p)&1: return None,0
    sg*=(-1)**bin(st&((1<<p)-1)).count('1')
    return st|(1<<p),sg
def basis6(): return [sum(1<<i for i in c) for c in itertools.combinations(range(10),6)]
def ops(h,V):
    basis=basis6(); idx={s:i for i,s in enumerate(basis)}; n=len(basis)
    H=np.zeros((n,n))
    for j,s in enumerate(basis):
        for p in range(10):
            for q in range(10):
                if h[p,q]==0: continue
                t,sg=cc(s,p,q)
                if t is not None: H[idx[t],j]+=sg*h[p,q]
        # 1/2 sum V_abcd a+a a+b a_d a_c
        for c in range(10):
            for d in range(10):
                if c==d: continue
                t1,g1=cc(s,c,c) if False else (None,0)
                if not (s>>d)&1: continue
                s1=s^(1<<d); g1=(-1)**bin(s&((1<<d)-1)).count('1')
                if not (s1>>c)&1: continue
                s2=s1^(1<<c); g2=(-1)**bin(s1&((1<<c)-1)).count('1')
                for a in range(10):
                    for b in range(10):
                        v=V[a,b,c,d]
                        if v==0 or a==b: continue
                        # a+_b first then a+_a: operator a+_a a+_b  on s2
                        if (s2>>b)&1: continue
                        s3=s2|(1<<b); g3=(-1)**bin(s2&((1<<b)-1)).count('1')
                        if (s3>>a)&1: continue
                        s4=s3|(1<<a); g4=(-1)**bin(s3&((1<<a)-1)).count('1')
                        H[idx[s4],j]+=0.5*v*g1*g2*g3*g4
    # S^2
    Sp=np.zeros((n,n)); Sz=np.zeros(n)
    for j,s in enumerate(basis):
        Sz[j]=0.5*sum(((s>>orb(m,0))&1)-((s>>orb(m,1))&1) for m in ms)
        for m in ms:
            t,sg=cc(s,orb(m,0),orb(m,1))
            if t is not None: Sp[idx[t],j]+=sg
    S2=Sp.T@Sp+np.diag(Sz*(Sz+1))
    return basis,H,S2
if __name__=="__main__":
    import sys
    h,V=build(1.0,4.5,0.0)
    basis,H0,S2=ops(h,V)
    print(np.allclose(H0,H0.T))
EOF
python3 d6.py