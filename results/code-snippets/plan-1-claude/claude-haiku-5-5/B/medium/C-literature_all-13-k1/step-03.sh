mkdir -p /tmp/w && cd /tmp/w && cat > d7.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N as sN
from functools import lru_cache
from math import pi

NSO=10
@lru_cache(None)
def gnt(l1,m1,l2,m2,l3,m3):
    if m1+m2+m3!=0: return 0.0
    return float(sN(gaunt(l1,l2,l3,m1,m2,m3),15))

def ang(k,mi,mj,mk,ml):
    tot=0.0
    for q in range(-k,k+1):
        X1=(-1)**(mi+q)*gnt(2,-mi,k,-q,2,mk)
        X2=(-1)**mj*gnt(2,-mj,k,q,2,ml)
        tot+=X1*X2
    return tot*4*pi/(2*k+1)

def build(Dq,B,C):
    F={2:441*B+63*C,4:441*C/35.0}
    idx=lambda m: m+2
    h=np.zeros((5,5))
    # P_eg = |0><0| + (|2>+|-2>)(<2|+<-2|)/2
    h[idx(0),idx(0)]+=1
    for a in (2,-2):
        for b in (2,-2):
            h[idx(a),idx(b)]+=0.5
    h*=10*Dq
    H1=np.zeros((NSO,NSO))
    for m1 in range(-2,3):
        for m2 in range(-2,3):
            for s in (0,1):
                H1[2*(m1+2)+s,2*(m2+2)+s]=h[idx(m1),idx(m2)]
    V=np.zeros((NSO,NSO,NSO,NSO))
    for i in range(NSO):
        for j in range(NSO):
            for k in range(NSO):
                for l in range(NSO):
                    if i%2!=k%2 or j%2!=l%2: continue
                    mi,mj,mk,ml=i//2-2,j//2-2,k//2-2,l//2-2
                    V[i,j,k,l]=sum(F[kk]*ang(kk,mi,mj,mk,ml) for kk in (2,4))
    basis=[sum(1<<i for i in c) for c in itertools.combinations(range(NSO),7)]
    index={b:n for n,b in enumerate(basis)}
    D=len(basis)
    def ann(x,st):
        if not (st>>x)&1: return None,0
        return st^(1<<x), (-1)**bin(st&((1<<x)-1)).count('1')
    def cre(x,st):
        if (st>>x)&1: return None,0
        return st|(1<<x), (-1)**bin(st&((1<<x)-1)).count('1')
    H=np.zeros((D,D))
    for n,b in enumerate(basis):
        for a in range(NSO):
            for c in range(NSO):
                if H1[a,c]==0: continue
                st,s1=ann(c,b)
                if st is None: continue
                st,s2=cre(a,st)
                if st is None: continue
                H[index[st],n]+=H1[a,c]*s1*s2
        # (1/2) sum V_ijkl c†_i c†_j c_l c_k
        for i in range(NSO):
            for j in range(NSO):
                for k in range(NSO):
                    for l in range(NSO):
                        v=V[i,j,k,l]
                        if v==0 or i==j or k==l: continue
                        st,s1=ann(k,b)
                        if st is None: continue
                        st,s2=ann(l,st)
                        if st is None: continue
                        st,s3=cre(j,st)
                        if st is None: continue
                        st,s4=cre(i,st)
                        if st is None: continue
                        H[index[st],n]+=0.5*v*s1*s2*s3*s4
    Sz=np.zeros((D,D)); Sp=np.zeros((D,D))
    for n,b in enumerate(basis):
        nu=sum((b>>(2*m))&1 for m in range(5)); nd=sum((b>>(2*m+1))&1 for m in range(5))
        Sz[n,n]=0.5*(nu-nd)
        for m in range(5):
            st,s1=ann(2*m+1,b)
            if st is None: continue
            st,s2=cre(2*m,st)
            if st is None: continue
            Sp[index[st],n]+=s1*s2
    S2=Sp.T@Sp+Sz@Sz+Sz
    return H,S2

def levels(Dq,B,C):
    H,S2=build(Dq,B,C)
    w,v=np.linalg.eigh(H+1e5*S2)
    out=[]
    for vec in v.T:
        s2=vec@S2@vec
        S=(-1+np.sqrt(1+4*s2))/2
        out.append((vec@H@vec, round(2*S)/2))
    out.sort()
    return out
if __name__=="__main__":
    lv=levels(0,0,0)
    print(set(round(e,6) for e,_ in lv))
    lv=levels(1000,800,3200)
    gs=lv[0][0]
    for e,S in lv: print(round(e-gs,1),S)
EOF
time python3 d7.py