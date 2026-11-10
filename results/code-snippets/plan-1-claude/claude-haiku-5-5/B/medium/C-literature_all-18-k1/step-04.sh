mkdir -p /w && cat > /w/ts.py << 'EOF'
import numpy as np, itertools
from scipy.special import sph_harm_y, eval_legendre
from scipy.optimize import least_squares

# angular grid
nt, nphi = 30, 60
x, wx = np.polynomial.legendre.leggauss(nt)
th = np.arccos(x); ph = np.arange(nphi)*2*np.pi/nphi
TH, PH = np.meshgrid(th, ph, indexing='ij'); W = (np.repeat(wx[:,None],nphi,1))*(2*np.pi/nphi)
ms = [-2,-1,0,1,2]
def Y(l,m,T,P): return sph_harm_y(l,m,T,P)  # scipy: degree l, order m, theta polar, phi azimuth
Ylm = {m: Y(2,m,TH,PH) for m in ms}
# unit vectors
dirs = np.array([[0,0,1],[0,0,-1],[1,0,0],[-1,0,0],[0,1,0],[0,-1,0]],float)
rx = np.sin(TH)*np.cos(PH); ry=np.sin(TH)*np.sin(PH); rz=np.cos(TH)
V0 = np.zeros_like(TH)
for d in dirs:
    V0 += eval_legendre(4, rx*d[0]+ry*d[1]+rz*d[2])
def integ(f): return np.sum(W*f)
# one-electron matrix shape
h1 = np.zeros((5,5),complex)
for a,ma in enumerate(ms):
    for c,mc in enumerate(ms):
        h1[a,c] = integ(np.conj(Ylm[ma])*V0*Ylm[mc])
ev = np.linalg.eigvalsh(h1)
print("unit one-electron eigen", np.round(ev,6))
gap = ev[2]-ev[0]  # t2g lower (3), eg upper (2)
# scale so that eg-t2g = 10 Dq with Dq=1
h1 = h1*10/gap
# shift: t2g at -4, eg at +6 (sign: lower group is t2g)
ev2 = np.linalg.eigvalsh(h1); print("scaled eig", np.round(ev2,4))
# Coulomb angular factors A^k(a,c;b,d)
def Mkq(a,c,k,q):
    # int Y_a* Y_c conj(Y_kq)
    Ykq = Y(k,q,TH,PH)
    return integ(np.conj(Ylm[a])*Ylm[c]*np.conj(Ykq)) if False else None
# precompute products for k=0,2,4
Ang = {}
for k in [0,2,4]:
    M = np.zeros((5,5,2*k+1),complex)  # M[a,c,q] = int Y_a* Y_c conj(Y_kq)
    for a,ma in enumerate(ms):
        for c,mc in enumerate(ms):
            for qi,q in enumerate(range(-k,k+1)):
                if abs(q)>2*0+k: continue
                Ykq = Y(k,q,TH,PH)
                M[a,c,qi] = integ(np.conj(Ylm[ma])*Ylm[mc]*np.conj(Ykq))
    Ang[k]=M
def Aang(k,a,c,b,d):
    M=Ang[k]
    # sum_q M[a,c,q] * int Y_b* Y_d Y_kq = conj(M[b,d,q]) ... int Y_b* Y_d Y_kq = conj(int Y_b Y_d^* Y_kq^*)... compute directly
    return (4*np.pi/(2*k+1))*np.sum(M[a,c,:]*Ang2[k][b,d,:])
Ang2={}
for k in [0,2,4]:
    N=np.zeros((5,5,2*k+1),complex)
    for b,mb in enumerate(ms):
        for d,md in enumerate(ms):
            for qi,q in enumerate(range(-k,k+1)):
                Ykq = Y(k,q,TH,PH)
                N[b,d,qi]=integ(np.conj(Ylm[mb])*Ylm[md]*Ykq)
    Ang2[k]=N
# check: sum over m of... fine
# Slater integrals: F2,F4 from C/B=4.5
x4 = (35*0+ 0)
r = 4.5
# C=35F4/441, B=(F2-5F4)/49 ; C/B = (35/9) x/(1-5x) = r
xr = r*9/(35+5*r*9)  # solve 35x = r*9*(1-5x) -> x = 9r/(35+45r)
F4r = xr
print("F4/F2 =", xr)
def coul_tensor(F2,F4):
    V = np.zeros((5,5,5,5))
    Fk = {0:0.0,2:F2,4:F4}
    for a in range(5):
     for c in range(5):
      for b in range(5):
       for d in range(5):
        s=0
        for k in [0,2,4]:
            if Fk[k]!=0: s+= Fk[k]*Aang(k,a,c,b,d).real
        V[a,c,b,d]=s
    return V
# determinant machinery: spin orbitals index = 2*orb + spin (0 up,1 down)
def so(o,s): return 2*o+s
def build_basis(nel,nup,ndn):
    dets=[]
    for up in itertools.combinations(range(5),nup):
        for dn in itertools.combinations(range(5),ndn):
            occ=tuple(sorted([so(o,0) for o in up]+[so(o,1) for o in dn]))
            dets.append(occ)
    return dets
def apply_c(occ, i, creation):
    # returns (sign, newocc) or None
    occ=list(occ)
    if creation:
        if i in occ: return None
        pos = sum(1 for x in occ if x<i)
        occ.append(i); occ.sort()
        return ((-1)**pos, tuple(occ))
    else:
        if i not in occ: return None
        pos = occ.index(i)
        occ.pop(pos)
        return ((-1)**pos, tuple(occ))
def apply_seq(occ, ops):
    # ops list of (i,creation) applied right to left: ops[-1] first
    sign=1; cur=occ
    for (i,cr) in reversed(ops):
        r=apply_c(cur,i,cr)
        if r is None: return None
        sign*=r[0]; cur=r[1]
    return sign,cur
def hamiltonian(dets, h1, V):
    idx={d:n for n,d in enumerate(dets)}
    H=np.zeros((len(dets),len(dets)))
    for n,occ in enumerate(dets):
        # one-body
        for a in range(5):
          for c in range(5):
            for s in range(2):
              if abs(h1[a,c])<1e-14: continue
              r=apply_seq(occ,[(so(a,s),True),(so(c,s),False)])
              if r is None: continue
              sg,new=r
              H[idx[new],n]+= sg*h1[a,c].real
        # two-body: 1/2 sum V_{acbd} a^+_a a^+_b a_d a_c  with <ab|1/r|cd>=V[a,c,b,d]
        for a in range(5):
         for b in range(5):
          for c in range(5):
           for d in range(5):
            v=V[a,c,b,d]
            if abs(v)<1e-14: continue
            for s1 in range(2):
             for s2 in range(2):
              r=apply_seq(occ,[(so(a,s1),True),(so(b,s2),True),(so(d,s2),False),(so(c,s1),False)])
              if r is None: continue
              sg,new=r
              H[idx[new],n]+=0.5*sg*v
    return H
EOF
cd /w && python3 -c "
import ts
print(ts.F4r if hasattr(ts,'F4r') else ts.F4r)
"