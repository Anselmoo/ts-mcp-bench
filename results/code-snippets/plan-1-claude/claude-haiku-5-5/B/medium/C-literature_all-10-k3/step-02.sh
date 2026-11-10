mkdir -p /w && cat > /w/ts.py << 'EOF'
import numpy as np, itertools
from sympy.physics.wigner import gaunt
from sympy import N as sN
from scipy.optimize import fsolve
# spin-orbitals: index = 2*(m+2)+s, s=0 up,1 down
orbs=[(m,s) for m in range(-2,3) for s in (0,1)]
nso=10
dets=[sum(1<<i for i in c) for c in itertools.combinations(range(nso),6)]
idx={d:i for i,d in enumerate(dets)}
D=len(dets)
def apply_ops(ops,state):
    # ops: list of (type,i): type 'c' creation or 'a' annihilation, applied right-to-left
    s=state; sign=1
    for t,i in ops:
        if t=='a':
            if not (s>>i)&1: return None,0
            sign*= (-1)**bin(s&((1<<i)-1)).count('1'); s^=(1<<i)
        else:
            if (s>>i)&1: return None,0
            sign*= (-1)**bin(s&((1<<i)-1)).count('1'); s|=(1<<i)
    return s,sign
# Gaunt-based angular coefficients A_k(a,c,q)=∫conj(Y_a) Y_kq Y_c
def A(k,a,c,q):
    if -a+q+c!=0: return 0.0
    if abs(q)>k: return 0.0
    return float(((-1)**(a%2))*sN(gaunt(2,k,2,-a,q,c)))
def Vang(k,ma,mc,mb,md):
    # <ma mb|C^k.C^k|mc md> part : sum_q (-1)^q A_k(ma,mc,q) A_k(mb,md,-q)
    tot=0.0
    for q in range(-k,k+1):
        tot+= (-1)**(q%2)*A(k,ma,mc,q)*A(k,mb,md,-q)
    return tot*4*np.pi/(2*k+1)
ks={2:None,4:None}
# build two-body matrices M_k for F^k with F0 omitted
def twobody(k):
    M=np.zeros((D,D))
    # H = 1/2 sum V_ijkl a+_i a+_j a_l a_k, V_ijkl=<ij|1/r|kl>
    cache={}
    for ci,(ma,sa) in enumerate(orbs):
        for cj,(mb,sb) in enumerate(orbs):
            for ck,(mc,sc) in enumerate(orbs):
                for cl,(md,sd) in enumerate(orbs):
                    if sa!=sc or sb!=sd: continue
                    v=Vang(k,ma,mc,mb,md)
                    if abs(v)<1e-14: continue
                    for di,st in enumerate(dets):
                        r,sg=apply_ops([('a',ck),('a',cl)],st) if False else (None,0)
                        # ops applied: a_k first then a_l, then a+_j, a+_i  (H ~ a+_i a+_j a_l a_k)
                        s1,g1=apply_ops([('a',ck)],st)
                        if s1 is None: continue
                        s2,g2=apply_ops([('a',cl)],s1)
                        if s2 is None: continue
                        s3,g3=apply_ops([('c',cj)],s2)
                        if s3 is None: continue
                        s4,g4=apply_ops([('c',ci)],s3)
                        if s4 is None: continue
                        M[idx[s4],di]+=0.5*v*g1*g2*g3*g4
    return M
# one-body: h = -4 I + 10 P_eg (Dq factor); P_eg in complex basis: m=0 and cos2phi combo
P=np.zeros((5,5),complex)  # index m+2
P[2,2]=1
# cos2phi real orbital (x2-y2)/... = (Y22+Y2-2)/sqrt2 up to sign convention
v=np.zeros(5,complex); v[4]=1/np.sqrt(2); v[0]=1/np.sqrt(2)
P+=np.outer(v,v.conj())
def onebody(h):
    M=np.zeros((D,D),complex)
    for i,(ma,sa) in enumerate(orbs):
        for j,(mb,sb) in enumerate(orbs):
            if sa!=sb or abs(h[ma+2,mb+2])<1e-14: continue
            for di,st in enumerate(dets):
                s1,g1=apply_ops([('a',j)],st)
                if s1 is None: continue
                s2,g2=apply_ops([('c',i)],s1)
                if s2 is None: continue
                M[idx[s2],di]+=h[ma+2,mb+2]*g1*g2
    return M
Hcf_eg=onebody(10*P)
Hcf_0=onebody(-4*np.eye(5))
# S^2 matrix
def spin_ops():
    Sp=np.zeros((D,D)); Sm=np.zeros((D,D)); Sz=np.zeros((D,D))
    for m in range(-2,3):
        iu=orbs.index((m,0)); idn=orbs.index((m,1))
        for di,st in enumerate(dets):
            s1,g1=apply_ops([('a',idn)],st)
            if s1 is not None:
                s2,g2=apply_ops([('c',iu)],s1)
                if s2 is not None: Sp[idx[s2],di]+=g1*g2
            s1,g1=apply_ops([('a',iu)],st)
            if s1 is not None:
                s2,g2=apply_ops([('c',idn)],s1)
                if s2 is not None: Sm[idx[s2],di]+=g1*g2
    Sz=np.diag([0.5*sum(1 if (st>>orbs.index((m,0)))&1 else 0 for m in range(-2,3)) -0.5*sum(1 if (st>>orbs.index((m,1)))&1 else 0 for m in range(-2,3)) for st in dets])
    return Sp,Sm,Sz
Sp,Sm,Sz=spin_ops()
S2=Sm@Sp+Sz@Sz+Sz
M2=twobody(2); M4=twobody(4)
np.savez('/w/mats.npz',M2=M2,M4=M4,Hcf_eg=Hcf_eg,Hcf_0=Hcf_0,S2=S2)
print("built", D)
EOF
cd /w && time python3 ts.py