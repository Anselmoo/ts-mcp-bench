python3 - << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y
from scipy.optimize import least_squares
xg, wg = np.polynomial.legendre.leggauss(16)
nphi = 32
phis = np.arange(nphi)*2*np.pi/nphi
ct, ph = np.meshgrid(xg, phis, indexing='ij')
W = np.outer(wg, np.ones(nphi))*(2*np.pi/nphi)
th = np.arccos(ct)
def Y(l,m): return sph_harm_y(l, m, th, ph)
ms = [-2,-1,0,1,2]
Yd = {m: Y(2,m) for m in ms}
def integ(f): return np.sum(W*f)
x = np.sin(th)*np.cos(ph); y=np.sin(th)*np.sin(ph); z=np.cos(th)
f = x**4+y**4+z**4-0.6
Mf = np.array([[integ(np.conj(Yd[a])*f*Yd[b]) for b in ms] for a in ms]).real
ev = np.linalg.eigvalsh(Mf)
a = ev[:3].mean(); b = ev[3:].mean()
alpha = 10.0/(b-a); beta = -4 - alpha*a
Mcf = alpha*Mf + beta*np.eye(5)
T = {}
for k in [0,2,4]:
    for q in range(-k,k+1):
        Ykq = Y(k,q)
        Ta = np.array([[integ(np.conj(Yd[a_])*np.conj(Ykq)*Yd[c]) for c in ms] for a_ in ms])
        Tb = np.array([[integ(np.conj(Yd[b_])*Ykq*Yd[d]) for d in ms] for b_ in ms])
        T[(k,q)] = (Ta,Tb)
def Vang(k):
    V = np.zeros((5,5,5,5),dtype=complex)
    for q in range(-k,k+1):
        Ta,Tb = T[(k,q)]
        V += np.einsum('ac,bd->abcd', Ta, Tb)
    return (V*4*np.pi/(2*k+1)).real
V0,V2,V4 = Vang(0),Vang(2),Vang(4)
norb=10; ne=7
states = [sum(1<<i for i in c) for c in itertools.combinations(range(norb), ne)]
idx = {s:i for i,s in enumerate(states)}
N=len(states)
def sgn(st, j): return (-1)**bin(st & ((1<<j)-1)).count('1')
def cre_ann(p,q,st):
    if not (st>>q)&1: return None
    s = st & ~(1<<q); sg = sgn(st,q)
    if (s>>p)&1: return None
    return sg*sgn(s,p), s|(1<<p)
def build_two(Fk):
    Vtot = Fk[0]*V0+Fk[2]*V2+Fk[4]*V4
    H=np.zeros((N,N))
    for i,st in enumerate(states):
        occ=[j for j in range(norb) if (st>>j)&1]
        for c_ in occ:
            for d_ in occ:
                if c_==d_: continue
                oc,sc=c_//2,c_%2; od,sd=d_//2,d_%2
                s1 = st & ~(1<<c_); sg1 = sgn(st,c_)
                s2 = s1 & ~(1<<d_); sg2 = sgn(s1,d_)
                for a_ in range(norb):
                    for b_ in range(norb):
                        if a_==b_: continue
                        oa,sa=a_//2,a_%2; ob,sb=b_//2,b_%2
                        if sa!=sc or sb!=sd: continue
                        v=Vtot[oa,ob,oc,od]
                        if abs(v)<1e-14: continue
                        if (s2>>b_)&1 or (s2>>a_)&1: continue
                        s3=s2|(1<<b_); sg3=sgn(s2,b_)
                        s4=s3|(1<<a_); sg4=sgn(s3,a_)
                        H[idx[s4],i]+=0.5*v*sg1*sg2*sg3*sg4
    return H
def build_cf():
    H=np.zeros((N,N))
    for i,st in enumerate(states):
        for p in range(norb):
            for q in range(norb):
                if p%2!=q%2: continue
                v=Mcf[p//2,q//2]
                if abs(v)<1e-14: continue
                r=cre_ann(p,q,st)
                if r is None: continue
                H[idx[r[1]],i]+=v*r[0]
    return H
Sz=np.zeros((N,N)); Sp=np.zeros((N,N))
for i,st in enumerate(states):
    for m in range(5):
        pu=2*m; pd=2*m+1
        Sz[i,i]+=0.5*(((st>>pu)&1)-((st>>pd)&1))
        r=cre_ann(pu,pd,st)
        if r is not None: Sp[idx[r[1]],i]+=r[0]
S2 = Sp.T@Sp + Sz@Sz + Sz
Hcf = build_cf()
w,V = np.linalg.eigh(S2)
Vq = V[:, np.abs(w-15/4)<1e-6]
# Build fixed operators: H = B*H_B + Dq*Hcf, with H_B = build_two at B=1 (F2,F4 from ratio 0.625)
ratio=0.625
def FB(B): 
    F2=B*441/(9-5*ratio); return {0:0.0,2:F2,4:ratio*F2}
HB = build_two(FB(1.0))
Hq_B = Vq.T@HB@Vq; Hq_cf = Vq.T@Hcf@Vq
def levels(Dq,B):
    lev = np.linalg.eigvalsh(B*Hq_B + Dq*Hq_cf)
    # cluster
    out=[]; 
    for e in lev:
        if not out or abs(e-out[-1][0])>1e-6: out.append([e,1])
        else: out[-1][1]+=1
    return out
# test
print(levels(1000,1000))
obs = np.array([8620.,18410.,20250.])
def resid(p):
    Dq,B = p
    lv = levels(Dq,B)
    # ground = lowest level (4T1g F); find levels
    e0 = lv[0][0]
    # all distinct levels
    E = [l[0]-e0 for l in lv]
    # candidate transitions: all levels above ground; pick 3 nearest to obs? use spin-allowed quartet-quartet set
    return E
# Pick assignment: T2g(F) = level with mult 12 and nonzero; A2g = mult 4; T1g(P)= mult 12 highest among quartets
def assign(Dq,B):
    lv = levels(Dq,B)
    e0=lv[0][0]
    return [(round(l[0]-e0,1),l[1]) for l in lv]
print(assign(1000,1000))
EOF