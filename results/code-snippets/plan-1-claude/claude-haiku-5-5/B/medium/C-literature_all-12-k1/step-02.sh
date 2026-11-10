mkdir -p /w && cat > /w/ts.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
# quadrature on sphere
xg,wg = np.polynomial.legendre.leggauss(20)
nphi=40
phis = np.arange(nphi)*2*np.pi/nphi; wphi = 2*np.pi/nphi
TH=[];PH=[];W=[]
for x,w in zip(xg,wg):
    for p in phis:
        TH.append(np.arccos(x)); PH.append(p); W.append(w*wphi)
TH=np.array(TH);PH=np.array(PH);W=np.array(W)
ms=[-2,-1,0,1,2]
def Y(l,m): return sph_harm_y(l,m,TH,PH)
Y2={m:Y(2,m) for m in ms}
def Yk(k,q): return Y(k,q)
# cubic field operator
X=np.sin(TH)*np.cos(PH); Yy=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
f = X**4+Yy**4+Z**4-0.6
Mf=np.array([[np.sum(W*np.conj(Y2[a])*f*Y2[b]) for b in ms] for a in ms])
ev=np.linalg.eigvalsh(Mf)
print("Mf eig",np.round(ev,4))
# scale so that t2g=-4, eg=+6 (difference 10)
lo,hi=ev[:3].mean(),ev[3:].mean()
scale=10/(hi-lo)
Hcf=Mf*scale
Hcf=Hcf - np.eye(5)*0  # barycentre already zero
print("cf eig", np.round(np.linalg.eigvalsh(Hcf),4))
# Coulomb angular factors
def ang(k,m1,m3,m2,m4):
    # <m1 m2|1/r12|m3 m4> angular, without F^k
    s=0
    for q in range(-k,k+1):
        A=np.sum(W*np.conj(Y2[m1])*Y2[m3]*np.conj(Yk(k,q)))
        B=np.sum(W*np.conj(Y2[m2])*Y2[m4]*Yk(k,q))
        s+=A*B
    return 4*np.pi/(2*k+1)*s
# precompute
Ang={}
for k in (0,2,4):
    arr=np.zeros((5,5,5,5),complex)
    for i1,m1 in enumerate(ms):
        for i3,m3 in enumerate(ms):
            for i2,m2 in enumerate(ms):
                for i4,m4 in enumerate(ms):
                    arr[i1,i3,i2,i4]=ang(k,m1,m3,m2,m4)
    Ang[k]=arr
# spin orbitals: idx = 2*i + s (s=0 up,1 down)
N=10
def spin_orb_V(k):
    V=np.zeros((N,N,N,N),complex)  # <ab|1/r|cd>
    for a in range(N):
        for b in range(N):
            for c in range(N):
                for d in range(N):
                    sa,sb,sc,sd=a%2,b%2,c%2,d%2
                    if sa!=sc or sb!=sd: continue
                    V[a,b,c,d]=Ang[k][a//2,c//2,b//2,d//2]
    return V
V2=spin_orb_V(2); V4=spin_orb_V(4); V0=spin_orb_V(0)
Vfull={'F0':V0,'F2':V2,'F4':V4}
# one-electron
h=np.zeros((N,N),complex)
for a in range(N):
    for b in range(N):
        if a%2==b%2: h[a,b]=Hcf[a//2,b//2]
# determinant basis
def dets(nup,ndn):
    out=[]
    for up in itertools.combinations(range(0,N,2),nup):
        for dn in itertools.combinations(range(1,N,2),ndn):
            out.append(tuple(sorted([2*i for i in up]+[2*i+1 for i in []]+[]))) if False else None
    return out
def occ_states(nel,sz2):
    # sz2 = 2*Ms ; n_up - n_dn = sz2
    res=[]
    for occ in itertools.combinations(range(N),nel):
        nu=sum(1 for o in occ if o%2==0); nd=nel-nu
        if nu-nd==sz2: res.append(occ)
    return res
def apply_ops(ops,state):
    # ops list of (type,idx) applied right-to-left order as given: first element applied last? we apply in order given
    # state: tuple sorted occupied; returns (sign,newstate) or None
    st=list(state); sign=1
    for typ,idx in ops:
        if typ=='a':   # annihilate
            if idx not in st: return None
            p=st.index(idx); sign*= (-1)**p; st.pop(p)
        else:          # create
            if idx in st: return None
            # insert in sorted position
            p=sum(1 for x in st if x<idx); sign*=(-1)**p; st.insert(p,idx)
    return sign,tuple(st)
def build(basis,Fk):
    # Fk: dict with F2,F4 coefficients; H = Dq-part h + sum_k F^k V^k (two-body)
    idx={s:i for i,s in enumerate(basis)}
    n=len(basis)
    Hcf_m=np.zeros((n,n),complex); Hee=np.zeros((n,n),complex)
    for j,s in enumerate(basis):
        # one-body
        for a in range(N):
            for b in range(N):
                if h[a,b]==0: continue
                r=apply_ops([('c',a),('a',b)],s)
                if r is None: continue
                sg,ns=r
                if ns in idx: Hcf_m[idx[ns],j]+=sg*h[a,b]
        # two-body: 1/2 sum V_abcd a+_a a+_b a_d a_c
        for a in range(N):
          for b in range(N):
            for c in range(N):
              for d in range(N):
                v=sum(Fk[k]*Vfull[k][a,b,c,d] for k in Fk if Fk[k]!=0)
                if v==0: continue
                r=apply_ops([('a',c),('a',d),('c',b),('c',a)],s)
                if r is None: continue
                sg,ns=r
                if ns in idx: Hee[idx[ns],j]+=0.5*sg*v
    return Hcf_m, Hee
EOF
cd /w && python3 -c "
import ts
print(ts.Hcf)
" 