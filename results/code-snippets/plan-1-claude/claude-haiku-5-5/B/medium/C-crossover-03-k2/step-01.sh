
cat << 'EOF' > /tmp/d6.py
import numpy as np, itertools
from scipy.optimize import brentq
from scipy.special import sph_harm
B,C=803.0,3078.0
F4=441*C/35.0; F2=(441*B+5*F4)/9.0; F0=0.0  # F0 drops out of energy differences (constant)
Fk={0:F0,2:F2,4:F4}
# quadrature on sphere
nth,nph=60,120
x,w=np.polynomial.legendre.leggauss(nth)
th=np.arccos(x); ph=np.arange(nph)*2*np.pi/nph
TH,PH=np.meshgrid(th,ph,indexing='ij'); W=np.outer(w,np.ones(nph))*(2*np.pi/nph)
def Y(l,m): return sph_harm(m,l,PH,TH)  # scipy: sph_harm(m,n,azimuth,polar)
ms=range(-2,3)
Yd={m:Y(2,m) for m in ms}
def ang(k,q,m1,m3):  # \int Y*_{m1} Y*_{kq} Y_{m3}
    return np.sum(W*np.conj(Yd[m1])*np.conj(Y(k,q))*Yd[m3])
# spatial two-electron integrals V[m1,m2,m3,m4] = sum_k F^k 4pi/(2k+1) sum_q ang(m1,m3,q) ang(m2,m4,q)'
# second point uses Y_{kq}: \int Y*_{m2} Y_{kq} Y_{m4}
def ang2(k,q,m2,m4):
    return np.sum(W*np.conj(Yd[m2])*Y(k,q)*Yd[m4])
Vsp={}
for m1,m2,m3,m4 in itertools.product(ms,repeat=4):
    tot=0
    for k in (0,2,4):
        s=0
        for q in range(-k,k+1):
            s+=ang(k,q,m1,m3)*ang2(k,q,m2,m4)
        tot+=Fk[k]*4*np.pi/(2*k+1)*s
    Vsp[(m1,m2,m3,m4)]=tot
# spin-orbitals: index (m,s) s=+1/2 -> 0, -1/2 -> 1
so=[(m,s) for m in ms for s in (0,1)]
N=10
def V(a,b,c,d):
    ma,sa=so[a]; mb,sb=so[b]; mc,sc=so[c]; md,sd=so[d]
    if sa!=sc or sb!=sd: return 0.0
    return Vsp[(ma,mb,mc,md)].real
# one-electron matrix in complex basis for cubic CF
# real orbitals in complex basis (columns = real orbitals), index by m
def vec(d): 
    v=np.zeros(5,complex)
    for m,c in d.items(): v[m+2]=c
    return v
s2=1/np.sqrt(2)
orbs={
 'xy': vec({2:1j*s2,-2:-1j*s2}),
 'yz': vec({1:1j*s2,-1:1j*s2}),
 'xz': vec({1:-s2,-1:s2}),
 'x2y2': vec({2:s2,-2:s2}),
 'z2': vec({0:1.0}),
}
energy={'xy':-4,'yz':-4,'xz':-4,'x2y2':6,'z2':6}  # units of Dq
def h1(Dq):
    h=np.zeros((5,5),complex)
    for n,v in orbs.items():
        h+=energy[n]*Dq*np.outer(v,np.conj(v))
    return h
# determinant basis: 6 electrons among 10 spin orbitals
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(N),6)]
idx={d:i for i,d in enumerate(dets)}
def apply_cdag_c(p,q,state):  # c_p^dag c_q
    # returns (sign, newstate) or None
    if not (state>>q)&1: return None
    sg=(-1)**bin(state & ((1<<q)-1)).count('1')
    st=state ^ (1<<q)
    if (st>>p)&1: return None
    sg*=(-1)**bin(st & ((1<<p)-1)).count('1')
    return sg, st|(1<<p)
def build(Dq):
    H1=h1(Dq)
    D=len(dets); H=np.zeros((D,D))
    # one-electron: sum_{ab} h_ab c_a^dag c_b, h in complex basis; spin diag
    hso=np.zeros((N,N),complex)
    for i,(m,s) in enumerate(so):
        for j,(mp,sp) in enumerate(so):
            if s==sp: hso[i,j]=H1[m+2,mp+2]
    # two-electron: 1/2 sum V_abcd c_a^dag c_b^dag c_d c_c
    Vt=np.zeros((N,N,N,N))
    for a,b,c,d in itertools.product(range(N),repeat=4):
        Vt[a,b,c,d]=V(a,b,c,d)
    for col,st in enumerate(dets):
        # one-body
        for p in range(N):
            for q in range(N):
                if abs(hso[p,q])<1e-14: continue
                r=apply_cdag_c(p,q,st)
                if r is None: continue
                sg,ns=r
                H[idx[ns],col]+=sg*hso[p,q].real
        # two-body
        for c in range(N):
            for d in range(N):
                if not (st>>d)&1: continue
                # c_d then c_c: annihilate d then c
                s1=(-1)**bin(st & ((1<<d)-1)).count('1'); t=st^(1<<d)
                if not (t>>c)&1: continue
                s2_=(-1)**bin(t & ((1<<c)-1)).count('1'); t2=t^(1<<c)
                for a in range(N):
                    for b in range(N):
                        if Vt[a,b,c,d]==0: continue
                        if (t2>>b)&1: continue
                        r1=apply_cdag_c(b,0,0) # placeholder
                        # c_a^dag c_b^dag applied to t2: first c_b^dag then c_a^dag
                        if (t2>>b)&1: continue
                        sb=(-1)**bin(t2 & ((1<<b)-1)).count('1'); t3=t2|(1<<b)
                        if (t3>>a)&1: continue
                        sa=(-1)**bin(t3 & ((1<<a)-1)).count('1'); t4=t3|(1<<a)
                        H[idx[t4],col]+=0.5*Vt[a,b,c,d]*s1*s2_*sb*sa
    return H
def S2_and_E(Dq):
    H=build(Dq)
    # S+ and Sz
    D=len(dets)
    Sp=np.zeros((D,D)); Sz=np.zeros(D)
    for col,st in enumerate(dets):
        n_up=sum(1 for i in range(N) if (st>>i)&1 and so[i][1]==0)
        n_dn=sum(1 for i in range(N) if (st>>i)&1 and so[i][1]==1)
        Sz[col]=0.5*(n_up-n_dn)
        for m in ms:
            up=2*(m+2); dn=2*(m+2)+1
            if (st>>dn)&1 and not (st>>up)&1:
                r=apply_cdag_c(up,dn,st)
                sg,ns=r
                Sp[idx[ns],col]+=sg
    S2=Sp.T@Sp+np.diag(Sz*(Sz+1))
    return H,S2,Sz
H,S2,Sz=S2_and_E(0.0)
print("check Hermitian", np.allclose(H,H.T))
def lowest(Dq):
    H,S2,Sz=S2_and_E(Dq)
    # sector-wise
    res={}
    for S in (0,2):
        # project onto S2 eigenspace
        ev,evec=np.linalg.eigh(S2)
        P=evec[:,np.abs(ev-S*(S+1))<1e-6]
        Hs=P.T@H@P
        res[S]=np.linalg.eigvalsh(Hs)[0]
    return res
for Dq in [0,1000,2000,2500,3000]:
    print(Dq,lowest(Dq))
EOF
python3 /tmp/d6.py
