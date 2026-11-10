import numpy as np, itertools
from scipy.special import sph_harm
from scipy.optimize import least_squares
# orbitals: complex d (m=-2..2), spin-orbitals index = 2*orb + s  (s=0 up,1 down)
ms=[-2,-1,0,1,2]
# quadrature
xg,wg=np.polynomial.legendre.leggauss(30)
nphi=60
phis=np.arange(nphi)*2*np.pi/nphi
TH,PH=np.meshgrid(np.arccos(xg),phis,indexing='ij')
W=np.outer(wg,np.ones(nphi))*(2*np.pi/nphi)
def Y(l,m,th,ph): return sph_harm(m,l,ph,th)  # scipy: sph_harm(m,n,azimuth,polar)
D=[Y(2,m,TH,PH) for m in ms]
X=np.sin(TH)*np.cos(PH); Yc=np.sin(TH)*np.sin(PH); Z=np.cos(TH)
Vang=X**4+Yc**4+Z**4-0.6
M=np.zeros((5,5),complex)
for a in range(5):
    for b in range(5):
        M[a,b]=np.sum(W*np.conj(D[a])*Vang*D[b])
ev=np.linalg.eigvalsh(M)
print("ligand eig raw",ev)
# eg = top two, t2g=bottom three
et,ee=ev[:3].mean(),ev[3:].mean()
# one-electron matrix h scaled so t2g=-4Dq, eg=+6Dq -> h = M*(10Dq/(ee-et))
h1=M/(ee-et)*10.0   # per unit Dq
# angular Slater-coefficient tensors for k=0,2,4
ANG={}
for k in [0,2,4]:
    G=np.zeros((5,5,5,5))  # G[a,c,b,d] = sum_q [∫ a* c Yk*q][∫ b* d Ykq] * 4pi/(2k+1)
    for q in range(-k,k+1):
        Ykq=Y(k,q,TH,PH)
        A=np.array([[np.sum(W*np.conj(D[a])*D[c]*np.conj(Ykq)) for c in range(5)] for a in range(5)])
        Bm=np.array([[np.sum(W*np.conj(D[b])*D[d]*Ykq) for d in range(5)] for b in range(5)])
        G+=np.einsum('ac,bd->acbd',A,Bm)
    ANG[k]=G*4*np.pi/(2*k+1)
# Build Fock basis: 3-electron determinants of 10 spin-orbitals
so=lambda o,s: 2*o+s
states=list(itertools.combinations(range(10),3))
idx={s:i for i,s in enumerate(states)}
def apply_ops(ops,st):
    # ops: list of ('c'|'a', index) applied right-to-left as in list order reversed; returns (sign,newstate) or None
    occ=list(st); sign=1
    for typ,i in reversed(ops):
        if typ=='a':   # annihilate
            if i not in occ: return None
            p=occ.index(i); sign*=(-1)**p; occ.pop(p)
        else:
            if i in occ: return None
            # insert in sorted position
            p=sum(1 for x in occ if x<i); sign*=(-1)**p; occ.insert(p,i)
    return sign,tuple(sorted(occ))
def build(Dq,B,C):
    F4=63*C/5.0
    F2=49*B+5*F4/9.0
    Fk={0:0.0,2:F2,4:F4}
    n=len(states)
    H=np.zeros((n,n),complex)
    # one-electron: sum_ab h_ab sum_s a†_{a s} a_{b s}
    # two-electron: 1/2 sum <ab|V|cd> a†_a a†_b a_d a_c
    # <ab|V|cd> = sum_k F^k * G^k[a,c,b,d]  (G indexed [a,c,b,d])
    for j,st in enumerate(states):
        for s1 in range(2):
            for a in range(5):
                for b in range(5):
                    if abs(h1[a,b]) < 1e-14 and True: pass
                    pass
        # one-body
        for a in range(5):
            for b in range(5):
                hab=h1[a,b]*Dq
                if abs(hab)<1e-14: continue
                for s in range(2):
                    r=apply_ops([('c',so(a,s)),('a',so(b,s))],st)
                    if r is None: continue
                    sg,ns=r; H[idx[ns],j]+=sg*hab
        # two-body
        for a in range(10):
            for b in range(10):
                if a==b: continue
                for c in range(10):
                    for d in range(10):
                        if c==d: continue
                        oa,sa=divmod(a,2); ob,sb=divmod(b,2); oc,sc=divmod(c,2); od,sd=divmod(d,2)
                        if sa!=sc or sb!=sd: continue
                        v=sum(Fk[k]*ANG[k][oa,oc,ob,od] for k in (2,4))
                        if abs(v)<1e-14: continue
                        r=apply_ops([('c',a),('c',b),('a',d),('a',c)],st)
                        if r is None: continue
                        sg,ns=r; H[idx[ns],j]+=0.5*sg*v
    return H
# spin sectors: Ms via occupancy count of up(even idx) minus down
def Ms2(st):
    up=sum(1 for x in st if x%2==0); dn=3-up
    return up-dn
def energies(Dq,B,C):
    H=build(Dq,B,C)
    H=np.real_if_close(H)
    ms3=[i for i,s in enumerate(states) if all(x%2==0 for x in s)]
    Hq=H[np.ix_(ms3,ms3)]
    quart=np.sort(np.linalg.eigvalsh(Hq))
    ms1=[i for i,s in enumerate(states) if Ms2(s)==1]
    H1=H[np.ix_(ms1,ms1)]
    all1=np.sort(np.linalg.eigvalsh(H1))
    # remove quartet Ms=1/2 eigenvalues: quartet states with Ms=1/2 have same energies as quartet terms
    # remove each quartet energy once
    dbl=list(all1)
    for qe in quart:
        # find nearest
        k=int(np.argmin([abs(x-qe) for x in dbl])); dbl.pop(k)
    return quart, np.array(sorted(dbl))
if __name__=="__main__":
    q,d=energies(1000.0,500.0,2000.0)
    print("quartets",q)
    print("doublets",d)
